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
import logging

from tqdm import tqdm
import requests
from bs4 import BeautifulSoup


logging.basicConfig(level=logging.INFO)


class SkippingError(Exception):
    pass


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

    progress = tqdm(pkgs)
    for pkg in progress:
        resp = requests.get(f'https://pypi.python.org/pypi/{pkg}/json')
        skip = f'skipping {pkg}'
        keep = f'keeping {pkg}'

        try:
            if not resp.status_code == 200:
                raise SkippingError('error retrieving metadata')

            props = resp.json()
            info = props.get('info')

            if not info:
                raise SkippingError('no info')
            
            if not info.get('summary') or info.get('summary') == 'UNKOWN':
                raise SkippingError('no summary')

            if not info.get('classifiers') or not len(info.get('classifiers')):
                raise SkippingError('no classifiers')

        except SkippingError as e:
            reason = str(e)
            progress.set_description(f'{skip}: {reason}')
            continue
        
        progress.set_description(f'{keep}')


