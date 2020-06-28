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

import inspect
import os
from typing import List, Dict

import pytest
from typing_extensions import TypedDict

from iconservice.base.address import Address, AddressPrefix
from iconservice.base.exception import InvalidParamsException
from iconservice.iconscore.typing.conversion import (
    convert_score_parameters,
    object_to_str,
)
from iconservice.iconscore.typing.element import Function


class User(TypedDict):
    name: str
    age: int
    single: bool
    wallet: Address


def test_convert_score_parameters():
    def func(
            _bool: bool,
            _bytes: bytes,
            _int: int,
            _str: str,
            _address: Address,
            _list: List[int],
            _dict: Dict[str, int],
            _struct: User,
            _list_of_struct: List[User],
            _dict_of_str_and_struct: Dict[str, User],
    ):
        pass

    address = Address.from_data(AddressPrefix.EOA, os.urandom(20))

    params = {
        "_bool": True,
        "_bytes": b"hello",
        "_int": 100,
        "_str": "world",
        "_address": address,
        "_list": [0, 1, 2, 3, 4, 5],
        "_dict": {"0": 0, "1": 1, "2": 2},
        "_struct": {"name": "hello", "age": 30, "single": True, "wallet": address},
        "_list_of_struct": [
            {"name": "hello", "age": 30, "single": True, "wallet": address},
            {"name": "world", "age": 40, "single": False},
        ],
        "_dict_of_str_and_struct": {
            "a": {"name": "hello", "age": 30, "single": True, "wallet": address},
            "b": {"age": 27},
        },
    }

    params_in_str = object_to_str(params)
    params_in_object = convert_score_parameters(params_in_str, inspect.signature(func))
    assert params_in_object == params


def test_convert_score_parameters_with_insufficient_parameters():
    class TestScore:
        def func(self, address: Address):
            pass

    params = {}

    with pytest.raises(InvalidParamsException):
        function = Function(TestScore.func)
        convert_score_parameters(params, function.signature)
