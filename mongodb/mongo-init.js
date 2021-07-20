db = db.getSiblingDB('opal_fetcher_mongodb');

db.createCollection('cities_collection');

db.cities_collection.insertMany([
  {
    city_id: 1,
    city_name: 'London',
    country_id: 1
  },
  {
    city_id: 2,
    city_name: 'Paris',
    country_id: 2
  },
  {
    city_id: 3,
    city_name: 'New York',
    country_id: 3
  },
  {
    city_id: 4,
    city_name: 'Tokyo',
    country_id: 4
  },
  {
    city_id: 5,
    city_name: 'Sydney',
    country_id: 5
  },
  {
    city_id: 6,
    city_name: 'Berlin',
    country_id: 6
  },
  {
    city_id: 7,
    city_name: 'Madrid',
    country_id: 7
  },
  {
    city_id: 8,
    city_name: 'Florence',
    country_id: 8
  },
  {
    city_id: 9,
    city_name: 'Amsterdam',
    country_id: 9
  },
]);