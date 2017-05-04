# py-mapzen-whosonfirst-spatial

Too soon. Everything is changing. Move along.

## Interface

First of all, we're using the term "interface" loosely here. I don't _think_ Python has interfaces so what we're really talking about are the methods defined in `mapzen.whosonfirst.spatial.base` class. This class is then subclassed by "client" (discussed below) who override them, since they all raise an exception by default. Ideally each client would implement every method but in reality they won't for a variety of reasons.

### point_in_polygon(self, lat, lon, **kwargs)

Perform a point in polygon query, with 0 or more optional filters.

### intersects(self, feature, **kwargs)

Return all the things that intersect with `feature`, with 0 or more optional filters.

### intersects_paginated(self, feature, **kwargs)

Return all the things that intersect with `feature`, with 0 or more optional filters. Take care of paginating the results. Pagination details are left to the discretion of individual clients.

### row_to_feature(self, feature, **kargs)

Convert a client's internal representation in to a proper GeoJSON `Feature` thingy. Ideally it would be the actual Who's On First record but that's still a bit squishy as of this wriging.

### index_feature(self, feature, **kwargs)

Index `feature` in the client's data store. Practically speaking this is still pretty specific to the PostGIS client right now but that may change.

## Clients

We index and query spatial data in a variety of ways both to keep us honest and because different circumstances have different constraints and burdens. Ideally we'd like to arrive at a place where every index would store (or at least return) the same data, at least in so far as consumers are concerned. We're not quite there yet.

### mapzen.whosonfirst.spatial.postgres.postgis

This implements all of "base" interface assuming a PostGIS database. All of this code is interwoven with code in the [go-whosonfirst-pgis](https://github.com/whosonfirst/go-whosonfirst-pgis) package which we use for indexing (because it's faster than doing in Python). As of this writing that package is where the database schema is defined.

### mapzen.whosonfirst.spatial.whosonfirst.api

Currently this implements the `point_in_polygon` and `row_to_feature` interfaces using the [Who's On First API](https://mapzen.com/documentation/wof/methods/#whosonfirstplaces).

### mapzen.whosonfirst.spatial.whosonfirst.pip

Currently this implements the `point_in_polygon` and `row_to_feature` interfaces using the [Who's On First PIP server](https://github.com/whosonfirst/go-whosonfirst-pip).

## Usage

## Basic

```
import mapzen.whosonfirst.spatial.whosonfirst
import mapzen.whosonfirst.spatial.postgres

pip_client = mapzen.whosonfirst.spatial.whosonfirst.pip()
pg_client = mapzen.whosonfirst.spatial.postgres.postgis()

for row in pip_client.point_in_polygon(40.661367, -111.500959):
    f = pip_client.row_to_feature(row)
    print f["properties"]

print "--"

for row in pg_client.point_in_polygon(40.661367, -111.500959):
    f = pg_client.row_to_feature(row)
    print f["properties"]
```

This would print:

```
{'wof:name': u'Park City', 'wof:placetype': u'locality', 'wof:id': 101727553}
{'wof:name': u'84060', 'wof:placetype': u'postalcode', 'wof:id': 554749823}
{'wof:name': u'Summit', 'wof:placetype': u'county', 'wof:id': 102083555}
{'wof:name': u'Utah', 'wof:placetype': u'region', 'wof:id': 85688567}
{'wof:name': u'United States', 'wof:placetype': u'country', 'wof:id': 85633793}
--
{u'wof:repo': u'whosonfirst-data-postalcode-us', 'geom:longitude': -111.501929, 'geom:latitude': 40.652347, u'wof:name': u'84060', 'wof:placetype': 'postalcode', u'wof:country': u'US', 'wof:parent_id': 101727553L, u'wof:hierarchy': [{u'region_id': 85688567, u'continent_id': 102191575, u'country_id': 85633793, u'locality_id': 101727553, u'county_id': 102083555, u'postalcode_id': 554749823}], 'wof:id': 554749823L}
{u'wof:repo': u'whosonfirst-data-constituency-us', 'geom:longitude': -111.328529, 'geom:latitude': 40.944919, u'wof:name': u'Utah Congressional District 1', 'wof:placetype': 'constituency', u'wof:country': u'us', 'wof:parent_id': 85688567L, u'wof:hierarchy': [{u'continent_id': 102191575, u'country_id': 85633793, u'region_id': 85688567}], 'wof:id': 1108737501L}
{u'wof:repo': u'whosonfirst-data-constituency-us', 'geom:longitude': -111.878816, 'geom:latitude': 39.098999, u'wof:name': u'Utah', 'wof:placetype': 'constituency', u'wof:country': u'US', 'wof:parent_id': 85633793L, u'wof:hierarchy': [{u'continent_id': 102191575, u'country_id': 85633793, u'region_id': 85688567}], 'wof:id': 1108746635L}
{u'wof:repo': u'whosonfirst-data', 'geom:longitude': -111.230352, 'geom:latitude': 40.861066, u'wof:name': u'Summit', 'wof:placetype': 'county', u'wof:country': u'US', 'wof:parent_id': 85688567L, u'wof:hierarchy': [{u'continent_id': 102191575, u'country_id': 85633793, u'region_id': 85688567, u'county_id': 102083555}], 'wof:id': 102083555L}
{u'wof:repo': u'whosonfirst-data', 'geom:longitude': -96.999668, 'geom:latitude': 39.715956, u'wof:name': u'United States', 'wof:placetype': 'country', u'wof:country': u'US', 'wof:parent_id': 102191575L, u'wof:hierarchy': [{u'continent_id': 102191575, u'country_id': 85633793, u'empire_id': 136253057}], 'wof:id': 85633793L}
{u'wof:repo': u'whosonfirst-data', 'geom:longitude': -101.328273, 'geom:latitude': 38.309137, u'wof:name': u'North America', 'wof:placetype': 'continent', u'wof:country': u'', 'wof:parent_id': -1L, u'wof:hierarchy': [], 'wof:id': 102191575L}
{u'wof:repo': u'whosonfirst-data', 'geom:longitude': -106.298325, 'geom:latitude': 42.095168, u'wof:name': u'America/Denver', 'wof:placetype': 'timezone', u'wof:country': u'', 'wof:parent_id': 85633793L, u'wof:hierarchy': [{u'continent_id': 102191575, u'timezone_id': 102047459, u'country_id': 85633793}], 'wof:id': 102047459L}
{u'wof:repo': u'whosonfirst-data', 'geom:longitude': -111.878816, 'geom:latitude': 39.098999, u'wof:name': u'Utah', 'wof:placetype': 'region', u'wof:country': u'US', 'wof:parent_id': 85633793L, u'wof:hierarchy': [{u'continent_id': 102191575, u'country_id': 85633793, u'region_id': 85688567}], 'wof:id': 85688567L}
{u'wof:repo': u'whosonfirst-data', 'geom:longitude': -111.496653, 'geom:latitude': 40.64482, u'wof:name': u'Park City', 'wof:placetype': 'locality', u'wof:country': u'US', 'wof:parent_id': 102083555L, u'wof:hierarchy': [{u'continent_id': 102191575, u'locality_id': 101727553, u'country_id': 85633793, u'region_id': 85688567, u'county_id': 102083555}], 'wof:id': 101727553L}
```

_The example response for the `pip_client` is actually a bit misleading. As of this writing it has been taught to fetch the source WOF record over the network so there is a lot more data. That's what it would look like if it didn't make a network request._

## See also