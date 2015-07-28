# py-mapzen-whosonfirst-lookup

"lookup"?  I don't know. Something. Also I can't be bothered to make myself sad and angry sorting out Python namespaces right now. I will, just not today...

## Importing data

There is already a handy `import.py` script for importing a directory full of files (like say, maybe... [whosonfirst-data](https://github.com/mapzen/whosonfirst-data)) and basically all it is doing is this:

```
import whosonfirst
import mapzen.whosonfirst.utils

dsn = "..."
db = whosonfirst.lookup(dsn)

source = os.path.asbpath(source)
crawl = mapzen.whosonfirst.utils.crawl(source, inflate=True)

for feature in crawl:
	db.import_feature(feature)
```

### PostGIS

```
$> sudo apt-get install postgresql-9.3 postgresql-client postgis postgresql-9.3-postgis-scripts python-psycopg2
$> sudo su -m postgres
$> createdb whosonfirst_pip
$> psql -d whosonfirst_pip -c "CREATE EXTENSION postgis;"
$> psql -d whosonfirst_pip -c "CREATE EXTENSION postgis_topology;"
$> psql -d whosonfirst
gazetteer=# CREATE TABLE whosonfirst (id BIGINT PRIMARY KEY, placetype VARCHAR, properties TEXT, geom GEOGRAPHY(MULTIPOLYGON, 4326));
CREATE INDEX by_geom ON whosonfirst USING GIST(geom);
CREATE INDEX by_placetype ON whosonfirst (placetype);
VACUUM ANALYZE;
```

#### Caveats

* This schema assumes `MULTIPOLYGON` geometries so 1) the import tools will convert single geometries to... mutli-geometries and 2) it will not work with point data (aka venues)
* The example above (and the code) still assume a database called `whosonfirst_pip` instead of something more sensible like `whosonfirst_lookup`. One thing at a time...

## Usage

### Basic

_Remember, when you see `whosonfirst.lookup` you are seeing me trying not to get angry and sad before I have to. This name will change._

### Lookup by lat,lon

Find one or more WOF places (optionally of a specific placetype) that contain a given point.

```
import whosonfirst

dsn = "..."
db = whosonfirst.lookup(dsn)

lat = 37.763251
lon = -122.424002
placetype = 'neighbourhood'

rsp = db.get_by_latlon(lat, lon, placetype=placetype)

for feature in rsp:
	props = feature['properties']
	print "%s %s" % (props['wof:id'], props['wof:name'])
```

For example:

```
$> whosonfirst.py -p neighbourhood -l 37.763251,-122.424002
85865951 Mission Dolores
```

### Lookup by extent

Find one or more WOF places (optionally of a specific placetype) that intersect a given bounding box.

```
import whosonfirst

dsn = "..."
db = whosonfirst.lookup(dsn)

bbox = '37.763251,-122.424002,37.768476,-122.417865'
swlat, swlon, nelat, nelon = bbox.split(",")
placetype = 'neighbourhood'

rsp = db.get_by_extent(swlat, swlon, nelat, nelon, placetype=placetype)

for feature in rsp:
	props = feature['properties']
	print "%s %s" % (props['wof:id'], props['wof:name'])
```

For example:

```
$> whosonfirst.py -p neighbourhood -b 37.763251,-122.424002,37.768476,-122.417865
85834637 Mission
85887467 The Hub
85865951 Mission Dolores
```

### Lookup by TMS tile address

This just requires writing some hoop-jumping around Migurski's [whereami.py](https://github.com/migurski/whereami) code to convert a `Z/X/Y` tile address in to a bounding box and then invoke `get_by_extent`. In the meantime _you_ could just write some hoop-jumping code of your around Migurski's [whereami.py](https://github.com/migurski/whereami) code... to convert a `Z/X/Y` tile address in to a bounding box.

## Fancy-pants HTTP pony lookups

See also: [ops-mapzen-whosonfirst-lookup](https://github.com/mapzen/ops-mapzen-whosonfirst-lookup) for a fancier gunicorn/nginx version of this.

On the server-side:

```
$> export WOF_LOOKUP_DSN='...'
$> ./scripts/server.py -v 
INFO:werkzeug: * Running on http://127.0.0.1:8888/
INFO:werkzeug:127.0.0.1 - - [23/Jul/2015 20:39:13] "GET /?bbox=37.763251,-122.424002,37.768476,-122.417865&placetype=country HTTP/1.1" 200 -
```

On the client-side:

```
$> curl 'http://localhost:8888/?bbox=37.763251,-122.424002,37.768476,-122.417865&placetype=country'
{
  "features": [
    {
      "id": 85633793, 
      "properties": {
        "geom:area": 9833516741647.34, 
        "geom:latitude": 45.964509, 
        "geom:longitude": -113.2686, 
        "iso:country": "US", 
        "name:chi_p": [
          "\u7f8e\u570b"
        ], 
        "name:chi_v": [
          "\u7f8e\u5229\u575a\u5408\u8846\u56fd", 
          "\u7f8e\u5229\u5805\u5408\u8846\u56fd", 
          "\u7f8e\u56fd"
        ], 
        "name:cze_p": [
          "Spojen\u00e9 St\u00e1ty Americk\u00e9"
        ], 
        "name:cze_v": [
          "Spojen\u00e9 st\u00e1ty"
        ], 
        "name:dan_v": [
          "Amerikas Forenede Stater"
        ], 
        "name:dut_p": [
          "Verenigde Staten"
        ], 
        "name:dut_v": [
          "VS", 
          "Verenigde Staten van Amerika"
        ], 
        "name:eng_a": [
          "US", 
          "USA"
        ], 
	# and so on...
        "wof:id": 85633793, 
        "wof:lastmodified": 1437610336, 
        "wof:name": "United States", 
        "wof:parent_id": 102191575, 
        "wof:path": "856/337/93/85633793.geojson", 
        "wof:placetype": "country", 
        "wof:superseded_by": [], 
        "wof:supersedes": []
      }, 
      "type": "Feature"
    }
  ], 
  "type": "FeatureCollection"
}
```

## Caveats

### Geometries

As I write this GeoJSON `geometry` elements are not included in any responses by default. This is by design for performance reasons. It will be possible 

### Search 

This is not meant for fulltext search. No. There will be a separate `py-mapzen-whosonfirst-search` package that will make happy with Elasticsearch and together they will make beautiful search. This is not that package.

## See also

* https://github.com/mapzen/theory-whosonfirst
* https://github.com/mapzen/whosonfirst-data