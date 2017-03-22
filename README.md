# py-mapzen-whosonfirst-spatial

## Install

```
sudo pip install -r requirements.txt .
```

## IMPORTANT

This library is provided as-is, right now. It lacks proper
documentation which will probably make it hard for you to use unless
you are willing to poke and around and investigate things on your
own.

### PostGIS

```
$> sudo apt-get install postgresql-9.3 postgresql-client postgis postgresql-9.3-postgis-scripts python-psycopg2
$> sudo su -m postgres
$> createdb whosonfirst
$> psql -d whosonfirst -c "CREATE EXTENSION postgis;"
$> psql -d whosonfirst -c "CREATE EXTENSION postgis_topology;"
$> psql -d whosonfirst
gazetteer=# CREATE TABLE whosonfirst (id BIGINT PRIMARY KEY, parent_id BIGINT, placetype VARCHAR, geom GEOGRAPHY(MULTIPOLYGON, 4326), centroid GEOGRAPHY(POINT, 4326));
CREATE INDEX by_geom ON whosonfirst USING GIST(geom);
CREATE INDEX by_placetype ON whosonfirst (placetype);
VACUUM ANALYZE;
```

## Caveats

### Geometries

* This schema assumes `MULTIPOLYGON` geometries so 1) the import tools will convert single geometries to... mutli-geometries and 2) it will not work with point data (aka venues) – this is no longer true but I haven't updated the code...

* As I write this GeoJSON `geometry` elements are not included in any responses by default. This is by design for performance reasons. It will be possible 

### Search 

This is not meant for fulltext search. No. There will be a separate `py-mapzen-whosonfirst-search` package that will make happy with Elasticsearch and together they will make beautiful search. This is not that package.

## See also
