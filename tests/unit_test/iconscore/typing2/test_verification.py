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
from typing import List, Optional, Union

import pytest
from typing_extensions import TypedDict

from iconservice.base.address import Address, AddressPrefix
from iconservice.base.exception import InvalidParamsException
from iconservice.iconscore.typing.verification import (
    verify_internal_call_arguments,
    verify_type_hint,
    merge_arguments,
    set_default_value_to_params,
)


class Person(TypedDict):
    name: str
    age: int
    single: bool
    data: bytes
    wallets: List[Address]


@pytest.mark.parametrize(
    "args,kwargs,valid",
    [
        ((0,), None, True),
        ((0,), {}, True),
        (None, None, False),
        (("hello",), {}, False),
        ((2, None), None, True),
        ((2,), None, True),
        ((2,), {"b": b"world"}, True),
        ((2, b"world"), None, True),
        ((2, b"world"), {}, True),
        ((2, b"world"), {"b": b"\x00"}, False),
        ((2, b"world"), {"c": b"\x00"}, False),
        ((2, b"world", 3), None, False),
    ],
)
def test_verify_internal_call_arguments(args, kwargs, valid):
    def func1(a: int, b: Optional[bytes] = None):
        a += 1

    def func2(a: int, b: Union[bytes, None] = None):
        a += 1

    for func in (func1, func2):
        sig = inspect.signature(func)

        if valid:
            verify_internal_call_arguments(sig, args, kwargs)
        else:
            with pytest.raises(InvalidParamsException):
                verify_internal_call_arguments(sig, args, kwargs)


@pytest.mark.parametrize(
    "args,kwargs,success",
    [
        ((True, b"bytes", 0), {}, True),
        ((), {"a": True, "b": b"bytes", "c": 100}, True),
        ((), {"a": True, "b": b"bytes", "c": "hello"}, True),
        ((True,), {"b": b"bytes", "c": 0}, True),
        ((True, b"bytes"), {"c": "hello"}, True),
        ((True, b"bytes"), {"c": "hello", "d": 0}, False),
        ((True, b"bytes", 0, "hello"), {}, False),
        ((), {"a": True, "b": b"bytes", "c": "hello", "d": 1}, False),
        ((True, b"bytes", 0), {"b": b"bytes2"}, False),
        ((True, b"bytes"), {}, True),
        ((), {"a": False}, True),
        ((True,), {"a": False}, False),
        ((), {}, True),
    ],
)
def test_merge_arguments(args, kwargs, success):
    def func(a: bool, b: bytes, c: int):
        pass

    params = {}
    sig = inspect.signature(func)

    if success:
        merge_arguments(params, sig.parameters, args, kwargs)
        assert len(params) == len(args) + len(kwargs)
    else:
        with pytest.raises(InvalidParamsException):
            merge_arguments(params, sig.parameters, args, kwargs)


@pytest.mark.parametrize(
    "_name,_age,success",
    [
        ("john", 13, True),
        ("", 10, True),
        ("bob", None, True),
        ("", None, True),
        (None, 10, False),
        (None, None, False),
    ],
)
def test_set_default_value_to_params(_name, _age, success):
    default = -1

    def func(name: str, age: int = default):
        pass

    sig = inspect.signature(func)

    params = {}
    expected = {}

    if _name is not None:
        expected["name"] = params["name"] = _name

    if _age is not None:
        expected["age"] = params["age"] = _age
    else:
        expected["age"] = default

    if success:
        set_default_value_to_params(params, sig.parameters)
        assert params == expected
        assert params["age"] == expected["age"]
    else:
        with pytest.raises(InvalidParamsException):
            set_default_value_to_params(params, sig.parameters)


@pytest.mark.parametrize(
    "value,type_hint,success",
    [
        (True, bool, True),
        (False, bool, True),
        (b"bytes", bytes, True),
        (True, int, False),
        (False, int, False),
        (0, int, True),
        (10, int, True),
        (-9, int, True),
        ("hello", str, True),
        (Address.from_prefix_and_int(AddressPrefix.EOA, 0), Address, True),
        ("hxe08a1ded7635bc7b769f4893aef65cf00049377b", Address, False),
        ([True, False], List[bool], True),
        ([True, False], List[int], False),
        ([0, 1, 2], List[int], True),
        ([0, 1, 2], List[str], False),
        (["a", "b", "c"], List[str], True),
        (["a", "b", "c"], List[bool], False),
        (
            {
                "name": "hello",
                "age": 100,
                "single": True,
                "data": b"world",
                "wallets": [Address(AddressPrefix.CONTRACT, os.urandom(20))],
            },
            Person,
            True,
        ),
        (
            {
                "name": "hello",
                "age": False,
                "single": True,
                "data": b"world",
                "wallets": [Address(AddressPrefix.CONTRACT, os.urandom(20))],
            },
            Person,
            False,
        ),
        (
            {
                "name": "hello",
                "age": 50,
                "single": True,
                "wallets": [Address(AddressPrefix.CONTRACT, os.urandom(20))],
            },
            Person,
            False,
        ),
    ],
)
def test_verify_type_hint(value, type_hint, success):
    if success:
        verify_type_hint(value, type_hint)
    else:
        with pytest.raises(expected_exception=(TypeError, InvalidParamsException)):
            verify_type_hint(value, type_hint)
