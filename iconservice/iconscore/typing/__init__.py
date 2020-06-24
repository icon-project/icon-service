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

__all__ = (
    "is_base_type",
    "get_origin",
    "get_args",
    "is_struct",
)

from typing import Tuple, Union, Type

from iconservice.base.address import Address

BaseObject = Union[bool, bytes, int, str, 'Address']
BaseObjectType = Type[BaseObject]

BASE_TYPES = {bool, bytes, int, str, Address}
TYPE_NAME_TO_TYPE = {_type.__name__: _type for _type in BASE_TYPES}


def is_base_type(value: type) -> bool:
    try:
        return value in BASE_TYPES
    except:
        return False


def name_to_type(type_name: str) -> BaseObjectType:
    return TYPE_NAME_TO_TYPE[type_name]


def get_origin(type_hint: type) -> type:
    """
    Dict[str, int].__origin__ == dict
    List[str].__origin__ == list

    :param type_hint:
    :return:
    """
    if is_base_type(type_hint) or is_struct(type_hint):
        return type_hint

    return getattr(type_hint, "__origin__", None)


def get_args(type_hint: type) -> Tuple[type, ...]:
    return getattr(type_hint, "__args__", ())


def is_struct(type_hint) -> bool:
    try:
        return type_hint.__class__.__name__ == "_TypedDictMeta"
    except:
        return False
