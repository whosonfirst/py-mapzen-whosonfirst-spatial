import mapzen.whosonfirst.spatial
import mapzen.whosonfirst.placetypes
import mapzen.whosonfirst.utils

import logging
import os
import json

import requests

# as in the wof-pip-server this is part of go-whosonfirst-pip-v2

class pip (mapzen.whosonfirst.spatial.base):

    def __init__(self, **kwargs):

        mapzen.whosonfirst.spatial.base.__init__(self, **kwargs)

        self.scheme = kwargs.get('scheme', 'http')
        self.hostname = kwargs.get('hostname', 'localhost')
        self.port = kwargs.get('port', 8080)

        self.data_root = kwargs.get("data_root", "https://data.whosonfirst.org")

    def point_in_polygon(self, lat, lon, **kwargs):

        filters = kwargs.get("filters", {})

        params = {
            "latitude": lat,
            "longitude": lon
        }

        if filters.get("wof:placetype_id", None):
            pt = mapzen.whosonfirst.placetypes.placetype(filters["wof:placetype_id"])
            params["placetype"] = str(pt)

        existential = (
            "wof:is_supersedes",
            "wof:is_deprecated",
            "wof:is_ceased",
            "wof:is_current",
        )

        for flag in existential:

            if filters.get(flag, None) != None:

                param = flag.replace("wof:", "")
                params[param] = filters[flag]

        endpoint = "%s://%s" % (self.scheme, self.hostname)

        if self.port:
            endpoint = "%s:%s" % (endpoint, self.port)

        try:

            rsp = requests.get(endpoint, params=params)

            if rsp.status_code != requests.codes.ok:
                logging.warning(rsp.content)
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

        wofid = row["wof:id"]
        repo = row["wof:repo"]

        root = self.data_root

        # please sort out using repo when fetching local files

        root = os.path.join(root, "data")

        return mapzen.whosonfirst.utils.load(root, wofid)

# as in an endpoint that implements the whosonfirst-api

class api (mapzen.whosonfirst.spatial.base):

    def __init__(self, **kwargs):

        mapzen.whosonfirst.spatial.base.__init__(self, **kwargs)

        self.endpoint = kwargs.get('endpoint', 'https://api.whosonfirst.org/rest')
        self.access_token = kwargs.get('access_token', None)

        self.data_root = kwargs.get("data_root", "https://data.whosonfirst.org")
        self.insecure = kwargs.get("insecure", False)

    def point_in_polygon(self, lat, lon, **kwargs):

        filters = kwargs.get("filters", {})

        params = {
            "access_token": self.access_token,
            "method": "whosonfirst.places.getByLatLon",
            "latitude": lat,
            "longitude": lon,
        }

        if filters.get("wof:placetype_id", None):
            pt = mapzen.whosonfirst.placetypes.placetype(filters["wof:placetype_id"])
            params["placetype"] = str(pt)

        existential = (
            "wof:is_superseded",
            "wof:is_deprecated",
            "wof:is_ceased",
            "wof:is_current",
        )

        for flag in existential:

            if filters.get(flag, None) != None:

                param = flag.replace("wof:", "")
                params[param] = filters[flag]

        if kwargs.get("extras", None):
            params["extras"] = kwargs["extras"]

        try:

            if self.insecure:
                rsp = requests.get(self.endpoint, params=params, verify=False)
            else:
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

        return mapzen.whosonfirst.utils.load(root, wofid, insecure=self.insecure)
