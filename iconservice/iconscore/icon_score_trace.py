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

from enum import Enum, unique
from typing import TYPE_CHECKING, Optional

from ..base.address import Address

if TYPE_CHECKING:
    pass


@unique
class TraceType(Enum):
    CALL = 0
    REVERT = 1
    THROW = 2
    DESTROY = 3


class Trace(object):
    """
    A DataClass of a Trace.
    sample
    {
        "scoreAddress": "cx00...",
        "trace": "CALL",
        "data": ["cx11...", "transfer", ["hx00...", "0x1234"]]
    }

    """

    def __init__(
            self,
            score_address: 'Address',
            trace: TraceType,
            data: list = None) -> None:
        """
        Constructor

        :param score_address: an address of SCORE in which the trace is occurred
        :param trace: trace type
        :param data: a list of arguments or call function name
          e.g.
            transfer: [RECIPIENT, AMOUNT]
            call: [SCORE_ADDRESS_TO_CALL, METHOD, [ARGS_OF_METHOD]]
            revert: [CODE, MESSAGE]
            throw: [CODE, MESSAGE]
        """
        self.score_address: 'Address' = score_address
        self.trace: TraceType = trace
        self.data: list = data

    def __str__(self) -> str:
        return '\n'.join([f'{k}: {v}' for k, v in self.__dict__.items()])

    def to_dict(self, casing: Optional = None) -> dict:
        """
        Returns properties as `dict`
        :return: a dict
        """
        new_dict = {}
        for key, value in self.__dict__.items():
            if value is None:
                # Excludes properties which have `None` value
                continue

            if isinstance(value, TraceType):
                value = value.name

            new_dict[casing(key) if casing else key] = value

        return new_dict
