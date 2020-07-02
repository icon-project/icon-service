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
from typing import List, Dict, Union, Optional, ForwardRef

import pytest
from typing_extensions import TypedDict

from iconservice.base.address import Address, AddressPrefix
from iconservice.base.exception import IllegalFormatException, InvalidParamsException
from iconservice.iconscore.icon_score_constant import ScoreFlag
from iconservice.iconscore.typing.element import (
    normalize_type_hint,
    verify_score_flag,
    check_parameter_default_type,
    verify_internal_call_arguments,
)


class Person(TypedDict):
    name: str
    age: int


@pytest.mark.parametrize(
    "type_hint,expected",
    [
        (bool, bool),
        (bytes, bytes),
        (int, int),
        (str, str),
        (Address, Address),
        (list, None),
        (List, None),
        (List[bool], List[bool]),
        (List[bytes], List[bytes]),
        (List[int], List[int]),
        (List[str], List[str]),
        (List[Address], List[Address]),
        (List[Person], List[Person]),
        (List["Person"], None),
        (List["Address"], None),
        (dict, None),
        (Dict, None),
        (Dict[str, bool], Dict[str, bool]),
        (Dict[str, bytes], Dict[str, bytes]),
        (Dict[str, int], Dict[str, int]),
        (Dict[str, str], Dict[str, str]),
        (Dict[str, Address], Dict[str, Address]),
        (Dict[str, Person], Dict[str, Person]),
        (Dict[int, str], None),
        (Dict[str, "Address"], None),
        (Optional[bool], Union[bool, None]),
        (Optional[bytes], Union[bytes, None]),
        (Optional[int], Union[int, None]),
        (Optional[str], Union[str, None]),
        (Optional[Address], Union[Address, None]),
        (Optional[List[str]], Union[List[str], None]),
        (Optional[Dict[str, str]], Union[Dict[str, str], None]),
        (Optional[Dict], None),
        (Union[str], str),
        (Union[str, int], None),
        (Union[bool, None], Union[bool, None]),
        (Union[bytes, None], Union[bytes, None]),
        (Union[int, None], Union[int, None]),
        (Union[str, None], Union[str, None]),
        (Union[None, str], Union[str, None]),
        (Union[Address, None], Union[Address, None]),
        (Union[Person, None], Union[Person, None]),
        (Union["Person", None], None),
        (ForwardRef("bool"), None),
        (ForwardRef("bytes"), None),
        (ForwardRef("int"), None),
        (ForwardRef("str"), None),
        (ForwardRef("Address"), None),
        (Optional[ForwardRef("Address")], None),
        (Dict[str, ForwardRef("Address")], None),
        (Union[ForwardRef("Person"), None], None),
    ]
)
def test_normalize_abnormal_type_hint(type_hint, expected):
    try:
        ret = normalize_type_hint(type_hint)
    except IllegalFormatException:
        ret = None

    assert ret == expected


@pytest.mark.parametrize(
    "flag,success",
    [
        (ScoreFlag.READONLY, False),
        (ScoreFlag.PAYABLE, False),
        (ScoreFlag.FALLBACK, False),
        (ScoreFlag.READONLY | ScoreFlag.PAYABLE, False),
        (ScoreFlag.READONLY | ScoreFlag.FALLBACK, False),
        (ScoreFlag.EXTERNAL | ScoreFlag.FALLBACK, False),
        (ScoreFlag.EXTERNAL | ScoreFlag.EVENTLOG, False),
        (ScoreFlag.EXTERNAL | ScoreFlag.INTERFACE, False),
        (ScoreFlag.EVENTLOG | ScoreFlag.READONLY, False),
        (ScoreFlag.INTERFACE | ScoreFlag.PAYABLE, False)
    ]
)
def test_verify_score_flag(flag, success):
    if success:
        verify_score_flag(flag)
    else:
        with pytest.raises(IllegalFormatException):
            verify_score_flag(flag)


@pytest.mark.parametrize(
    "type_hint,default,success",
    [
        (bool, 0, False),
        (bytes, "hello", False),
        (int, "world", False),
        (int, False, False),
        (str, True, False),
        (Address, 1, False),
        (str, None, True),
        (bool, False, True),
        (bytes, b"hello", True),
        (int, 1, True),
        (str, "hello", True),
        (Address, Address.from_prefix_and_int(AddressPrefix.EOA, 1), True),
        (str, None, True),
        (Union[int, None], None, True),
        (Union[None, int], 0, False),
        (Person, None, True),
        (List[int], None, True),
        (Union[List[Person], None], None, True),
        (Dict[str, int], None, True),
        (Union[Dict[str, int], None], None, True),
        (Optional[bool], None, True),
        (Optional[bytes], None, True),
        (Optional[int], None, True),
        (Optional[str], None, True),
        (Optional[Address], None, True),
    ]
)
def test_check_parameter_default_type(type_hint, default, success):
    if success:
        check_parameter_default_type(type_hint, default)
    else:
        with pytest.raises(InvalidParamsException):
            check_parameter_default_type(type_hint, default)


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
        pass

    sig = inspect.signature(func)

    if valid:
        verify_internal_call_arguments(sig, args, kwargs)
    else:
        with pytest.raises(InvalidParamsException):
            verify_internal_call_arguments(sig, args, kwargs)
