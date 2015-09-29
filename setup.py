#!/usr/bin/env python

from setuptools import setup, find_packages

packages = find_packages()
desc = open("README.md").read(),

setup(
    name='mapzen.whosonfirst.spatial',
    namespace_packages=['mapzen', 'mapzen.whosonfirst', 'mapzen.whosonfirst.spatial'],
    version='0.03',
    description='Simple Python wrapper for Who\'s On First spatial functionality',
    author='Mapzen',
    url='https://github.com/mapzen/py-mapzen-whosonfirst-spatial',
    install_requires=[
        'psycopg2',
        'geojson',
        'mapzen.whosonfirst.utils',
        ],
    dependency_links=[
        'https://github.com/whosonfirst/py-mapzen-whosonfirst-utils/tarball/master#egg=mapzen.whosonfirst.utils-0.05',
        ],
    packages=packages,
    scripts=[
        'scripts/wof-spatial-index',
        'scripts/wof-spatial-query',
        'scripts/wof-spatial-server.py',
        ],
    download_url='https://github.com/mapzen/py-mapzen-whosonfirst-spatial/releases/tag/v0.03',
    license='BSD')
