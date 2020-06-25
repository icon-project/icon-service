# -*- coding: utf-8 -*-


from typing import Union, List, Dict, Optional

import pytest
from typing_extensions import TypedDict

from iconservice.base.address import Address
from iconservice.iconscore.typing import (
    get_origin,
    get_args,
)


class Person(TypedDict):
    name: str
    age: int
    single: bool


@pytest.mark.parametrize(
    "type_hint,expected",
    [
        (bool, bool),
        (bytes, bytes),
        (int, int),
        (str, str),
        (Address, Address),
        (List[int], list),
        (List[List[str]], list),
        (Dict, dict),
        (Dict[str, int], dict),
        (Union[int, str], Union),
        (Optional[int], Union),
        (Person, Person),
    ]
)
def test_get_origin(type_hint, expected):
    origin = get_origin(type_hint)
    assert origin == expected


@pytest.mark.parametrize(
    "type_hint,expected",
    [
        (bool, ()),
        (bytes, ()),
        (int, ()),
        (str, ()),
        (Address, ()),
        (List[int], (int,)),
        (List[List[str]], (List[str],)),
        (Dict[str, int], (str, int)),
        (Union[int, str, Address], (int, str, Address)),
        (Optional[int], (int, type(None))),
        (List[Person], (Person,)),
    ]
)
def test_get_args(type_hint, expected):
    args = get_args(type_hint)
    assert args == expected
