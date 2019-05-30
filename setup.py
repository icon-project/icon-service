#!/usr/bin/env python
import os

from setuptools import setup, find_packages

with open('requirements.txt') as requirements:
    requires = list(requirements)

version = os.environ.get('VERSION')

extra_requires = {
    "test": [
        "hypothesis>=4.0.0",
        "pytest>=3.6",
        "pytest-cov>=2.5.1"
    ]
}

test_requires = extra_requires['test']

if version is None:
    with open(os.path.join('.', 'VERSION')) as version_file:
        version = version_file.read().strip()

setup_options = {
    'name': 'iconservice',
    'version': version,
    'description': 'ICON Service for python',
    'long_description_content_type': 'text/markdown',
    'long_description': open('README.md').read(),
    'url': 'https://github.com/icon-project/icon-service',
    'author': 'ICON Foundation',
    'author_email': 'foo@icon.foundation',
    'packages': find_packages(exclude=['tests*', 'docs']),
    'package_data': {'iconservice': [
        'icon_service.json',
        'builtin_scores/*/package.json'
    ]},
    'setup_requires': ['pytest-runner'],
    'tests_require': test_requires,
    'license': "Apache License 2.0",
    'install_requires': requires,
    'extras_require': extra_requires,
    'entry_points': {
        'console_scripts': [
            'iconservice=iconservice.icon_service_cli:main'
        ],
    },
    'classifiers': [
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers', 
        'Intended Audience :: System Administrators',
        'Natural Language :: English',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.6'
    ],
    'test_suite': 'tests'
}

setup(**setup_options)
