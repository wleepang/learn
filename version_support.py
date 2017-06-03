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
from tqdm import tqdm
import requests
from bs4 import BeautifulSoup

if __name__ == '__main__':
    resp = requests.get('https://pypi.python.org/simple')
    if not resp.status_code == 200:
        raise RuntimeError('package index returned {}'.format(resp.status_code))

    soup = BeautifulSoup(resp.text, 'html.parser')

    pkgs = [link.get('href') for link in tqdm(soup.find_all('a'))]
    progress = tqdm(pkgs)
    for pkg in progress:
        resp = requests.get(f'https://pypi.python.org/pypi/{pkg}/json')
        skip = f'skipping {pkg}'
        keep = f'keeping {pkg}'
        if not resp.status_code == 200:
            progress.set_description(f'{skip}: error retrieving metadata')
            continue

        props = resp.json()
        info = props.get('info')
        if not info:
            progress.set_description(f'{skip}: no info')
            continue
        
        if not info.get('summary') or info.get('summary') == 'UNKOWN':
            progress.set_description(f'{skip}: no summary')
            continue

        if not info.get('classifiers') or not len(info.get('classifiers')):
            progress.set_description(f'{skip}: no classifiers')
            continue
        
        progress.set_description(f'{keep}')


