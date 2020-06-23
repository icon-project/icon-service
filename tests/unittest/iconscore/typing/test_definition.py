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

from typing import Dict, List
from typing_extensions import TypedDict

from iconservice.base.address import Address
from iconservice.iconscore.typing.definition import (
    get_input,
    _get_type,
)


class Person(TypedDict):
    name: str
    age: int
    single: bool
    wallet: Address
    data: bytes


def test__get_type():
    types: List[type] = []
    _get_type(List[List[int]], types)
    assert types == [list, list, int]


def test_get_fields_by_type_hints():
    fields = [
        ("name", str),
        ("age", int),
        ("single", bool),
        ("wallet", Address),
        ("data", bytes),
    ]
    expected = [{"name": field[0], "type": field[1].__name__} for field in fields]

    ret = get_fields_from_typed_dict(Person)
    assert ret == expected
