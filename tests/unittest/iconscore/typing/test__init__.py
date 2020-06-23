# -*- coding: utf-8 -*-


from typing import List, Dict, Optional, Union, get_type_hints
from typing_extensions import TypedDict

import pytest

from iconservice.iconscore.typing import get_origin, get_args
from iconservice.base.address import Address


class Person(TypedDict):
    name: str
    age: int
    single: bool


TYPE_HINTS = (
    # bool, bytes, int, str, Address,
    # list, List, List[int], List[Person], List["Person"],
    # Optional[str], Optional[List[str]], Optional[Dict[str, str]],
    # Dict, Dict[str, int], Optional[Dict],
    Union[str, int], Union[str, int]
)

GET_ORIGIN_RESULTS = (
    Union, Union
)


def func(person: Person):
    pass


@pytest.mark.parametrize("type_hint", TYPE_HINTS)
@pytest.mark.parametrize("result", GET_ORIGIN_RESULTS)
def test_get_origin(type_hint, result):
    type_hints = get_type_hints(func)
    origin = get_origin(type_hints["person"])
    assert origin == Person
