import mapzen.whosonfirst.spatial
import mapzen.whosonfirst.uri
import mapzen.whosonfirst.placetypes

import math
import os
import logging
import json
import subprocess

# basically if you're going to have to install psycopg2 then installing
# shapely shouldn't be a big deal either... (20170502/thisisaaronland)

import psycopg2
import shapely.geometry

# see also: https://github.com/whosonfirst/go-whosonfirst-pgis

class postgis(mapzen.whosonfirst.spatial.base):

    def __init__(self, **kwargs):

        self.debug = kwargs.get("debug", False)

        dbname = kwargs.get("dbname", "whosonfirst")
        username = kwargs.get("username", "whosonfirst")
        password = kwargs.get("password", "")
        host = kwargs.get("host", "localhost")

        # https://pythonhosted.org/psycopg2/

        dsn = "dbname=%s user=%s password=%s host=%s" % (dbname, username, password, host)
        conn = psycopg2.connect(dsn)

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

            k = k.replace("wof:", "")

            where.append("%s=" % k + "%s")
            params.append(v)

        params = tuple(params)

        sql = "SELECT id, parent_id, placetype_id, meta, ST_AsGeoJSON(geom), ST_AsGeoJSON(centroid) FROM whosonfirst WHERE " + " AND " . join(where)
        logging.debug(sql)

        self.curs.execute(sql, params)

        for row in self.curs.fetchall():

            if kwargs.get("as_feature", False):
                row = self.row_to_feature(row)

            yield row
        
    def intersects(self, feature, **kwargs):

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

        logging.debug(sql)

        self.curs.execute(sql, params)

        for row in self.curs.fetchall():

            if kwargs.get("as_feature", False):

                try:
                    row = self.row_to_feature(row)
                except Exception, e:
                    logging.error("failed to 'intersects' for %s because %s" % (row[0], e))
                    continue

            yield row

    def intersects_paginated(self, feature, **kwargs):

        page = kwargs.get('page', 1)
        per_page = kwargs.get('per_page', 5000)

        where, params = self._where(feature, **kwargs)

        sql = "SELECT COUNT(id) FROM whosonfirst WHERE " + " AND ".join(where)

        logging.debug(sql)

        self.curs.execute(sql, params)

        row = self.curs.fetchone()
        count = row[0]

        page_count = 1

        if count > per_page:

            count = float(count)
            per_page = float(per_page)

            page_count = math.ceil(count / per_page)
            page_count = int(page_count)

        logging.info("count intersects: %s (%s pages (%s))" % (count, page_count, page))

        while page <= page_count:

            logging.info("%s results page %s/%s" % (count, page, page_count))

            kwargs['per_page'] = per_page
            kwargs['page'] = page

            for row in self.intersects(feature, **kwargs):
                yield row

            page += 1

    def index_feature(self, feature, **kwargs):

        # please implement me in python below... maybe?
        # (20170503/thisisaaronland)

        index_tool = kwargs.get("index_tool", "/usr/local/bin/wof-pgis-index")

        data_root = kwargs.get("data_root", None)
        debug = kwargs.get("debug", False)

        if data_root == None:
            raise Exception, "You forgot to set data_root in the constructor"

        props = feature["properties"]
        repo = props["wof:repo"]

        root = os.path.join(data_root, repo)
        data = os.path.join(root, "data")

        wofid = props["wof:id"]
        path = mapzen.whosonfirst.uri.id2abspath(data, wofid)

        cmd = [
            index_tool
        ]

        if debug:
            cmd.append("-debug")

        cmd.extend([
            "-mode", "files",
            path
        ])
    
        logging.info(" ".join(cmd))
        
        out = subprocess.check_output(cmd)
        logging.debug(out)

        return repo

        """
        geom = feature['properties']
        props = feature['properties']

        wofid = props['wof:id']
        parent_id = props['wof:parent_id']

        pt = mapzen.whosonfirst.placetypes.placetype(props['wof:placetype'])
        placetype_id = pt.id()

        name = props['wof:name']
        country = props.get('wof:country', 'XX')
        repo = props['wof:repo']
        hier = props.get('wof:hierarchy', [])

        is_superseded = 0
        is_deprecated = 0

        if len(props.get('wof:superseded_by', [])):
            is_superseded = 1

        if not props.get('etdf:deprecated', '') in ('', 'uuuu'):
            is_deprecated = 1

        meta = {
            'wof:hierarchy': hier,
            'wof:repo': repo,
            'wof:name': name,
            'wof:country': country,
        }

        pass
        """

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

            if kwargs.get("buffer", None):

                where = [
                    "ST_Intersects(ST_Buffer(ST_GeomFromGeoJSON(%s), " + str(kwargs.get("buffer")) + "), geom)",
                ]

            else:

                where = [
                    "ST_Intersects(ST_GeomFromGeoJSON(%s), geom)",
                ]

            params = [
                str_geom
            ]

        filters = kwargs.get("filters", {})

        for k, v in filters.items():

            k = k.replace("wof:", "")

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
                logging.warning("failed to parse geom (%s) for %s, because %s" % (geom, wofid, e))

        if centroid:

            try:
                centroid = json.loads(centroid)
                lon, lat = centroid['coordinates']
            except Exception, e:
                logging.warning("failed to parse centroid (%s) for %s, because %s" % (centroid, wofid, e))

        if not geom and not centroid:

            logging.error("can't parse either geom or centroid xxxx")
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
