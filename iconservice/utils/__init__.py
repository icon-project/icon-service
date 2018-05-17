# -*- coding: utf-8 -*-

# Copyright 2017-2018 theloop Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Utilities

Functions and classes in this module don't have any external dependencies.
"""

import logging
import re
import hashlib
import struct
from functools import wraps
import threading


def is_lowercase_hex_string(value: str) -> bool:
    """Check whether value is hexadecimal format or not

    :param value: text
    :return: True(lowercase hexadecimal) otherwise False
    """

    try:
        result = re.match('[0-9a-f]+', value)
        return len(result.group(0)) == len(value)
    except Exception:
        pass

    return False


def trace(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        logging.debug('%s(%r, %r) start' % (func.__name__, args, kwargs))
        result = func(*args, **kwargs)
        logging.debug('%s() end ret(%r)' % (func.__name__, result))

        return result
    return wrapper


def sha3_256(data: bytes) -> bytes:
    return hashlib.sha3_256(data).digest()


def int_to_bytes(n: int) -> bytes:
    length = (n.bit_length() + 7) // 8
    if n <= 0:
        length += 1
    return n.to_bytes(length, byteorder='big', signed=True)
