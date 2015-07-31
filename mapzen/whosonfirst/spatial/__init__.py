# https://pythonhosted.org/setuptools/setuptools.html#namespace-packages
__import__('pkg_resources').declare_namespace(__name__)

import psycopg2
import json
import logging

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

        conn = psycopg2.connect(dsn)
        curs = conn.cursor()

        self.conn = conn
        self.curs = curs

class index(db):

    def import_feature(self, feature):

        geom = feature['geometry']
        props = feature['properties']

        # GRRRRNNNNN..... maybe? 

        if geom['type'] == 'Polygon':
            geom['coordinates'] = [ geom['coordinates'] ]
            geom['type'] = 'MultiPolygon'

        placetype = props['wof:placetype']
        id = props['wof:id']
        id = int(id)

        if placetype == 'planet':
            return False

        str_props = json.dumps(props)
        str_geom = json.dumps(geom)
        
        try:

            sql = "INSERT INTO whosonfirst (id, placetype, properties, geom) VALUES (%s, %s, %s, ST_GeomFromGeoJSON(%s))"
            params = (id, placetype, str_props, str_geom)
            
            self.curs.execute(sql, params)
            self.conn.commit()

            logging.debug("insert WOF:ID %s" % id)

        except psycopg2.IntegrityError, e:

            try:
                self.conn.rollback()
            
                sql = "UPDATE whosonfirst SET placetype=%s, properties=%s, geom=ST_GeomFromGeoJSON(%s) WHERE id=%s"
                params = (placetype, str_props, str_geom, id)
                
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

        if kwargs.get('placetype', None):
            where.append("placetype=%s")
            params.append(kwargs['placetype'])

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

if __name__ == '__main__':

    import sys
    import optparse

    opt_parser = optparse.OptionParser()

    opt_parser.add_option('-d', '--database', dest='database', action='store', default='whosonfirst_pip', help='')
    opt_parser.add_option('-u', '--username', dest='username', action='store', default='postgres', help='')
    # opt_parser.add_option('-p', '--password', dest='password', action='store', default=None, help='')

    opt_parser.add_option('-l', '--latlong', dest='latlon', action='store_true', default=None, help='')
    opt_parser.add_option('-b', '--bbox', dest='bbox', action='store_true', default=None, help='')
    opt_parser.add_option('-p', '--placetype', dest='placetype', action='store', default=None, help='')

    opt_parser.add_option('-v', '--verbose', dest='verbose', action='store_true', default=False, help='Be chatty (default is false)')
    options, args = opt_parser.parse_args()

    if options.verbose:	
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    dsn = "dbname=%s user=%s" % (options.database, options.username)
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
