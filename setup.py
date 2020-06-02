#!/usr/bin/env python
import os
import sys

from setuptools import setup, find_packages

CURRENT_PYTHON = sys.version_info[:3]
REQUIRED_PYTHON = (3, 6, 5)

if CURRENT_PYTHON < REQUIRED_PYTHON:
    sys.stderr.write(
        f"Unsupported Python version* This version of Icon Service requires\n"
        f"Python {'.'.join([str(v) for v in REQUIRED_PYTHON])}, "
        f"but you're trying to install it on Python {'.'.join([str(v) for v in CURRENT_PYTHON])}. ")
    sys.exit(1)

with open('requirements.txt') as requirements:
    requires = list(requirements)

about = {}
with open(os.path.join(os.path.abspath(os.path.dirname(__file__)), 'iconservice/__version__.py'), 'r',
          encoding='utf-8') as f:
    exec(f.read(), about)

extra_requires = {
    "test": [
        "hypothesis>=4.0.0",
        "pytest>=3.6",
        "pytest-cov>=2.5.1",
        "iconsdk",
        "pytest-mock"
    ]
}

setup_options = {
    'name': 'iconservice',
    'version': about['__version__'],
    'description': 'ICON Service for Python',
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
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7'
    ]
}

setup(**setup_options)
