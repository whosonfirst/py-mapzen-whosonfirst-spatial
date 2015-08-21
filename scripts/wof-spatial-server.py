#!/usr/bin/env python
# -*-python-*-

import os
import re
import logging

import mapzen.whosonfirst.spatial as spatial
import mapzen.whosonfirst.utils as utils
import mapzen.whosonfirst.placetypes as placetypes
import mapzen.whosonfirst.whereami as whereami

import flask
import werkzeug
import werkzeug.security
from werkzeug.contrib.fixers import ProxyFix

app = flask.Flask('WOF_LOOKUP')
app.wsgi_app = ProxyFix(app.wsgi_app)

logging.basicConfig(level=logging.INFO)

@app.before_request
def init():

    query_dsn = os.environ.get('WOF_SPATIAL_DSN', None)
    query_db = spatial.query(query_dsn)

    flask.g.query_db = query_db

@app.after_request
def after_request(response):
  response.headers.add('Access-Control-Allow-Origin', '*')
  response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
  response.headers.add('Access-Control-Allow-Methods', 'GET')
  return response

@app.route("/")
def lookup():

    lat = flask.request.args.get('latitude', None)
    lon = flask.request.args.get('longitude', None)
    bbox = flask.request.args.get('bbox', None)
    tile = flask.request.args.get('tile', None)

    placetype = flask.request.args.get('placetype', None)

    if placetype:

        placetype = placetype.split(",")

        for p in placetype:

            if not placetypes.is_valid_placetype(p):
                flask.abort(400)

    if lat and lon:
        rsp = by_latlon(lat, lon, placetype)

    # TO DO - ensure min/max bbox size by placetype

    elif bbox:
        rsp = by_extent(bbox, placetype)

    # TO DO – ensure zoom (min/max bbox size) by placetype

    elif tile:
        
        if not re.match(r'^\d+/\d+/\d+$', tile):
            flask.abort(400)

        rsp = by_tile(tile, placetype)

    else:
        flask.abort(400)

    return enresponsify(rsp)

def by_latlon(lat, lon, placetypes):

    lat = float(lat)
    lon = float(lon)

    if not is_valid_latitude(lat):
        flask.abort(400)

    if not is_valid_longitude(lon):
        flask.abort(400)

    # basically belongs to...

    if not placetypes:
        rsp = flask.g.query_db.get_by_latlon(lat, lon)
    else:
        rsp = flask.g.query_db.get_by_latlon_recursive(lat, lon, placetypes=placetypes)        

    return rsp

def by_extent(bbox, placetypes):

    # sudo make a "recursive" version of me...

    if placetypes:
        placetype = placetypes[0]
    else:
        placetype = None

    bbox = bbox.split(",")
    swlat, swlon, nelat, nelon = map(float, bbox)

    if not is_valid_latitude(swlat) or not is_valid_latitude(nelat):
        flask.abort(400)

    if not is_valid_longitude(swlon) or not is_valid_longitude(nelon):
        flask.abort(400)

    rsp = flask.g.query_db.get_by_extent(swlat, swlon, nelat, nelon, placetype=placetype)
    return rsp

def by_tile(tile, placetype):

    rsp = whereami.whereami(tile)
    sw = rsp.get('southwest').split(' ')
    ne = rsp.get('northeast').split(' ')

    bbox = []
    bbox.extend(sw)
    bbox.extend(ne)
    bbox = ",".join(bbox)

    return by_extent(bbox, placetype)

def enresponsify(rsp):

    features = []

    for feature in rsp:

        props = feature['properties']
        id = props['wof:id']

        path = utils.id2relpath(id)
        props['wof:path'] = path

        feature['properties'] = props
        features.append(feature)

    rsp = {'type': 'FeatureCollection', 'features': features}
    return flask.jsonify(rsp)

def is_valid_latitude(lat):
    lat = float(lat)

    if lat < -90.0:
        return False

    if lat > 90.0:
        return False

    return True

def is_valid_longitude(lon):
    lon = float(lon)

    if lon < -180.0:
        return False

    if lon > 180.0:
        return False

    return True

if __name__ == '__main__':

    import sys
    import optparse
    import ConfigParser

    opt_parser = optparse.OptionParser()

    opt_parser.add_option('-p', '--port', dest='port', action='store', default=8888, help='')
    opt_parser.add_option('-c', '--config', dest='config', action='store', default=None, help='')
    opt_parser.add_option('-s', '--section', dest='sect', action='store', default='whosonfirst', help='')

    opt_parser.add_option('-v', '--verbose', dest='verbose', action='store_true', default=False, help='Be chatty (default is false)')
    options, args = opt_parser.parse_args()

    if options.verbose:	
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    if not os.path.exists(options.config):
        logging.error("Missing config file")
        sys.exit()

    cfg = ConfigParser.ConfigParser()
    cfg.read(options.config)

    dsn = spatial.cfg2dsn(cfg, options.sect)
    os.environ['WOF_SPATIAL_DSN'] = dsn

    port = int(options.port)
    app.run(port=port)
