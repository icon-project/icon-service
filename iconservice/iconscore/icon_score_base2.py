# -*- coding: utf-8 -*-

# Copyright 2018 ICON Foundation
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

from typing import TypeVar, TYPE_CHECKING
from abc import ABC, ABCMeta
from enum import IntEnum, unique

from ..base.address import Address

if TYPE_CHECKING:
    from .icon_score_base import IconScoreBase

T = TypeVar('T')
BaseType = TypeVar('BaseType', bool, int, str, bytes, Address)

CONST_CLASS_EXTERNALS = '__externals'
CONST_CLASS_PAYABLES = '__payables'
CONST_CLASS_INDEXES = '__indexes'
CONST_CLASS_API = '__api'

CONST_BIT_FLAG = '__bit_flag'
CONST_INDEXED_ARGS_COUNT = '__indexed_args_count'

FORMAT_IS_NOT_FUNCTION_OBJECT = "isn't function object: {}, cls: {}"
FORMAT_IS_NOT_DERIVED_OF_OBJECT = "isn't derived of {}"
FORMAT_DECORATOR_DUPLICATED = "can't duplicated {} decorator func: {}, cls: {}"
STR_IS_NOT_CALLABLE = 'is not callable'
STR_FALLBACK = 'fallback'


@unique
class ConstBitFlag(IntEnum):
    NonFlag = 0
    ReadOnly = 1
    External = 2
    Payable = 4
    EventLog = 8
    Interface = 16


class InterfaceScoreMeta(ABCMeta):
    def __new__(mcs, name, bases, namespace, **kwargs):
        if ABC in bases:
            return super().__new__(mcs, name, bases, namespace, **kwargs)

        cls = super().__new__(mcs, name, bases, namespace, **kwargs)
        return cls


class InterfaceScore(ABC, metaclass=InterfaceScoreMeta):
    def __init__(self, addr_to: 'Address', from_score: 'IconScoreBase'):
        self.__addr_to = addr_to
        self.__from_score = from_score

    @property
    def addr_to(self) -> 'Address':
        return self.__addr_to

    @property
    def from_score(self) -> 'IconScoreBase':
        return self.__from_score
