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

from typing import List, Dict, Union, Optional, ForwardRef

import pytest
from typing_extensions import TypedDict

from iconservice.base.address import Address
from iconservice.base.exception import IllegalFormatException
from iconservice.iconscore.icon_score_constant import ScoreFlag
from iconservice.iconscore.typing.element import normalize_type_hint
from iconservice.iconscore.typing.element import verify_score_flag


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
