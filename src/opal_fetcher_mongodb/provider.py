"""
Simple fetch provider for MongoDB.
"""
from typing import Optional, List

from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import OperationFailure
from pydantic import BaseModel, Field
from tenacity import wait, stop, retry_unless_exception_type

from opal_common.fetcher.fetch_provider import BaseFetchProvider
from opal_common.fetcher.events import FetcherConfig, FetchEvent
from opal_common.logger import logger


class MongoDBFindOneParams(BaseModel):
    """
    Params needed to run a 'findOne' query against MongoDB.
    """

    query: dict = Field(None, description="the query to run")
    projection: Optional[dict] = Field(None, description="the projection to run")
    options: Optional[dict] = Field(None, description="the options to pass to the findOne call, same args of PyMongo findOne")


class MongoDBFindParams(BaseModel):
    """
    Params needed to run a 'find' query against MongoDB.
    """

    query: dict = Field(None, description="the query to run")
    projection: Optional[dict] = Field(None, description="the projection to run")
    options: Optional[dict] = Field(None, description="the options to pass to the find call, same args of PyMongo find")


class MongoDBAggregateParams(BaseModel):
    """
    Params needed to run an aggregation pipeline against MongoDB.
    """

    pipeline: List[dict] = Field(None, description="the pipeline to run, an array of stages")
    options: Optional[dict] = Field(None, description="the options to pass to the aggregate call, same args of PyMongo aggregate")


class MongoDBTransformParams(BaseModel):
    """
    Params that specify how the result from a MongoDB query should be transformed.
    """

    first: Optional[bool] = Field(False, description="whether to return only the first document, used only by find and aggregate")
    mapKey: Optional[str] = Field(None, description="transform the array of documents to an object, using the specified key as the object key, used only by find and aggregate")
    merge: Optional[bool] = Field(False, description="merge the resulting array of documents into a single object, duplicated keys will be overwritten sequentially, used only by find and aggregate")


class MongoDBFetcherConfig(FetcherConfig):
    """
    Config for MongoDBFetchProvider, instance of `FetcherConfig`.
    """

    fetcher: str = "MongoDBFetchProvider"
    database: Optional[str] = Field(
        None, description="the database to use"
    )
    collection: str = Field(
        ..., description="the collection to run the query against"
    )
    findOne: Optional[MongoDBFindOneParams] = Field(
        None,
        description="find one document and use it to update the destination",
    )
    find: Optional[MongoDBFindParams] = Field(
        None,
        description="find documents and use them to update the destination",
    )
    aggregate: Optional[MongoDBAggregateParams] = Field(
        None,
        description="run an aggregation pipeline and use the result to update the destination",
    )
    transform: Optional[MongoDBTransformParams] = Field(
        None,
        description="transform the result of the query before updating the destination",
    )



class MongoDBFetchEvent(FetchEvent):
    """
    A FetchEvent shape for the MongoDB Fetch Provider.
    """

    fetcher: str = "MongoDBFetchProvider"
    config: MongoDBFetcherConfig = None


