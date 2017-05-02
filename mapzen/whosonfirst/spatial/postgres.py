import mapzen.whosonfirst.spatial
import logging

import json
import psycopg2

# see also: https://github.com/whosonfirst/go-whosonfirst-pgis

class postgis(mapzen.whosonfirst.spatial.base):

    def __init__(self):

        self.debug = kwargs.get("debug", False)

        dbname = kwargs.get("dbname", "whosonfirst")
        username = kwargs.get("username", "whosonfirst")
        password = kwargs.get("password", "")
        host = kwargs.get("host", "localhost")

        # https://pythonhosted.org/psycopg2/

        dsn = "dbname=%s user=%s password=%s host=%s" % (dbname, username, password, host)
        conn = psycopg2.connect(dsn)

        self.curs = conn.cursor()

    def point_in_polygon(self, lat, lon, placetype, **kwargs):

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

        sql = "SELECT id, parent_id, placetype_id, meta, ST_AsGeoJSON(geom), ST_AsGeoJSON(centroid) FROM whosonfirst WHERE " + " AND ".join(where)
        logging.debug(sql)

        self.curs.execute(sql, params)

        for row in self.curs.fetchall():

            """
            if kwargs.get("as_feature", False):

                try:
                    row = self.row_to_feature(row)
                except Exception, e:
                    logging.error("failed to point in polygon for %s because %s" % (row[0], e))
                    continue
            """

            yield row
        
    def intersects(self, feature, **kwargs):

        page = kwargs.get('page', 1)
        per_page = kwargs.get('per_page', 5000)

        offset = (page - 1) * per_page

        where, params = self._where(feature, **kwargs)

        sql = "SELECT id, parent_id, placetype_id, meta, ST_AsGeoJSON(geom), ST_AsGeoJSON(centroid) FROM whosonfirst WHERE " + " AND ".join(where)

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
        
