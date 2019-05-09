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

from operator import lt, gt
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..base.address import Address


class CandidateInfoForSort(object):
    def __init__(self, address: 'Address', name: str, block_height: int, tx_index: int):
        self._address: 'Address' = address
        self._name: str = name
        self._block_height: int = block_height
        self._tx_index: int = tx_index
        self._total_delegated: int = 0

    @property
    def address(self) -> 'Address':
        return self._address

    @property
    def name(self) -> str:
        return self._name

    @property
    def total_delegated(self) -> int:
        return self._total_delegated

    @property
    def block_height(self) -> int:
        return self._block_height

    @property
    def tx_index(self) -> int:
        return self._tx_index

    def update(self, total_delegated: int):
        self._total_delegated: int = total_delegated

    @staticmethod
    def create_object(address: 'Address',
                      name: str,
                      block_height: int,
                      tx_index: int) -> 'CandidateInfoForSort':
        return CandidateInfoForSort(address, name, block_height, tx_index)

    def to_order_list(self) -> list:
        return [self._total_delegated, self._block_height,  self._tx_index]

    def __gt__(self, other: 'CandidateInfoForSort') -> bool:
        x: list = self.to_order_list()
        y: list = other.to_order_list()
        is_reverse: list = [False, True, True]

        for i in range(len(x)):
            first_operator = gt
            second_operator = lt

            if is_reverse[i]:
                first_operator = lt
                second_operator = gt

            if first_operator(x[i], y[i]):
                return True
            elif second_operator(x[i], y[i]):
                return False
            else:
                if i != len(x):
                    continue
                else:
                    return False

    def __lt__(self, other: 'CandidateInfoForSort') -> bool:
        return not self.__gt__(other)

    @staticmethod
    def compare_key(x: 'CandidateInfoForSort', y: 'CandidateInfoForSort') -> int:
        if x < y:
            return 1
        elif x > y:
            return -1
        else:
            return 0
