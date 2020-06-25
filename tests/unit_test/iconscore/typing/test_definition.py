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

from inspect import signature
from typing import List

import pytest
from typing_extensions import TypedDict

from iconservice.base.address import Address
from iconservice.iconscore.typing.definition import (
    _get_inputs,
    _split_type_hint,
    _get_eventlog
)


class Delegation(TypedDict):
    address: Address
    value: int


class Person(TypedDict):
    name: str
    age: int
    single: bool
    wallet: Address
    data: bytes


class Company(TypedDict):
    name: str
    delegation: Delegation
    workers: List[Person]


def test_get_inputs_with_list_of_struct():
    expected = [
        {
            "name": "_persons",
            "type": "[]struct",
            "fields": [
                {"name": "name", "type": "str"},
                {"name": "age", "type": "int"},
                {"name": "single", "type": "bool"},
                {"name": "wallet", "type": "Address"},
                {"name": "data", "type": "bytes"},
            ]
        }
    ]

    def func(_persons: List[Person]):
        pass

    sig = signature(func)
    inputs = _get_inputs(sig.parameters)
    assert inputs == expected


def test_get_inputs_with_list_of_struct_nesting_struct():
    expected = [
        {
            "name": "_company",
            "type": "struct",
            "fields": [
                {"name": "name", "type": "str"},
                {
                    "name": "delegation",
                    "type": "struct",
                    "fields": [
                        {"name": "address", "type": "Address"},
                        {"name": "value", "type": "int"},
                    ]
                },
                {
                    "name": "workers",
                    "type": "[]struct",
                    "fields": [
                        {"name": "name", "type": "str"},
                        {"name": "age", "type": "int"},
                        {"name": "single", "type": "bool"},
                        {"name": "wallet", "type": "Address"},
                        {"name": "data", "type": "bytes"},
                    ]
                },
            ]
        }
    ]

    def func(_company: Company):
        pass

    sig = signature(func)
    inputs = _get_inputs(sig.parameters)
    assert inputs == expected


@pytest.mark.parametrize(
    "type_hint,expected",
    [
        (bool, [bool]),
        (bytes, [bytes]),
        (int, [int]),
        (str, [str]),
        (Address, [Address]),
        (List[int], [list, int]),
        (List[List[str]], [list, list, str]),
        (List[List[List[Person]]], [list, list, list, Person]),
    ]
)
def test_split_type_hint(type_hint, expected):
    types: List[type] = _split_type_hint(type_hint)
    assert types == expected


def test__get_eventlog():
    expected = {
        "name": "ICXTransfer",
        "type": "eventlog",
        "inputs": [
            {"name": "to", "type": "Address", "indexed": True},
            {"name": "amount", "type": "int", "indexed": False},
            {"name": "data", "type": "bytes", "indexed": False},
        ]
    }

    indexed_args_count = 1
    def ICXTransfer(to: Address, amount: int, data: bytes):
        pass

    ret = _get_eventlog(ICXTransfer.__name__, signature(ICXTransfer), indexed_args_count)
    assert ret == expected
