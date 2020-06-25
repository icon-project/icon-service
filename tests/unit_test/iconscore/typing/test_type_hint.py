# -*- coding: utf-8 -*-

from typing import List, Optional, Dict, Union

import pytest
from typing_extensions import TypedDict

from iconservice.base.address import Address


class Person(TypedDict):
    name: str
    age: int


type_hints = (
    bool, bytes, int, str, Address,
    list, List, List[int], List[Person], List["Person"],
    Optional[str], Optional[List[str]], Optional[Dict[str, str]],
    Dict, Dict[str, int], Optional[Dict],
    Union[str], Union[str, int]
)


@pytest.mark.parametrize("type_hint", type_hints)
def test_normalize_type_hint(type_hint):
    pass
