#!/usr/bin/env python

import sys
import os.path
import logging

import mapzen.whosonfirst.utils

# see notes in (local) whosonfirst.py about namespaces
# and anger (20150723/thisisaaronland)

import whosonfirst

if __name__ == '__main__':

    import sys
    import optparse

    opt_parser = optparse.OptionParser()

    opt_parser.add_option('-s', '--source', dest='source', action='store', default='None', help='')
    opt_parser.add_option('-d', '--database', dest='database', action='store', default='whosonfirst_pip', help='')
    opt_parser.add_option('-u', '--username', dest='username', action='store', default='postgres', help='')
    # opt_parser.add_option('-p', '--password', dest='password', action='store', default=None, help='')

    opt_parser.add_option('-v', '--verbose', dest='verbose', action='store_true', default=False, help='Be chatty (default is false)')
    options, args = opt_parser.parse_args()

    if options.verbose:	
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    dsn = "dbname=%s user=%s" % (options.database, options.username)
    db = whosonfirst.lookup(dsn)

    source = os.path.asbpath(source)
    crawl = mapzen.whosonfirst.utils.crawl(source, inflate=True)

    for feature in crawl:
        db.import_feature(feature)

    sys.exit()
        
