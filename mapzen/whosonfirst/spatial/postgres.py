import mapzen.whosonfirst.spatial
import mapzen.whosonfirst.uri
import mapzen.whosonfirst.placetypes

import math
import os
import logging
import json
import subprocess
import time

# basically if you're going to have to install psycopg2 then installing
# shapely shouldn't be a big deal either... (20170502/thisisaaronland)

import psycopg2
import shapely.geometry

# see also: https://github.com/whosonfirst/go-whosonfirst-pgis

class postgis(mapzen.whosonfirst.spatial.base):

    def __init__(self, **kwargs):

        self.debug = kwargs.get("debug", False)

        self.pg_database = kwargs.get("dbname", "whosonfirst")
        self.pg_username = kwargs.get("username", "whosonfirst")
        self.pg_password = kwargs.get("password", None)
        self.pg_host = kwargs.get("host", "localhost")

        # https://pythonhosted.org/psycopg2/

        dsn = "dbname=%s user=%s host=%s" % (self.pg_database, self.pg_username, self.pg_host)

        if self.pg_password:
            dsn = "%s password=%s" % (dsn, self.pg_password)

        conn = psycopg2.connect(dsn)

        self.conn = conn
        self.curs = conn.cursor()

    def point_in_polygon(self, lat, lon, **kwargs):

        centroid = { 'type': 'Point', 'coordinates': [ lon, lat ] }
        str_centroid = json.dumps(centroid)

        where = [
            "ST_Intersects(geom, ST_GeomFromGeoJSON(%s))",
        ]

        params = [
            str_centroid
        ]

        filters = kwargs.get("filters", {})

        for k, v in filters.items():

            # pending https://github.com/whosonfirst/go-whosonfirst-pgis/issues/4
            # see notes in inflate_row (20170731/thisisaaronland)

            if k == "wof:is_ceased":
                logging.debug("[spatial][postgis][pip] BANDAID drop wof:is_ceased from query")
                continue

            k = k.replace("wof:", "")

            where.append("%s=" % k + "%s")
            params.append(v)

        params = tuple(params)

        t1 = time.time()

        sql = "SELECT id, parent_id, placetype_id, meta, ST_AsGeoJSON(geom), ST_AsGeoJSON(centroid) FROM whosonfirst WHERE " + " AND " . join(where)
        logging.debug("[spatial][postgis][pip] %s with args: %s" % (sql, list(params)))

        """
        because sometimes this happens... 
        see also: https://whosonfirst.mapzen.com/spelunker/id/136253037
        not convinced this is the problem but it's a good possibility...
        (20170824/thisisaaronland)

        DEBUG:root:[spatial][postgis][pip] SELECT id, parent_id, placetype_id, meta, ST_AsGeoJSON(geom), ST_AsGeoJSON(centroid) FROM whosonfirst WHERE ST_Intersects(geom, ST_GeomFromGeoJSON(%s)) AND is_superseded=%s AND is_deprecated=%s AND placetype_id=%s with args: ['{"type": "Point", "coordinates": [7.509687, 46.730219]}', 0, 0, '102312335']
ERROR:root:query failed, because BOOM! Could not generate outside point!
        """

        try:
            self.curs.execute(sql, params)
        except Exception, e:
            self.conn.rollback()
            logging.error("query failed, because %s" % e)
            return

        t2 = time.time()
        ttx = t2 - t1

        logging.debug("[spatial][postgis][pip] time to execute query (point-in-polygon for %s,%s) : %s" % (lat, lon, ttx))

        for row in self.curs.fetchall():

            row = self.inflate_row(row, **kwargs)

            if not row:
                logging.debug("[spatial][postgis][pip] failed to inflate row")
                continue

            yield row
        
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

        self.curs.execute(sql, params)

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

    def inflate_row(self, row, **kwargs):

        logging.debug("[spatial][postgis][inflate_row] %s" % kwargs)

        # BANDAID WARNING

        # pending https://github.com/whosonfirst/go-whosonfirst-pgis/issues/4
        # wof:is_ceased is set in mz-wof-hierarchy and frankly is a confusing
        # label but it means `WHERE is_ceased=0` and gets set in _where below
        # it happen sometimes... maybe we will change it but not today
        # (20170731/thisisaaronland)

        filters = kwargs.get("filters", {})

        logging.error("[spatial][postgis][inflate_row] BANDAID has wof:is_ceased: %s" % filters.has_key("wof:is_ceased"))
        logging.error("[spatial][postgis][inflate_row] BANDAID is wof:is_ceased == 0: %s ('%s')" % (filters.get("wof:is_ceased", None) == 0, filters.get("wof:is_ceased", None)))

        if kwargs.get("as_feature", False):

            try:
                row = self.row_to_feature(row)
            except Exception, e:
                logging.error("[spatial][postgis][inflate_row] failed to convert row to feature")
                return None

            # BANDAID - see above

            if filters.has_key("wof:is_ceased") and filters["wof:is_ceased"] == 0:

                wofid = row["properties"]["wof:id"]

                try:

                    data_root = kwargs.get("data_root", "/usr/local/data")
                    repo = row["properties"]["wof:repo"]                    
                    root = os.path.join(data_root, repo)
                    data = os.path.join(root, "data")
                    
                    f = mapzen.whosonfirst.utils.load(data, wofid)

                except Exception, e:
                    logging.error("[spatial][postgis][inflate_row] BANDAID failed to load feature (%s) from source" % wofid)
                    return None

                cessation = f["properties"].get("edtf:cessation", "uuuu")
                logging.error("[spatial][postgis][inflate_row] BANDAID cessation for %s is '%s'" % (wofid, cessation))

                if not cessation in ("", "u", "uuuu"):
                    logging.debug("[spatial][postgis][inflate_row] BANDAID record %s has been ceased, skipping" % wofid)
                    return None
        
        # BANDAID - see above
        
        elif filters.has_key("wof:is_ceased") and filters["wof:is_ceased"] == 0:

            try:
                tmp = self.row_to_feature(row)
            except Exception, e:
                logging.error("[spatial][postgis][inflate_row] BANDAID failed to convert row to feature")
                return None

            wofid = tmp["properties"]["wof:id"]

            try:

                data_root = kwargs.get("data_root", "/usr/local/data")                
                repo = tmp["properties"]["wof:repo"]                    
                root = os.path.join(data_root, repo)
                data = os.path.join(root, "data")
                
                f = mapzen.whosonfirst.utils.load(data, wofid)

            except Exception, e:
                logging.error("[spatial][postgis][inflate_row] BANDAID failed to load feature (%s) from source" % wofid)
                return None
                
            cessation = f["properties"].get("edtf:cessation", "uuuu")

            if not cessation in ("", "u", "uuuu"):
                logging.debug("[spatial][postgis][inflate_row] BANDAID record has been ceased, skipping")
                return None

        else:
            pass

        return row

    def index_feature(self, feature, **kwargs):

        # please implement me in python below... maybe?
        # (20170503/thisisaaronland)

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
        
    def row_to_feature(self, row, **kwargs):

        wofid, parent_id, placetype_id, meta, geom, centroid = row

        props = json.loads(meta)

        if geom:

            try:
                geom = json.loads(geom)
            except Exception, e:
                logging.warning("[spatial][postgis][row_to_feature] failed to parse geom (%s) for %s, because %s" % (geom, wofid, e))

        if centroid:

            try:
                centroid = json.loads(centroid)
                lon, lat = centroid['coordinates']
            except Exception, e:
                logging.warning("[spatial][postgis][row_to_feature] failed to parse centroid (%s) for %s, because %s" % (centroid, wofid, e))

        if not geom and not centroid:

            logging.error("[spatial][postgis][row_to_feature] can't parse either geom or centroid xxxx for %s" % wofid)
            raise Exception, "bunk geometry for %s" % wofid

        if not geom:
            geom = centroid

        if not centroid:

            shp = shapely.geometry.asShape(geom)
            coords = shp.centroid

            lat = coords.y
            lon = coords.x

        pt = mapzen.whosonfirst.placetypes.placetype(placetype_id)

        props['wof:id'] = wofid
        props['wof:parent_id'] = parent_id
        props['wof:placetype'] = str(pt)

        props['geom:latitude'] = lat
        props['geom:longitude'] = lon

        return { 'type': 'Feature', 'geometry': geom, 'properties': props }
