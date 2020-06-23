# -*- coding: utf-8 -*-

from inspect import signature
from typing import List, Dict, Optional, Union

import pytest

from typing_extensions import TypedDict

from iconservice.iconscore.typing.function import (
    normalize_signature,
)


class Person(TypedDict):
    name: str
    age: int


# Allowed list
def func0(name: str, age: int) -> int: pass
def func1(name: "str", age: int) -> str: pass
def func2(a: list): pass
def func3(a: List): pass
def func4(a: List[int]): pass
def func5(a: List["int"]): pass
def func6(a: List[Person]): pass
def func7(a: List["Person"]): pass

_ALLOWED_LIST = [func0, func1, func2, func3, func4, func5, func6, func7]

# Denied list
def func0_error(a: "int"): pass
def func1_error(a: Dict): pass
def func2_error(a: Dict[str, str]): pass
def func3_error(a: Union[int, str]): pass
def func4_error(a: Optional[str]): pass

_DENIED_LIST = [
    func0_error,
    func1_error,
    func2_error,
    func3_error,
    func4_error,
]


@pytest.mark.parametrize("func", _ALLOWED_LIST)
def test_normalize_signature_with_allowed_func(func):
    sig = signature(func)
    new_sig = normalize_signature(sig)
    assert new_sig == sig


@pytest.mark.skip("Not implemented")
@pytest.mark.parametrize("func", _DENIED_LIST)
def test_normalize_signature_with_denied_func(func):
    sig = signature(func)
    new_sig = normalize_signature(sig)
    assert new_sig != sig

    new_sig2 = normalize_signature(new_sig)
    assert new_sig2 == new_sig
