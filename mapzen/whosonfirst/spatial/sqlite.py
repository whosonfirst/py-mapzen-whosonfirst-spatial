import mapzen.whosonfirst.spatial
import time
import logging
import sqlite3
import json
import mapzen.whosonfirst.hierarchy
import mapzen.whosonfirst.utils
import os
import math
import subprocess

class spatialite(mapzen.whosonfirst.spatial.base):

    def __init__(self, **kwargs):
        
        #read in sqlite dump directly
        dsn = kwargs.get("dsn", "/Users/stephen.epps/Desktop/sqlite-db/whosonfirst-data-latest.db")
        conn = sqlite3.connect(dsn)
        conn.enable_load_extension(True)
        conn.execute('SELECT load_extension("mod_spatialite.dylib")')

        self.conn = conn
        self.curs = conn.cursor()

    def point_in_polygon(self, lat, lon, **kwargs):

        sql = "SELECT id FROM geometries WHERE ST_Within(GeomFromText('POINT(%0.6f %0.6f)'), geom) AND rowid IN (SELECT pkid FROM idx_geometries_geom WHERE xmin < %0.6f AND xmax > %0.6f AND ymin < %0.6f AND ymax > %0.6f)" % (lon, lat, lon, lon, lat, lat)

        params = []

        t1 = time.time()

        try:
            self.curs.execute(sql, params)
        except Exception, e:
            self.conn.rollback()
            logging.error("query failed, because %s" % e)
            return

        t2 = time.time()
        ttx = t2 - t1

        logging.debug("[spatial][spatialit][pip] time to execute query (point-in-polygon for %s,%s) : %s" % (lat, lon, ttx))

        for row in self.curs.fetchall():
            row = self.inflate_row(row)

            if not row:
                logging.debug("[spatial][spatialite][pip] failed to inflate row")
                continue

            yield row

    def inflate_row(self, row):

        wofid = row[0]

        sql = "SELECT body FROM geojson WHERE id = ?"
        params = [ wofid ]

        self.curs.execute(sql, params)
        row = self.curs.fetchone()

        feature = json.loads(row[0])
        return feature
        
    def intersects(self, feature, **kwargs):

        props = feature["properties"]
        wof_id = props["wof:id"]

        page = kwargs.get('page', 1)
        per_page = kwargs.get('per_page', 5000)

        offset = (page - 1) * per_page

        where, params = self._where(feature, **kwargs)

        sql = "SELECT id, parent_id, placetype_id, meta, ST_AsGeoJSON(geom), ST_AsGeoJSON(centroid) FROM whosonfirst WHERE " + " AND " . join(where)

        # OMG PLEASE MAKE THIS BETTER SOMEHOW...

        filters = kwargs.get("filters", {})

        if filters.get("wof:parent_id", None):
            sql += " OR parent_id=%s"

            # OMG SO DUMB...
            params = list(params)
            params.append(filters["wof:parent_id"])
            params = tuple(params)

        # https://www.postgresql.org/docs/9.6/static/queries-limit.html
        sql += " LIMIT %s OFFSET %s" % (per_page, offset)

        logging.debug("[spatial][postgis][intersects] %s" % sql)

        t1 = time.time()

        self.curs.execute(sql, params)

        t2 = time.time()
        ttx = t2 - t1

        logging.debug("[spatial][postgis][intersects] time to execute query (find intersecting for %s): %s" % (wof_id, ttx))

        for row in self.curs.fetchall():

            row = self.inflate_row(row, **kwargs)

            if not row:
                continue

            yield row

    def intersects_paginated(self, feature, **kwargs):

        props = feature["properties"]
        wof_id = props["wof:id"]

        page = kwargs.get('page', 1)
        per_page = kwargs.get('per_page', 5000)

        where, params = self._where(feature, **kwargs)

        sql = "SELECT COUNT(id) FROM whosonfirst WHERE " + " AND " . join(where)

        t1 = time.time()

        logging.debug("[spatial][postgis][intersects_paginated] %s" % sql)

        try:
            self.curs.execute(sql, params)
        except Exception, e:
            self.conn.rollback()
            logging.error("query failed, because %s" % e)
            return

        t2 = time.time()
        ttx = t2 - t1

        logging.debug("[spatial][postgis][intersects_paginated] time to execute query (count intersecting for %s) : %s" % (wof_id, ttx))

        row = self.curs.fetchone()

        logging.debug("status %s" % self.curs.statusmessage)

        count = row[0]
        page_count = 1

        if count > per_page:

            count = float(count)
            per_page = float(per_page)

            page_count = math.ceil(count / per_page)
            page_count = int(page_count)

        logging.info("[spatial][postgis][intersects_paginated] count: %s (%s pages (%s))" % (count, page_count, page))

        while page <= page_count:

            logging.info("[spatial][postgis][intersects_paginated] %s results page %s/%s" % (count, page, page_count))

            kwargs['per_page'] = per_page
            kwargs['page'] = page

            for row in self.intersects(feature, **kwargs):

                yield row

            page += 1

    def row_to_feature(self, row, **kwargs):

        wofid = row["properties"]["wof:id"]
        parent_id = row["properties"]["wof:parent_id"]
        centroid = [ row["properties"]["geom:longitude"], row["properties"]["geom:latitude"] ]
        props = row["properties"]

        if row["geometry"]:

            geom = row["geometry"]

        else:

            logging.warning("[spatial][postgis][row_to_feature] failed to parse geom (%s) for %s, because %s" % (geom, wofid, e))

        if not centroid:

            logging.warning("[spatial][postgis][row_to_feature] failed to parse centroid (%s) for %s, because %s" % (centroid, wofid, e))

        if not geom and not centroid:

            logging.error("[spatial][postgis][row_to_feature] can't parse either geom or centroid xxxx for %s" % wofid)
            raise Exception, "bunk geometry for %s" % wofid

        if not geom:

            geom = centroid

        if not centroid:

            shp = shapely.geometry.asShape(geom)
            coords = shp.centroid

            props["geom:longitude"] = coords.x
            props["geom:latitude"] = coords.y

        return { 'type': 'Feature', 'geometry': geom, 'properties': props }

    def _where (self, feature, **kwargs): 

        where = []
        params = []

        # because venues

        if kwargs.get('use_centroid', False):

            geom = feature['geometry']
            str_geom = json.dumps(geom)
            
            if kwargs.get("buffer", None):

                where = [
                    "ST_Intersects(ST_Buffer(ST_GeomFromGeoJSON(%s)," + str(kwargs.get("buffer")) + "), centroid)",
                ]

            else:

                where = [
                    "ST_Intersects(ST_GeomFromGeoJSON(%s), centroid)",
                ]

            params = [
                str_geom
            ]            

        else:

            geom = feature['geometry']
            str_geom = json.dumps(geom)

            params = [
                str_geom
            ]

            if kwargs.get("check_centroid", None) and kwargs.get("buffer", None):

                where = [
                    "(ST_Intersects(ST_Buffer(ST_GeomFromGeoJSON(%s), " + str(kwargs.get("buffer")) + "), geom) OR ST_Intersects(ST_Buffer(ST_GeomFromGeoJSON(%s), " + str(kwargs.get("buffer")) + "), geom))"
                ]

                params.append(str_geom)

            elif kwargs.get("check_centroid", None):

                where = [
                    "(ST_Intersects(ST_GeomFromGeoJSON(%s), geom) OR ST_Intersects(ST_GeomFromGeoJSON(%s), centroid))",
                ]

                params.append(str_geom)

            elif kwargs.get("buffer", None):

                where = [
                    "ST_Intersects(ST_Buffer(ST_GeomFromGeoJSON(%s), " + str(kwargs.get("buffer")) + "), geom)",
                ]

            else:

                where = [
                    "ST_Intersects(ST_GeomFromGeoJSON(%s), geom)",
                ]

        filters = kwargs.get("filters", {})

        for k, v in filters.items():

            # pending https://github.com/whosonfirst/go-whosonfirst-pgis/issues/4
            # see notes in inflate_row (20170731/thisisaaronland)

            if k == "wof:is_ceased":
                logging.debug("[spatial][postgis][where] BANDAID drop wof:is_ceased from query")
                continue

            k = k.replace("wof:", "")

            logging.debug("[spatial][postgis][where] %s=%s" % (k, v))

            where.append("%s=" % k + "%s")
            params.append(v)

        return where, tuple(params)
 
    def index_feature(self, feature, **kwargs):

        index_tool = kwargs.get("index_tool", "/usr/local/bin/wof-pgis-index")
        data_root = kwargs.get("data_root", None)
        debug = kwargs.get("debug", False)

        if data_root == None:
            raise Exception, "You forgot to set data_root in the constructor"

        props = feature["properties"]
        wofid = props["wof:id"]

        repo = props.get("wof:repo", None)

        if repo == None:
            logging.error("%s is missing a wof:repo property" % wofid)
            raise Exception, "Missing wof:repo property"

        root = os.path.join(data_root, repo)
        data = os.path.join(root, "data")
        
        path = mapzen.whosonfirst.uri.id2abspath(data, wofid)

        cmd = [
            index_tool,
            "-pgis-database", self.pg_database,
            "-pgis-host", self.pg_host,
            "-pgis-user", self.pg_username,
        ]

        if self.pg_password:

            cmd.extend([
                "-pgis-password", self.pg_password
            ])
        
        if debug:
            cmd.append("-debug")

        cmd.extend([
            "-mode", "files",
            path
        ])
    
        logging.info("[spatial][postgis][index] %s" % " ".join(cmd))
        
        out = subprocess.check_output(cmd)

        if out:
            logging.debug("[spatial][postgis][index] %s" % out)

        return repo

