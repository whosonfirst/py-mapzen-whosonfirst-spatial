# https://pythonhosted.org/setuptools/setuptools.html#namespace-packages
__import__('pkg_resources').declare_namespace(__name__)

import psycopg2
import geojson
import json
import logging

import mapzen.whosonfirst.placetypes

def cfg2dsn(cfg, sect='spatial'):
        
    db_user = cfg.get(sect, 'db_user')
    db_pswd = cfg.get(sect, 'db_pswd')
    db_host = cfg.get(sect, 'db_host')
    db_name = cfg.get(sect, 'db_name')
    
    dsn = "dbname=%s user=%s password=%s host=%s" % (db_name, db_user, db_pswd, db_host)
    return dsn

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

    def __init__ (self, dsn, **kwargs):

        self.cache = cache()

        # https://pypi.python.org/pypi/psycopg2
        # http://initd.org/psycopg/docs/module.html#psycopg2.connect
        # dsn = "dbname=%s user=%s password=%s host=%s" % (db_name, db_user, db_pswd, db_host)

        self.dsn = dsn

        self.conn = None
        self.curs = None

        # "...so when using a module such as multiprocessing or a forking web deploy method such
        # as FastCGI make sure to create the connections after the fork."
        # http://initd.org/psycopg/docs/usage.html#thread-safety

        if not kwargs.get('defer', False):
            self.connect()

    def connect(self):

        if self.conn:
            return

        conn = psycopg2.connect(self.dsn)
        curs = conn.cursor()

        self.conn = conn
        self.curs = curs

    def __del__(self):
        pass

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

        parent_id = props.get('wof:parent_id', -1)
        parent_id = int(parent_id)

        str_geom = json.dumps(geom)
        
        try:

            if geom['type'] == 'Point':
                sql = "INSERT INTO whosonfirst (id, parent_id, placetype, centroid) VALUES (%s, %s, %s, %s, ST_GeomFromGeoJSON(%s))"
            else:
                sql = "INSERT INTO whosonfirst (id, parent_id, placetype, geom) VALUES (%s, %s, %s, %s, ST_GeomFromGeoJSON(%s))"

            params = (id, parent_id, placetype, str_geom)
            
            self.curs.execute(sql, params)
            self.conn.commit()

            logging.debug("insert WOF:ID %s" % id)

        except psycopg2.IntegrityError, e:

            try:
                self.conn.rollback()
                
                if geom['type'] == 'Point':
                    sql = "UPDATE whosonfirst SET parent_id=%s, placetype=%s, centroid=ST_GeomFromGeoJSON(%s) WHERE id=%s"
                else:
                    sql = "UPDATE whosonfirst SET parent_id=%s, placetype=%s, geom=ST_GeomFromGeoJSON(%s) WHERE id=%s"

                params = (parent_id, placetype, str_props, str_geom, id)
                
                self.curs.execute(sql, params)
                self.conn.commit()
                
                logging.debug("update WOF:ID %s" % id)

            except Exception, e:
                logging.error("failed to update WOF:ID %s, because %s" % (id, e))
                logging.error(feature)

                self.conn.rollback()
                return False

                # raise Exception, e

        except Exception, e:

                logging.error("failed to insert WOF:ID %s, because %s" % (id, e))

                self.conn.rollback()
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

        sql = "SELECT id FROM whosonfirst WHERE %s" % where

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

        sql = "SELECT id FROM whosonfirst WHERE %s" % where

        self.curs.execute(sql, params)
            
        for row in self.curs.fetchall():
            yield self.inflate(row)

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

        where.append("id != %s")
        params.append(props['wof:id'])

        where.append("placetype=%s")
        params.append(props['wof:placetype'])

        where.append("ST_Intersects(geom, ST_GeomFromGeoJSON(%s))")
        params.append(geom)

        where = " AND ".join(where)

        sql = "SELECT id FROM whosonfirst WHERE %s" % where    
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

    def inflate(self, row):
        return row

if __name__ == '__main__':

    """
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
    """
