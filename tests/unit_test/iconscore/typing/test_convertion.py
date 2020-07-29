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
from typing import List, Dict, Optional, Union

import pytest
from typing_extensions import TypedDict

from iconservice.base.address import Address, AddressPrefix
from iconservice.base.exception import InvalidParamsException
from iconservice.iconscore.typing.conversion import (
    convert_score_parameters,
    object_to_str,
    str_to_object_in_struct,
)
from iconservice.iconscore.typing.element import normalize_signature
from iconservice.iconscore.typing.element import FunctionMetadata


class User(TypedDict):
    name: str
    age: int
    single: bool
    wallet: Union[Address, None]


class Person(TypedDict):
    name: str
    age: Optional[int]


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
            {"name": "world", "age": 40, "single": False, "wallet": address},
        ],
        "_dict_of_str_and_struct": {
            "a": {"name": "hello", "age": 30, "single": True, "wallet": address},
            "b": {"name": "h", "age": 10, "single": False, "wallet": None},
        },
    }

    params_in_str = object_to_str(params)
    params_in_object = convert_score_parameters(params_in_str, inspect.signature(func))
    assert params_in_object == params


def test_convert_score_parameters_with_insufficient_params():
    class TestScore:
        def func(self, address: Address):
            pass

    params = {}

    with pytest.raises(InvalidParamsException):
        function = FunctionMetadata(TestScore.func)
        convert_score_parameters(params, function.signature)


def test_convert_score_parameters_with_type_mismatch():
    class TestScore:
        def func(self, seed: str):
            pass

    params = {"seed": ["1", "2"]}

    with pytest.raises(InvalidParamsException):
        function = FunctionMetadata(TestScore.func)
        convert_score_parameters(params, function.signature)


@pytest.mark.parametrize(
    "skipped_field,success",
    [
        (None, True),
        ("name", False),
        ("age", False),
        ("single", False),
        ("wallet", False),
    ]
)
def test_str_to_object(skipped_field, success):
    class TestScore:
        def func(self, user: User):
            pass

    address = Address(AddressPrefix.EOA, os.urandom(20))
    params = {
        "user": {
            "name": "hello",
            "age": 30,
            "single": True,
            "wallet": address,
        }
    }

    if skipped_field:
        del params["user"][skipped_field]

    str_params = object_to_str(params)
    sig = normalize_signature(TestScore.func)

    if success:
        ret = convert_score_parameters(str_params, sig)
        assert ret == params
    else:
        with pytest.raises(InvalidParamsException):
            convert_score_parameters(str_params, sig)


@pytest.mark.parametrize(
    "age,success",
    [
        (10, True),
        (None, True),
        (-1, False),
    ]
)
def test_str_to_object_in_struct(age, success):
    expected = {"name": "john"}
    if age is None or age > 0:
        expected["age"] = age

    params = object_to_str(expected)

    if success:
        assert str_to_object_in_struct(params, Person) == expected
    else:
        with pytest.raises(InvalidParamsException):
            str_to_object_in_struct(params, Person)
