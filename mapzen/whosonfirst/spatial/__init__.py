# https://pythonhosted.org/setuptools/setuptools.html#namespace-packages
__import__('pkg_resources').declare_namespace(__name__)

import psycopg2
import geojson
import json
import logging
import shapely.geometry

import mapzen.whosonfirst.placetypes

def cfg2dsn(cfg, sect):
        
    db_user = cfg.get(sect, 'db_user')
    db_pswd = cfg.get(sect, 'db_pswd')
    db_host = cfg.get(sect, 'db_host')
    db_name = cfg.get(sect, 'db_name')
    
    dsn = "dbname=%s user=%s password=%s host=%s" % (db_name, db_user, db_pswd, db_host)
    return dsn

def feature2reversegeo_coords(feature):

    props = feature['properties']

    lat = props.get('mps:latitude', None)
    lon = props.get('mps:longitude', None)

    if lat and lon:
        return (lat, lon)

    lat = props.get('lbl:latitude', None)
    lon = props.get('lbl:longitude', None)

    if lat and lon:
        return (lat, lon)

    lat = props.get('geom:latitude', None)
    lon = props.get('geom:longitude', None)
    
    if lat and lon:
        return (lat, lon)

    geom = feature['geometry']
    shp = shapely.geometry.asShape(geom)
    coords = shp.centroid
    
    lat = coords.y
    lon = coords.x

    return (lat, lon)

def feature2reversegeo_placetypes(feature, **kwargs):

    allowed_optional = kwargs.get('allowed_optional', ['county'])
    
    props = feature['properties']
    placetype = props['wof:placetype']

    ancestors = []

    last = placetype

    while last:

        placetype = mapzen.whosonfirst.placetypes.placetype(last)
        last = None

        for p in placetype.parents():

            pt = str(p)
            role = p.role()

            if role == 'common':
                ancestors.append(pt)
            elif role == 'common_optional' and str(p) in allowed_optional:
                ancestors.append(pt)
            else:
                pass

            last = pt

    return ancestors

class cache:
    
    def __init__(self):
        self.__cache__ = {}

    def get(self, k):
        return self.__cache__.get(k, None)

    def set(self, k, v):
        self.__cache__[k] = v

    def unset(self, k):
        if self.__cache__.get(k, None):
            del(self.__cache__[k])

class db:

    def __init__ (self, dsn):

        self.cache = cache()

        # https://pypi.python.org/pypi/psycopg2
        # http://initd.org/psycopg/docs/module.html#psycopg2.connect
        # dsn = "dbname=%s user=%s password=%s host=%s" % (db_name, db_user, db_pswd, db_host)

        conn = psycopg2.connect(dsn)
        curs = conn.cursor()

        self.conn = conn
        self.curs = curs

class index(db):

    def import_feature(self, feature):

        geom = feature['geometry']
        props = feature['properties']

        if geom['type'] == 'Polygon':
            geom['coordinates'] = [ geom['coordinates'] ]
            geom['type'] = 'MultiPolygon'

        placetype = props['wof:placetype']
        id = props['wof:id']
        id = int(id)

        parent_id = props.get('wof:planet_id', -1)

        if placetype == 'planet':
            return False

        str_props = json.dumps(props)
        str_geom = json.dumps(geom)
        
        try:

            if geom['type'] == 'Point':
                sql = "INSERT INTO whosonfirst (id, parent_id, placetype, properties, centroid) VALUES (%s, %s, %s, %s, ST_GeomFromGeoJSON(%s))"
            else:
                sql = "INSERT INTO whosonfirst (id, parent_id, placetype, properties, geom) VALUES (%s, %s, %s, %s, ST_GeomFromGeoJSON(%s))"

            params = (id, parent_id, placetype, str_props, str_geom)
            
            self.curs.execute(sql, params)
            self.conn.commit()

            logging.debug("insert WOF:ID %s" % id)

        except psycopg2.IntegrityError, e:

            try:
                self.conn.rollback()
                
                if geom['type'] == 'Point':
                    sql = "UPDATE whosonfirst SET parent_id=%s, placetype=%s, properties=%s, centroid=ST_GeomFromGeoJSON(%s) WHERE id=%s"
                else:
                    sql = "UPDATE whosonfirst SET parent_id=%s, placetype=%s, properties=%s, geom=ST_GeomFromGeoJSON(%s) WHERE id=%s"

                params = (parent_id, placetype, str_props, str_geom, id)
                
                self.curs.execute(sql, params)
                self.conn.commit()
                
                logging.debug("update WOF:ID %s" % id)

            except Exception, e:
                self.conn.rollback()
                logging.error("failed to update WOF:ID %s, because %s" % (id, e))
                logging.error(feature)
                return False

                # raise Exception, e

        except Exception, e:

                self.conn.rollback()
                logging.error("failed to insert WOF:ID %s, because %s" % (id, e))
                raise Exception, e

        return True

