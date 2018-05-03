# THIS IS WET PAINT AND PROBABLY DOESN'T WORK YET
# (20180416/thisisaaronland)

import mapzen.whosonfirst.spatial
import time
import logging
import sqlite3
import json

class spatialite(mapzen.whosonfirst.spatial.base):

    def __init__(self, **kwargs):

        dsn = kwargs.get("dsn", "/Users/stephen.epps/Desktop/sqlite-db/whosonfirst-data-latest.db")
        conn = sqlite3.connect(dsn)

        conn.enable_load_extension(True)

        conn.execute('SELECT load_extension("mod_spatialite.dylib")')
        # if we load a real DB we don't need to init it
        #conn.execute('SELECT InitSpatialMetaData();')

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
        raise Exception, "Method 'row_to_feature' not implemented by this class."

    def intersects_paginated(self, feature, **kwargs):
        raise Exception, "Method 'row_to_feature' not implemented by this class."

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

    def index_feature(self, feature, **kwargs):
        raise Exception, "Method 'index_feature' not implemented by this class."
