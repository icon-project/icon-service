# -*- coding: utf-8 -*-
# Copyright 2020 ICON Foundation
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

from typing import List

from iconservice.base.exception import IllegalFormatException
from . import get_origin, get_args, is_struct
from .conversion import is_base_type


def get_input(name: str, type_hint: type) -> dict:
    _input = {"name": name}

    types: List[type] = []
    _get_type(type_hint, types)
    _input["type"] = types_to_name(types)

    return _input


def _get_type(type_hint: type, types: List[type]):
    origin: type = get_origin(type_hint)
    types.append(origin)

    if origin is list:
        args = get_args(type_hint)
        if len(args) != 1:
            raise IllegalFormatException(f"Invalid type: {type_hint}")

        _get_type(args[0], types)


def types_to_name(types: List[type]) -> str:
    def func():
        for _type in types:
            if _type is list:
                yield "[]"
            elif is_base_type(_type):
                yield _type.__name__
            elif is_struct(_type):
                yield "struct"

    return "".join(func())


def get_fields(type_hint: type):
    """Returns fields info from struct

    :param type_hint: struct type
    :return:
    """

    annotations = getattr(type_hint, "__annotations__", None)
    if annotations is None:
        raise IllegalFormatException(f"Not struct type: {type_hint}")

    # annotations is a dictionary containing key-type pair which has field_name as a key and type as a value
    return [{"name": k, "type": v.__name__} for k, v in annotations.items()]