class query(db):


    def get_by_id(self, id):

        cache_key = "id_%s" % id
        cache = self.cache.get(cache_key)

        if cache:
            return cache

        sql = "SELECT id, properties FROM whosonfirst WHERE id=%s"
        params = [id]
        
        self.curs.execute(sql, params)
        row = self.curs.fetchone()

        if row:
            row = self.inflate(row)

        self.cache.set(cache_key, row)
        return row

    def get_by_latlon_recursive(self, lat, lon, **kwargs):

        placetypes = kwargs.get('placetypes', [])
        places = 0

        for p in placetypes:
            
            rsp = self.get_by_latlon(lat, lon, placetype=p)

            for row in rsp:
                places += 1
                yield row

            if places > 0:
                break
                
    def get_by_latlon(self, lat, lon, **kwargs):

        where = []
        params = []

        pt = kwargs.get('placetype', None)

        if not pt == None:
            where.append("placetype=%s")
            params.append(pt)

        where.append("ST_Contains(geom::geometry, ST_SetSRID(ST_Point(%s, %s), 4326))")
        params.extend([lon, lat])

        where = " AND ".join(where)

        sql = "SELECT id, properties FROM whosonfirst WHERE %s" % where

        self.curs.execute(sql, params)
            
        for row in self.curs.fetchall():
            yield self.inflate(row)

    def get_by_extent(self, swlat, swlon, nelat, nelon, **kwargs):

        where = []
        params = []

        where.append("ST_IsValid(geom::geometry)")

        if kwargs.get('placetype', None):
            where.append("placetype=%s")
            params.append(kwargs['placetype'])        
        
        if kwargs.get('contains', False):
            where.append("ST_Contains(ST_MakeEnvelope(%s, %s, %s, %s, 4326), geom::geometry)")
        else:
            where.append("ST_Intersects(ST_MakeEnvelope(%s, %s, %s, %s, 4326), geom::geometry)")

        params.extend([swlon, swlat, nelon, nelat])

        where = " AND ".join(where)

        sql = "SELECT id, properties FROM whosonfirst WHERE %s" % where

        self.curs.execute(sql, params)
            
        for row in self.curs.fetchall():
            yield self.inflate(row)

    def generate_hierarchy(self, feature, **kwargs):

        hier = []

        lat,lon = mapzen.whosonfirst.spatial.feature2reversegeo_coords(feature)
        placetypes = mapzen.whosonfirst.spatial.feature2reversegeo_placetypes(feature)

        while len(placetypes):

            logging.debug("lookup hier for %s" % ",".join(placetypes))
            
            rsp = self.get_by_latlon_recursive(lat, lon, placetypes=placetypes)

            features = []

            for _feature in rsp:
                _props = _feature['properties']
                _hier = _props['wof:hierarchy']
                
                if len(_hier) > 0:
                    features.append(_feature)

            if len(features):
                break

            placetypes = placetypes[1:]

        for pf in features:
            pp = pf['properties']

            if pp.get('wof:hierarchy', False):
                hier.extend(pp['wof:hierarchy'])

        return hier

    # props['wof:hierarchy'] = hier
    # feature['properties'] = props

    def inflate_hierarchies(self, hiers):

        for h in hiers:
            self.inflate_hierarchy(h)

    def inflate_hierarchy(self, hier):

        for k, v in hier.items():
            placetype, ignore = k.split("_id")

            feature = self.get_by_id(v)
            props = feature['properties']
            name = props['wof:name']

            hier[placetype] = name

    def inflate(self, row):

        id, props = row
        props = json.loads(props)

        feature = {
            'type': 'Feature',
            'id': id,
            'properties': props
        }

        return feature

    # new untested stuff - translation:
    # dunno... maybe... it's all still so new and shiny...
    # (20150818/thisisaaronland)

    def breaches(self, data, **kwargs):

        # this assumes an 'inflated' row which has been 'append_geometry'-ed
        # (20150818/thisisaaronland)

        if not data.get('geometry', False):
            yield

        geom = data['geometry']
        props = data['properties']

        geom = geojson.dumps(geom)

        where = []
        params = []

        where.append("placetype=%s")
        params.append(props['wof:placetype'])

        where.append("ST_Intersects(geom, ST_GeomFromGeoJSON(%s))")
        params.append(geom)

        where = " AND ".join(where)

        sql = "SELECT id, properties FROM whosonfirst WHERE %s" % where    
        self.curs.execute(sql, params)
            
        for row in self.curs.fetchall():
            yield self.inflate(row)

    def append_geometry(self, data):

        sql = "SELECT ST_AsGeoJSON(geom) FROM whosonfirst WHERE id=%s"
        params = [data['id']]
        
        self.curs.execute(sql, params)
        row = self.curs.fetchone()

        if not row:
            return False

        geom = row[0]
        geom = geojson.loads(geom)
            
        data['geometry'] = geom
        return True

if __name__ == '__main__':

    import sys
    import optparse

    opt_parser = optparse.OptionParser()

    opt_parser.add_option('-c', '--config', dest='config', action='store', default=None, help='')
    opt_parser.add_option('-l', '--latlong', dest='latlon', action='store_true', default=None, help='')
    opt_parser.add_option('-b', '--bbox', dest='bbox', action='store_true', default=None, help='')
    opt_parser.add_option('-p', '--placetype', dest='placetype', action='store', default=None, help='')

    opt_parser.add_option('-v', '--verbose', dest='verbose', action='store_true', default=False, help='Be chatty (default is false)')
    options, args = opt_parser.parse_args()

    if options.verbose:	
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    cfg = ConfigParser.ConfigParser()
    cfg.read(options.config)

    dsn = spatial.cfg2dsn(cfg, 'spatial')
    db = query(dsn)

    args = args[0].split(",")

    if options.latlon:

        if len(args) != 2:
            logging.error("...")
            sys.exit()

        lat, lon = map(float, args)
        
        placetype = options.placetype

        rsp = db.get_by_latlon(lat, lon, placetype=options.placetype)

    elif options.bbox:

        if len(args) != 4:
            logging.error("...")
            sys.exit()

        swlat, swlon, nelat, nelon = map(float, args)
        
        placetype = options.placetype

        rsp = db.get_by_extent(swlat, swlon, nelat, nelon, placetype=options.placetype)
    
    else:
        logging.error("Invalid query")
        sys.exit()

    for feature in rsp:
        props = feature['properties']
        # hier = props['wof:hierarchy']
        # db.inflate_hierarchies(hier)

        print "%s %s" % (props['wof:id'], props['wof:name'])
