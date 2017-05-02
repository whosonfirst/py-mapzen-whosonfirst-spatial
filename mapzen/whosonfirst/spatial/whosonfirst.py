import mapzen.whosonfirst.spatial

import logging
import json
import requests

class pip (mapzen.whosonfirst.spatial.base):

    def __init__(self, **kwargs):

        mapzen.whosonfirst.spatial.base.__init__(self, **kwargs)

        self.scheme = kwargs.get('scheme', 'https')
        self.hostname = kwargs.get('hostname', 'pip.mapzen.com')
        self.port = kwargs.get('port', None)

    def point_in_polygon(self, lat, lon, **kwargs):

        endpoint = "%s://%s" % (self.scheme, self.hostname)

        if self.port:
            endpoint = "%s:%s" % (endpoint, self.port)

        params = { "latitude": lat, "longitude": lon }
        
        for k, v in kwargs.items():
            params[k] = v

        rsp = requests.get(endpoint, params=params)

        data = json.loads(rsp.content)

        for row in data:
            yield row

    def row_to_feature(self, row):

        # {u'Name': u'Utah', u'Deprecated': False, u'Superseded': False, u'Placetype': u'region', u'Offset': -1, u'Id': 85688567}

        geom = {}

        props = {
            "wof:id": row['Id'],
            "wof:name": row['Name'],
            "wof:placetype": row['Placetype'],
        }

        feature = {
            "type": "Feature",
            "geometry": geom,
            "properties": props,
        }

        return feature
