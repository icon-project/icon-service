#!/usr/bin/env python
from setuptools import setup, find_packages
from iconservice import __version__

requires = [
    'plyvel',
    'jsonpickle',
    'coloredlogs',
    'aio_pika'
]

setup_options = {
    'name': 'iconservice', 
    'version': __version__,
    'description': 'iconservice for python',
    'long_description': open('docs/class.md').read(),
    'author': 'ICON foundation',
    'packages': find_packages(exclude=['tests*','docs']),
    'license': "Apache License 2.0",
    'install_requires': requires,
    'entry_points': {
        'console_scripts': [
            'iconservice=iconservice:main'
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
    ]
}

setup(**setup_options)
