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
from typing import List

import pytest

from iconservice.base.address import Address, AddressPrefix
from iconservice.base.exception import InvalidParamsException
from iconservice.iconscore.typing.verification import (
    verify_internal_call_arguments,
    verify_type_hint,
    bind_arguments,
)
from . import Person


@pytest.mark.parametrize(
    "args,kwargs,valid",
    [
        ((0,), None, True),
        ((0,), {}, True),
        (None, None, False),
        (("hello",), {}, False),
    ]
)
def test_verify_internal_call_arguments(args, kwargs, valid):
    def func(a: int):
        a += 1

    sig = inspect.signature(func)

    if valid:
        verify_internal_call_arguments(sig, args, kwargs)
    else:
        with pytest.raises(InvalidParamsException):
            verify_internal_call_arguments(sig, args, kwargs)


@pytest.mark.parametrize(
    "args,kwargs",
    [
        ((True, b"hello", 0), {}),
        ((), {"a": True, "b": b"bytes", "c": 100}),
        ((), {"a": True, "b": b"bytes", "c": "hello"})
    ]
)
def test_bind_arguments(args, kwargs):
    def func(a: bool, b: bytes, c: int):
        pass

    params = {}
    sig = inspect.signature(func)

    params = bind_arguments(params, sig.parameters, args, kwargs)
    assert len(params) == len(args) + len(kwargs)


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
                "name": "hello", "age": 100, "single": True, "data": b"world",
                "wallets": [Address(AddressPrefix.CONTRACT, os.urandom(20))],
            },
            Person,
            True
        ),
    ]
)
def test_verify_type_hint(value, type_hint, success):
    if success:
        verify_type_hint(value, type_hint)
    else:
        with pytest.raises(expected_exception=(TypeError, KeyError)):
            verify_type_hint(value, type_hint)
