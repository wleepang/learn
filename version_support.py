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
from collections import defaultdict

import requests
from bs4 import BeautifulSoup


logging.basicConfig(level=logging.INFO)


class SkippingError(Exception):
    pass


def get_versions(classifiers):
    versions = list(filter(
        lambda x: re.search('Python :: \d\.\d', x),
        classifiers
    ))

    if versions:
        versions = list(map(
            lambda x: float(re.split('\s::\s', x)[2]),
            versions
        ))

    return versions


def read_package(pkg):
    resp = requests.get(f'https://pypi.python.org/pypi/{pkg}/json')
    skip = f'skip {pkg}'
    keep = f'keep {pkg}'

    versions = []
    try:
        if not resp.status_code == 200:
            raise SkippingError('error retrieving metadata')

        props = resp.json()
        info = props.get('info')

        if not info:
            raise SkippingError('no info')
        
        # summary = info.get('summary')
        # if not summary or summary == 'UNKOWN':
        #     raise SkippingError('no summary')
        
        classifiers = info.get('classifiers')
        if not classifiers or not len(classifiers):
            raise SkippingError('no classifiers')

        logging.info(f'{keep}')
        versions = get_versions(classifiers)

    except SkippingError as e:
        reason = str(e)
        logging.info(f'{skip}: {reason}')

    return versions
    

PKG_INFO = {}
VERSIONS = defaultdict(lambda: 0)

if __name__ == '__main__':

    logging.info('retrieving packages list')
    resp = requests.get('https://pypi.python.org/simple')
    if not resp.status_code == 200:
        logging.error('could not get packages list')
        raise RuntimeError('package index returned {}'.format(resp.status_code))

    logging.info('parsing packages list')
    soup = BeautifulSoup(resp.text, 'html.parser')
    pkgs = [link.get('href') for link in soup.find_all('a')]
    logging.info('{} packages found'.format(len(pkgs)))

    # for pkg in pkgs:
    #     versions = read_package(pkg)

    with cf.ThreadPoolExecutor() as executor:
        futures = {executor.submit(read_package, pkg): pkg for pkg in pkgs}
        for future in cf.as_completed(futures):
            pkg = futures[future]
            versions = future.result()

            PKG_INFO[pkg] = versions

            if len(versions):
                for version in versions:
                    VERSIONS[version] += 1
            else:
                VERSIONS['unknown'] += 1

