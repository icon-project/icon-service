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

import re
import hashlib
from collections import Iterable
from typing import Any


def int_to_bytes(n: int) -> bytes:
    length = (n.bit_length() + 8) // 8
    return n.to_bytes(length, byteorder='big', signed=True)


def is_lowercase_hex_string(value: str) -> bool:
    """Check whether value is hexadecimal format or not

    :param value: text
    :return: True(lowercase hexadecimal) otherwise False
    """

    try:
        result = re.match('[0-9a-f]+', value)
        return len(result.group(0)) == len(value)
    except:
        pass

    return False


def sha3_256(data: bytes) -> bytes:
    return hashlib.sha3_256(data).digest()


def to_camel_case(snake_str: str) -> str:
    str_array = snake_str.split('_')
    return str_array[0] + ''.join(sub.title() for sub in str_array[1:])


def integers_to_hex(res: Any) -> Iterable:
    if isinstance(res, dict):
        for k, v in res.items():
            if isinstance(v, dict):
                res[k] = integers_to_hex(v)
            elif isinstance(v, list):
                res[k] = integers_to_hex(v)
            elif isinstance(v, int):
                res[k] = hex(v)
    elif isinstance(res, list):
        for k, v in enumerate(res):
            if isinstance(v, dict):
                res[k] = integers_to_hex(v)
            elif isinstance(v, list):
                res[k] = integers_to_hex(v)
            elif isinstance(v, int):
                res[k] = hex(v)
    elif isinstance(res, int):
        res = hex(res)
    return res


def make_response(result: Any):
    if check_error_response(result):
        return result
    elif isinstance(result, (dict, list, int)):
        return integers_to_hex(result)


def check_error_response(result: Any):
    return isinstance(result, dict) and result.get('error')


def make_error_response(code: Any, message: str):
    return {'error': {'code': integers_to_hex(int(code)), 'message': message}}
