#!/usr/bin/env python
import os

from setuptools import setup, find_packages

requires = [
    'plyvel',
    'jsonpickle',
    'setproctitle'
]

version = os.environ.get('VERSION')

if version is None:
    with open(os.path.join('.', 'VERSION')) as version_file:
        version = version_file.read().strip()

setup_options = {
    'name': 'iconservice',
    'version': version,
    'description': 'iconservice for python',
    'long_description': open('docs/class.md').read(),
    'author': 'ICON foundation',
    'packages': find_packages(exclude=['tests*', 'docs']),
    'package_data': {'iconservice': [
        'icon_service.json',
        'builtin_scores/*/package.json'
    ]},
    'license': "Apache License 2.0",
    'install_requires': requires,
    'entry_points': {
        'console_scripts': [
            'iconservice=iconservice.icon_service_cli:main'
        ],
    },
    'setup_requires': ['pytest-runner'],
    'tests_requires': ['pytest'],
    'classifiers': [
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers', 
        'Intended Audience :: System Administrators',
        'Natural Language :: English',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.6'
    ]
}

setup(**setup_options)
