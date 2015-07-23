# py-mapzen-whosonfirst-lookup

"lookup"?  I don't know. Something. Also I can't be bothered to make myself sad and angry sorting out Python namespaces right now. I will, just not today...

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

## Importing data

There is already a handy `import.py` script (for importing a directory full of files) and basically all it is doing is this:

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

_Something something something about PostGIS schemas and geometry types. Yeah, that..._

## Fancy-pants HTTP pony lookups

On the server-side:

```
$> export DSN='...'
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

## Caveats

### Geometries

As I write this GeoJSON `geometry` elements are not included in any responses by default. This is by design for performance reasons. It will be possible 

### Search 

This is not meant for fulltext search. No. There will be a separate `py-mapzen-whosonfirst-search` package that will make happy with Elasticsearch and together they will make beautiful search. This is not that package.

## See also

* https://github.com/mapzen/theory-whosonfirst
* https://github.com/mapzen/whosonfirst-data