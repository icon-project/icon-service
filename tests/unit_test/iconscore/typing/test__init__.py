# -*- coding: utf-8 -*-


from typing import Union, List, Dict, Optional

import pytest
from typing_extensions import TypedDict

from iconservice.base.address import Address
from iconservice.iconscore.typing import (
    get_origin,
    get_args,
    isinstance_ex,
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
        ("Address", Address),
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
        (Person, ()),
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


def test_get_args_with_struct():
    expected = {
        "name": str,
        "age": int,
        "single": bool,
    }

    annotations = Person.__annotations__
    assert len(annotations) == len(expected)

    for name, type_hint in annotations.items():
        assert type_hint == expected[name]


@pytest.mark.parametrize(
    "value,_type,expected",
    [
        (True, int, False),
        (False, int, False),
        (0, bool, False),
        (1, bool, False),
        (True, bool, True),
        (False, bool, True),
    ]
)
def test_isinstance_ex(value, _type, expected):
    assert isinstance_ex(value, _type) == expected