class MongoDBFetchProvider(BaseFetchProvider):
    """
    An OPAL fetch provider for MongoDB.

    We fetch data from a MongoDB instance by running one of findOne, find or aggregate queries,
    transforming the results to json and dumping the results into the policy store.
    """

    RETRY_CONFIG = {
        "wait": wait.wait_random_exponential(),
        "stop": stop.stop_after_attempt(10),
        "retry": retry_unless_exception_type(
            OperationFailure
        ), # query error (i.e: invalid pipeline stage, etc)
        "reraise": True,
    }

    def __init__(self, event: MongoDBFetchEvent) -> None:
        if event.config is None:
            # FIXME: where should collection be read from?
            event.config = MongoDBFetcherConfig(collection='')
        super().__init__(event)
        self._connection: Optional[AsyncIOMotorClient] = None
        # TODO: implement readonly transaction.
        # self._transaction: Optional[Transaction] = None

    def parse_event(self, event: FetchEvent) -> MongoDBFetchEvent:
        return MongoDBFetchEvent(**event.dict(exclude={"config"}), config=event.config)

    async def __aenter__(self):
        self._event: MongoDBFetchEvent # type casting

        uri: str = self._event.url

        logger.debug(f"{self.__class__.__name__} connecting to database")

        # connect to the MongoDB instance
        self._connection: AsyncIOMotorClient = AsyncIOMotorClient(host=uri)

        # start a readonly transaction (we don't want OPAL client writing data due to security!)
        # TODO: implement readonly transaction.
        # self._transaction: Transaction = self._connection.transaction(readonly=True)
        # await self._transaction.__aenter__()

        return self

    async def __aexit__(self, exc_type=None, exc_val=None, tb=None):
        # TODO: implement readonly transaction.
        # End the transaction
        # if self._transaction is not None:
        #     await self._transaction.__aexit__(exc_type, exc_val, tb)

        # Close the connection
        if self._connection is not None:
            # await self._connection.close()
            self._connection.close()

    async def _fetch_(self):
        self._event: MongoDBFetchEvent # type casting

        if self._event.config is None:
            logger.warning(
                "incomplete fetcher config: MongoDB data entries require a query to specify what data to fetch!"
            )
            return []

        # validate that only one of findOne, find or aggregate is defined
        defined_queries = 0
        if self._event.config.findOne is not None:
            defined_queries += 1
        if self._event.config.find is not None:
            defined_queries += 1
        if self._event.config.aggregate is not None:
            defined_queries += 1

        if defined_queries != 1:
            logger.warning(
                "malformed fetcher config: MongoDB data entries requires one of findOne, find or aggregate to be defined!"
            )
            return []

        # selecting database and collection
        if self._event.config.database is not None:
            db = self._connection[self._event.config.database]
        else:
            db = self._connection

        collection = db[self._event.config.collection]

        # define first option
        if self._event.config.transform is not None:
            first = self._event.config.transform.first
            if first is None:
                first = False
        else:
            first = False

        if self._event.config.findOne is not None:
            logger.debug(f"{self.__class__.__name__} executing findOne query")

            try:
                # read query, projection and options from config
                query = self._event.config.findOne.query

                if self._event.config.findOne.projection is not None:
                    projection = self._event.config.findOne.projection
                else:
                    projection = None

                if self._event.config.findOne.options is not None:
                    options = self._event.config.findOne.options
                else:
                    options = {}

                # fetch the data
                document = await collection.find_one(
                    query, projection=projection, **options
                )

                if document is None:
                    return []
                else:
                    return [document]
            except Exception as e:
                template = "An exception of type {0} occurred. Arguments:\n{1!r}"
                message = template.format(type(e).__name__, e.args)

                logger.error(f"{self.__class__.__name__} error executing findOne query")
                logger.error(message)

                # pass along the original exception
                raise e

        if self._event.config.find is not None:
            logger.debug(f"{self.__class__.__name__} executing find query")

            try:
                # read query, projection and options from config
                query = self._event.config.find.query

                if self._event.config.find.projection is not None:
                    projection = self._event.config.find.projection
                else:
                    projection = None

                if self._event.config.find.options is not None:
                    options = self._event.config.find.options
                else:
                    options = {}

                # fetch the data
                documents = []

                cursor = collection.find(
                    query, projection=projection, **options
                )

                # if we only want the first document, we can just return it
                if first:
                    logger.debug(f"{self.__class__.__name__} fetching first document of find query")
                    return await cursor.to_list(length=1)

                # otherwise, we need to iterate over the cursor
                logger.debug(f"{self.__class__.__name__} iterating documents of find query")

                async for document in cursor:
                    documents.append(document)

                # return the documents
                return documents
            except Exception as e:
                template = "An exception of type {0} occurred. Arguments:\n{1!r}"
                message = template.format(type(e).__name__, e.args)

                logger.error(f"{self.__class__.__name__} error executing find query")
                logger.error(message)

                # pass along the original exception
                raise e

        if self._event.config.aggregate is not None:
            logger.debug(f"{self.__class__.__name__} executing aggregation pipeline")

            try:
                # read pipeline and options from config
                pipeline = self._event.config.aggregate.pipeline

                if self._event.config.aggregate.options is not None:
                    options = self._event.config.aggregate.options
                else:
                    options = {}

                # fetch the data
                documents = []

                cursor = collection.aggregate(
                    pipeline, **options
                )

                # if we only want the first document, we can just return it
                if first:
                    logger.debug(f"{self.__class__.__name__} fetching first document of aggregation pipeline")
                    return await cursor.to_list(length=1)

                # otherwise, we need to iterate over the cursor
                logger.debug(f"{self.__class__.__name__} iterating documents of aggregation pipeline")

                async for document in cursor:
                    documents.append(document)

                # return the documents
                return documents
            except Exception as e:
                template = "An exception of type {0} occurred. Arguments:\n{1!r}"
                message = template.format(type(e).__name__, e.args)

                logger.error(f"{self.__class__.__name__} error executing aggregation pipeline")
                logger.error(message)

                # pass along the original exception
                raise e

    async def _process_(self, records: List[dict]):
        self._event: MongoDBFetchEvent # type casting

        # TODO: make sure that only one single transform is defined

        try:
            # handle findOne
            if self._event.config.findOne is not None:
                if records and len(records) > 0 and records[0] is not None:
                    return dict(records[0])
                else:
                    return {}

            # define first option
            if self._event.config.transform is not None:
                first = self._event.config.transform.first
                if first is None:
                    first = False
            else:
                first = False

            # define mapKey option
            if self._event.config.transform is not None:
                mapKey = self._event.config.transform.mapKey
            else:
                mapKey = None

            # define merge option
            if self._event.config.transform is not None:
                merge = self._event.config.transform.merge
                if merge is None:
                    merge = False
            else:
                merge = False

            # handle one single document
            result = None
            if first:
                if records and len(records) > 0 and records[0] is not None:
                    result = dict(records[0])
                else:
                    result = {}

            # handle merge
            elif merge:
                # transform the array of documents to a single object, duplicated keys will be overwritten sequentially
                document = {}

                for record in records:
                    document.update(dict(record))

                result = document

            # handle mapKey
            elif mapKey is not None:
                # transform the array of documents to an object, using the specified key as the object key
                document = {}

                for record in records:
                    document[record[mapKey]] = dict(record)

                result = document

            else:
                # handle multiple documents
                result = [dict(record) for record in records]

            return result
        except Exception as e:
            template = "An exception of type {0} occurred. Arguments:\n{1!r}"
            message = template.format(type(e).__name__, e.args)

            logger.error(f"{self.__class__.__name__} error processing records")
            logger.error(message)

            # pass along the original exception
            raise e
