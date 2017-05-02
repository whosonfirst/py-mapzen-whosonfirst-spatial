# py-mapzen-whosonfirst-spatial

Too soon. Everything is changing. Move along.

## Example

## Basic

```
import mapzen.whosonfirst.spatial.whosonfirst
import mapzen.whosonfirst.spatial.postgres

wof_pip = mapzen.whosonfirst.spatial.whosonfirst.pip()
pg_pip = mapzen.whosonfirst.spatial.postgres.postgis()

for row in wof_pip.point_in_polygon(40.661367, -111.500959):
    f = wof_pip.row_to_feature(row)
    print f["properties"]

print "--"

for row in pg_pip.point_in_polygon(40.661367, -111.500959):
    f = pg_pip.row_to_feature(row)
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