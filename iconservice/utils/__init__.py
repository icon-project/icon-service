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


def sha3_256(data: bytes) -> bytes:
    return hashlib.sha3_256(data).digest()


def int_to_bytes(n: int) -> bytes:
    length = (n.bit_length() + 8) // 8
    return n.to_bytes(length, byteorder='big', signed=True)
