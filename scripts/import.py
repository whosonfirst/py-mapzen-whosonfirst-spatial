#!/usr/bin/env python

import sys
import os.path
import logging

import mapzen.whosonfirst.utils

# see notes in (local) whosonfirst.py about namespaces
# and anger (20150723/thisisaaronland)

import whosonfirst

if __name__ == '__main__':

    import optparse
    import ConfigParser

    opt_parser = optparse.OptionParser()

    opt_parser.add_option('-s', '--source', dest='source', action='store', default='None', help='')
    opt_parser.add_option('-c', '--config', dest='config', action='store', default='None', help='')

    # opt_parser.add_option('-d', '--database', dest='database', action='store', default='whosonfirst_pip', help='')
    # opt_parser.add_option('-u', '--username', dest='username', action='store', default='postgres', help='')
    # opt_parser.add_option('-p', '--password', dest='password', action='store', default=None, help='')

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

    db_host = cfg.get('whosonfirst', 'db_host')
    db_name = cfg.get('whosonfirst', 'db_name')
    db_user = cfg.get('whosonfirst', 'db_user')
    db_pswd = cfg.get('whosonfirst', 'db_pswd')

    dsn = "host=%s dbname=%s user=%s password=%s" % (db_host, db_name, db_user, db_pswd)
    db = whosonfirst.lookup(dsn)

    source = os.path.abspath(options.source)
    crawl = mapzen.whosonfirst.utils.crawl(source, inflate=True)

    for feature in crawl:
        logging.debug("import feature %s" % feature.get('id', "UNKNOWN"))

        geom = feature['geometry']

        if geom['type'] == 'Point':
            logging.warning("skipping because %s is a point" % id)
            continue

        db.import_feature(feature)

    sys.exit()
        
