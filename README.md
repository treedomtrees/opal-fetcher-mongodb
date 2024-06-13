<p  align="center">
 <img src="https://github.com/permitio/opal/assets/4082578/4e21f85f-30ab-43e2-92de-b82f78888c71" height=170 alt="opal" border="0" />
</p>
<h2 align="center">
OPAL Fetcher for MongoDB
</h2>

<h4 align="center">
Made with ❤️ at <a href="https://treedom.net"><img src="https://i.ibb.co/QfYVtP5/Treedom-logo.png" height="24" alt="treedom" border="0" /></a>, <a href="#-join-us-in-making-a-difference-">join us in making a difference</a>!
</h4>

<h6 align="center">
<a href="https://www.treedom.net/it/organization/treedom/event/treedom-open-source"><img src="https://badges.treedom.net/badge/f/treedom-open-source?2" alt="plant-a-tree" border="0" /></a>
</h6>

[Check out OPAL main repo here.](https://github.com/permitio/opal)


### What's in this repo?
An OPAL [custom fetch provider](https://docs.opal.ac/tutorials/write_your_own_fetch_provider) to bring authorization state from [MongoDB](https://www.mongodb.com/).

### How to try this custom fetcher in one command? (Example docker-compose configuration)

You can test this fetcher with the example docker compose file in this repository root. Clone this repo, `cd` into the cloned repo, and then run:
```
docker compose up
```
this docker compose configuration already correctly configures OPAL to load the MongoDB Fetch Provider, and correctly configures `OPAL_DATA_CONFIG_SOURCES` to include an entry that uses this fetcher.

### ✏️ How to use this fetcher in your OPAL Setup

#### 1) Build a custom opal-client `Dockerfile`

The official docker image only contains the built-in fetch providers. You need to create your own `Dockerfile` (that is based on the official docker image), that includes this fetcher's pip package.

Your `Dockerfile` should look like this:
```
FROM permitio/opal-client:latest
RUN pip install --no-cache-dir --user opal-fetcher-mongodb
```

#### 2) Build your custom opal-client container
Say your special Dockerfile from step one is called `custom_client.Dockerfile`.

You must build a customized OPAL container from this Dockerfile, like so:
```
docker build -t yourcompany/opal-client -f custom_client.Dockerfile .
```

#### 3) When running OPAL, set `OPAL_FETCH_PROVIDER_MODULES`
Pass the following environment variable to the OPAL client docker container (comma-separated provider modules):
```
OPAL_FETCH_PROVIDER_MODULES=opal_common.fetcher.providers,opal_fetcher_mongodb.provider
```
Notice that OPAL receives a list from where to search for fetch providers.
The list in our case includes the built-in providers (`opal_common.fetcher.providers`) and our custom MongoDB provider.

#### 4) Using the custom provider in your DataSourceEntry objects

Your DataSourceEntry objects (either in `OPAL_DATA_CONFIG_SOURCES` or in dynamic updates sent via the OPAL publish API) can now include this fetcher's config.

Example value of `OPAL_DATA_CONFIG_SOURCES` (formatted nicely, but in env var you should pack this to one-line and no-spaces):
```json
{
  "config": {
    "entries": [
      {
        "url": "mongodb://user:password@mongodb/test_database?authSource=admin",
        "config": {
          "fetcher": "MongoDBFetchProvider",
          "database": "opal_fetcher_mongodb",
          "collection": "cities_collection",
          "find": { "query": {} }
        },
        "topics": ["policy_data"],
        "dst_path": "cities"
      }
    ]
  }
}
```

Notice how `config` is an instance of `MongoDBFetchProvider` (code is in `opal_fetcher_mongodb/provider.py`).

Values for this fetcher config:
* The `url` is actually a MongoDB uri.
* Your `config` must include the `fetcher` key to indicate to OPAL that you use a custom fetcher.
* Your `config` must include the `collection` key to indicate what collection to query in MongoDB.
* Your `config` may include the `database` key to indicate what database to query in MongoDB. If not specified, the default database will be used.
* Your `config` must include one of `findOne`, `find` or `aggregate` keys to indicate what query to run against MongoDB.
* Your `config` may include the `transform` key to transform the results from the `find` or `aggregate` queries.

#### Query methods
All the three available query methods accept the same input parameters as defined in the MongoDB documentation.

##### findOne

* `findOne` - [MongoDB docs](https://docs.mongodb.com/manual/reference/method/db.collection.findOne/)

<details>
  <summary>Example configuration</summary>

```json
{
  "config": {
    "entries": [
      {
        ...
        "config": {
          ...
          "findOne": {
            "query": {
              ...
            },
            "projection": {
              ...
            },
            "options": {
              ...
            }
          }
        }
      }
    ]
  }
}
```
</details>

##### find

* `find` - [MongoDB docs](https://docs.mongodb.com/manual/reference/method/db.collection.find/)

<details>
  <summary>Example configuration</summary>

```json
{
  "config": {
    "entries": [
      {
        ...
        "config": {
          ...
          "find": {
            "query": {
              ...
            },
            "projection": {
              ...
            },
            "options": {
              ...
            }
          },
          "transform": {
            "first": false,
            "mapKey": "",
            "merge": true
          }
        }
      }
    ]
  }
}
```
</details>

##### aggregate

* `aggregate` - [MongoDB docs](https://docs.mongodb.com/manual/reference/method/db.collection.aggregate/)

<details>
  <summary>Example configuration</summary>

```json
{
  "config": {
    "entries": [
      {
        ...
        "config": {
          ...
          "aggregate": {
            "pipeline": [
              ...
            ],
            "options": {
              ...
            }
          },
          "transform": {
            "first": false,
            "mapKey": ""
          }
        }
      }
    ]
  }
}
```
</details>

#### Query transform
`transform` allows you to transform the results from the `find` or `aggregate` queries.

##### first
`transform.first` allows you to return only the first result from the query.

Equivalent to the following Python code:

```python
result = query_result[0]
```

##### mapKey
`transform.mapKey` allows you to map the original list-like result to a dictionary-like result using the property specified in the `mapKey` as the key for the dictionary.

Equivalent to the following Python code:

```python
result = {}
for item in query_result:
    result[item['key']] = item
```

> Only properties in the root of the document can be used as the key for the dictionary.

##### merge

`transform.merge` allows you to merge the results from the query into a single document. Duplicate keys will be overwritten by the last document in the list.

Equivalent to the following Python code:

```python
result = {}
for item in query_result:
    for key, value in item.items():
        result[key] = value
```

## 🌳 Join Us in Making a Difference! 🌳

We invite all developers who use Treedom's open-source code to support our mission of sustainability by planting a tree with us. By contributing to reforestation efforts, you help create a healthier planet and give back to the environment. Visit our [Treedom Open Source Forest](https://www.treedom.net/en/organization/treedom/event/treedom-open-source) to plant your tree today and join our community of eco-conscious developers.

Additionally, you can integrate the Treedom GitHub badge into your repository to showcase the number of trees in your Treedom forest and encourage others to plant new ones. Check out our [integration guide](https://github.com/treedomtrees/.github/blob/main/profile/README.md) to get started.

Together, we can make a lasting impact! 🌍💚
