# -*- coding: utf-8 -*-

# Copyright 2018 ICON Foundation
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

import hashlib
import json
import re
from collections import namedtuple
from enum import Flag
from typing import Any, Union, Optional
import inspect

from iconcommons import Logger

from ..icon_constant import BUILTIN_SCORE_ADDRESS_MAPPER, DATA_BYTE_ORDER, ICX_IN_LOOP


def int_to_bytes(n: int) -> bytes:
    length = byte_length_of_int(n)
    return n.to_bytes(length, byteorder=DATA_BYTE_ORDER, signed=True)


def bytes_to_int(v: bytes) -> int:
    return int.from_bytes(v, byteorder=DATA_BYTE_ORDER, signed=True)


def byte_length_of_int(n: int):
    if n < 0:
        # adds 1 because `bit_length()` always returns a bit length of absolute-value of `n`
        n += 1
    return (n.bit_length() + 8) // 8


def bytes_to_hex(data: Optional[bytes], prefix: str = "0x") -> str:
    if not isinstance(data, bytes):
        return "None"

    return f"{prefix}{data.hex()}"


def icx_to_loop(icx: int) -> int:
    return icx * ICX_IN_LOOP


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


def check_error_response(result: Any):
    return isinstance(result, dict) and result.get('error')


def get_main_type_from_annotations_type(annotations_type: type) -> type:
    main_type = None

    if hasattr(annotations_type, '__origin__') and annotations_type.__origin__ is not Union:
        return annotations_type.__origin__

    # in python 3.7, _subs_tree method has excluded.
    if hasattr(annotations_type, '__args__'):
        annotations = annotations_type.__args__
        for annotation_type in annotations:
            if annotation_type is not None:
                main_type = annotation_type
                break
    else:
        main_type = annotations_type
    return main_type


def is_builtin_score(score_address: str) -> bool:
    return score_address in BUILTIN_SCORE_ADDRESS_MAPPER.values()


def is_all_flag_on(src_flags: Flag, flag: Flag) -> bool:
    return src_flags & flag == flag


def is_any_flag_on(src_flags: Flag, flag: Flag) -> bool:
    return bool(src_flags & flag)


def set_flag(src_flags: Flag, flag: Flag, on: bool) -> Flag:
    if on:
        src_flags |= flag
    else:
        src_flags &= ~flag

    return src_flags


ContextEngine = namedtuple("engine", "deploy fee icx iiss prep issue inv")
ContextStorage = namedtuple("storage", "deploy fee icx iiss prep issue meta rc inv")


def print_log_with_level(log_level: str, msg: str, tag: str):
    logging_function = getattr(Logger, log_level)
    logging_function(msg, tag)


class BytesToHexJSONEncoder(json.JSONEncoder):
    """Used to make logging message more readable

    """
    def default(self, obj):
        if isinstance(obj, bytes):
            return bytes_to_hex(obj)

        return json.JSONEncoder.default(self, obj)
