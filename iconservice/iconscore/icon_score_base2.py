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

import hashlib
import json

from typing import TYPE_CHECKING, Optional, Union, Any
from abc import ABC, ABCMeta

from ..base.exception import RevertException, ExceptionCode
from ..iconscore.icon_score_context import ContextContainer
from ..iconscore.icon_score_step import StepType
from ..base.address import Address

if TYPE_CHECKING:
    from .icon_score_base import IconScoreBase


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


class Block(object):
    def __init__(self, block_height: int, timestamp: int) -> None:
        """Constructor

        :param block_height: block height
        :param timestamp: block timestamp
        """
        self._height = block_height
        # unit: microsecond
        self._timestamp = timestamp

    @property
    def height(self) -> int:
        return self._height

    @property
    def timestamp(self) -> int:
        return self._timestamp


def revert(message: Optional[str] = None,
           code: Union[ExceptionCode, int] = ExceptionCode.SCORE_ERROR) -> None:
    """
    Reverts the transaction and breaks.
    All the changes of state DB will be reverted.

    :param message: revert message
    :param code: code
    """
    raise RevertException(message, code)


def sha3_256(data: bytes) -> bytes:
    """
    Computes hash using the input data
    :param data: input data
    :return: hashed data in bytes
    """
    context = ContextContainer._get_context()
    if context.step_counter:
        step_count = 1
        if data:
            step_count += len(data)
        context.step_counter.apply_step(StepType.API_CALL, step_count)

    return hashlib.sha3_256(data).digest()


def json_dumps(obj: Any, **kwargs) -> str:
    return json.dumps(obj, **kwargs)


def json_loads(src: str, **kwargs) -> Any:
    return json.loads(src, **kwargs)
