#!/usr/bin/env python

"""
A script to gather data about python packages and the
versions of python they support

Method:
Uses PyPI as a list of python packages.  This is easier to mine
than GitHub and represents the repository that would most commonly
be used when users install packages - i.e. via `pip`

Lists published packages via PyPI's `simple` API:
https://pypi.python.org/simple/

Iterate through the list and retrieve package metadata using the
JSON API:
https://pypi.python.org/pypi/<package>/json

Filter the list for packages with the following metadata properties:
- info.summary != null or "UNKNOWN"
- info.classifiers.length > 0
- info.classifiers contains
    - Development Status >= 4 and <= 6 (may be too stringent)
    - Programming Language :: Python :: <version>
"""
import re
import logging
import concurrent.futures as cf
import multiprocessing as mp
import json
from collections import defaultdict, namedtuple
from pprint import pprint
from datetime import datetime

import requests
from bs4 import BeautifulSoup


logging.basicConfig(level=logging.INFO)
MAX_PROCESSES = mp.cpu_count()*8

class SkippingError(Exception):
    pass


PkgInfo = namedtuple('PkgInfo', ['versions', 'error'])

def get_versions(classifiers):
    versions = [
        c for c in classifiers if re.search('Python :: \d(\.\d)?', c)
    ]

    if versions:
        versions = [
            re.split('\s::\s', v)[2].strip()
            for v in versions
        ]

    return list(set(versions))


def read_package(pkg, id_=None):
    resp = requests.get(f'https://pypi.python.org/pypi/{pkg}/json')
    if id_:
        id_ = f'[{id_:7d}] '

    skip = f'{id_}skip {pkg}'
    keep = f'{id_}keep {pkg}'

    versions = []
    error = None
    try:
        if not resp.status_code == 200:
            raise SkippingError('error retrieving metadata')

        props = resp.json()
        info = props.get('info')

        if not info:
            raise SkippingError('no info')

        classifiers = info.get('classifiers')
        if not classifiers or not len(classifiers):
            raise SkippingError('no classifiers')

        logging.info(f'{keep}')
        versions = get_versions(classifiers)

    except SkippingError as e:
        error = str(e)
        logging.info(f'{skip}: {error}')

    return PkgInfo(versions, error)


PKG_INFO = {}
VERSIONS = defaultdict(lambda: 0)

if __name__ == '__main__':

    time_start = datetime.now()

    logging.info('started: {}'.format(time_start.strftime('%F %X')))
    logging.info('retrieving packages list')
    resp = requests.get('https://pypi.python.org/simple')
    if not resp.status_code == 200:
        logging.error('could not get packages list')
        raise RuntimeError('package index returned {}'.format(resp.status_code))

    logging.info('parsing packages list')
    soup = BeautifulSoup(resp.text, 'html.parser')
    pkgs = [link.get('href') for link in soup.find_all('a')]
    logging.info('{} packages found'.format(len(pkgs)))

    time_parse_start = datetime.now()
    with cf.ThreadPoolExecutor(MAX_PROCESSES) as executor:
        futures = {executor.submit(read_package, pkg, id_): pkg for id_, pkg in enumerate(pkgs)}
        for future in cf.as_completed(futures):
            pkg = futures[future]
            info = future.result()

            PKG_INFO[pkg] = info
            VERSIONS['total'] += 1
            if len(info.versions):
                VERSIONS['known'] += 1
                for version in info.versions:
                    VERSIONS[version] += 1
            else:
                if not info.error:
                    VERSIONS['nd_unk'] += 1
                else:
                    VERSIONS['na'] += 1

    time_end = datetime.now()
    time_parse_elapsed = time_end - time_parse_start
    time_elapsed = time_end - time_start

    with open('PKG_INFO.json', 'w') as pkgfile, open('VERSIONS.json', 'w') as verfile:
        json.dump(PKG_INFO, pkgfile)
        json.dump(VERSIONS, verfile)

    logging.info('finished: {}'.format(time_end.strftime('%F %X')))
    logging.info('parsing elapsed: {}'.format(str(time_parse_elapsed)))
    logging.info('total elapsed: {}'.format(str(time_elapsed)))

    pprint(VERSIONS)
