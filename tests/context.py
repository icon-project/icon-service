# -*- coding: utf-8 -*-

import sys
import os

"""The only purpose of this file is to make it easy to write unittest codes.
"""


parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)
    sys.path.insert(0, os.path.join(parent_dir, 'icx'))
