import mapzen.whosonfirst.spatial
import mapzen.whosonfirst.placetypes
import mapzen.whosonfirst.utils

import logging
import os
import json

import requests

class pip (mapzen.whosonfirst.spatial.base):

    def __init__(self, **kwargs):

        mapzen.whosonfirst.spatial.base.__init__(self, **kwargs)

        self.scheme = kwargs.get('scheme', 'https')
        self.hostname = kwargs.get('hostname', 'pip.mapzen.com')
        self.port = kwargs.get('port', None)

        self.data_root = kwargs.get("data_root", "https://whosonfirst.mapzen.com")

    def point_in_polygon(self, lat, lon, **kwargs):

        filters = kwargs.get("filters", {})

        params = {
            "latitude": lat,
            "longitude": lon
        }

        if filters.get("wof:placetype_id", None):
            pt = mapzen.whosonfirst.placetypes.placetype(filters["wof:placetype_id"])
            params["placetype"] = str(pt)

        endpoint = "%s://%s" % (self.scheme, self.hostname)

        if self.port:
            endpoint = "%s:%s" % (endpoint, self.port)        

        try:

            rsp = requests.get(endpoint, params=params)

            if rsp.status_code != requests.codes.ok:
                rsp.raise_for_status()

            data = json.loads(rsp.content)

        except Exception, e:

            logging.error("failed to PIP with %s (%s) because %s" % (endpoint, params, e))
            raise Exception, e

        for row in data:

            if kwargs.get("as_feature", False):
                row = self.row_to_feature(row)

            yield row

    def row_to_feature(self, row):

        # this is what we have to work with... today (20170502/thisisaaronland)
        # {u'Name': u'Utah', u'Deprecated': False, u'Superseded': False, u'Placetype': u'region', u'Offset': -1, u'Id': 85688567}

        wofid = row["Id"]

        root = self.data_root

        # please fix me (as in work out the details)
        # (20170502/thisisaaronland)

        """
        repo = row.get("wof:repo", None)

        if repo:
            root = os.path.join(root, repo)
        """

        root = os.path.join(root, "data")

        return mapzen.whosonfirst.utils.load(root, wofid)

class api (mapzen.whosonfirst.spatial.base):

    def __init__(self, **kwargs):

        mapzen.whosonfirst.spatial.base.__init__(self, **kwargs)

        self.endpoint = kwargs.get('endpoint', 'http://whosonfirst-api.mapzen.com')
        self.api_key = kwargs.get('api_key', None)

        self.data_root = kwargs.get("data_root", "https://whosonfirst.mapzen.com")

    def point_in_polygon(self, lat, lon, **kwargs):

        filters = kwargs.get("filters", {})

        params = {
            "api_key": self.api_key,
            "method": "whosonfirst.places.getByLatLon",
            "latitude": lat,
            "longitude": lon,
        }

        if filters.get("wof:placetype_id", None):
            pt = mapzen.whosonfirst.placetypes.placetype(filters["wof:placetype_id"])
            params["placetype"] = str(pt)

        try:

            rsp = requests.get(self.endpoint, params=params)

            if rsp.status_code != requests.codes.ok:
                rsp.raise_for_status()

            data = json.loads(rsp.content)

        except Exception, e:

            logging.error("failed to PIP with %s (%s) because %s" % (self.endpoint, params, e))
            raise Exception, e

        for row in data["places"] :

            if kwargs.get("as_feature", False):
                row = self.row_to_feature(row)

            yield row

    # intersects - we could call 'whosonfirst.places.getIntersects' here but
    # since that only does bounding boxes it's likely to confuse things since
    # the postgis one assumes polygons... (20170502/thisisaaronland)

    def row_to_feature(self, row):

        wofid = row["wof:id"]
        repo = row["wof:repo"]

        root = self.data_root

        # please sort out using repo when fetching local files

        root = os.path.join(root, "data")

        return mapzen.whosonfirst.utils.load(root, wofid)
