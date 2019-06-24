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

from copy import deepcopy
from typing import List, Union, Optional

from .prep import PRep
from ...base.address import Address
from ...base.exception import InvalidParamsException, AccessDeniedException
from ...icon_constant import PREP_MAIN_PREPS, PREP_SUB_PREPS
from ...iconscore.icon_score_context import IconScoreContext


class SortedList(object):
    def __init__(self):
        self._sorted_list = []

    def add(self, new_prep: 'PRep'):
        index = 0

        for i in range(len(self._sorted_list)):
            prep: 'PRep' = self._sorted_list[i]
            if new_prep.order() > prep.order():
                break

            index += 1

        self._sorted_list.insert(index, new_prep)

    def sort(self, prep: 'PRep'):
        self._sorted_list.remove(prep)
        self.add(prep)

    def index(self, prep: 'PRep') -> int:
        return self._sorted_list.index(prep)

    def remove(self, prep: 'PRep'):
        self._sorted_list.remove(prep)

    def append(self, prep: 'PRep'):
        self._sorted_list.append(prep)

    def __iter__(self):
        for prep in self._sorted_list:
            yield prep

    def __getitem__(self, k: Union[int, slice]) -> Union['PRep', List['PRep']]:
        if isinstance(k, slice):
            return self._sorted_list[k]
        return self._sorted_list[k]

    def __len__(self) -> int:
        return len(self._sorted_list)


class PRepContainer(object):
    """Contains PRep objects

    P-Rep PRep object contains information on registration and delegation.
    PRep objects are sorted in descending order by delegated amount.
    """

    # bitwise flags
    NONE = 0x00
    READONLY = 0x01
    DIRTY = 0x02

    def __init__(self, flags: int = NONE):
        self.flags: int = flags
        self._prep_dict = {}
        self._prep_list = SortedList()

    def load(self, context: 'IconScoreContext'):
        for prep in context.storage.prep.get_prep_iterator():
            self._add(prep)

    def add(self, prep: 'PRep'):
        if self.flags & self.READONLY:
            raise AccessDeniedException("PRepContainer access denied")

        self._add(prep)
        self.flags |= self.DIRTY

    def _add(self, prep: 'PRep'):
        self._prep_dict[prep.address] = prep
        self._prep_list.append(prep)

    def remove(self, address: 'Address'):
        if self.flags & self.READONLY:
            raise AccessDeniedException("PRepContainer access denied")

        prep: 'PRep' = self._prep_dict.get(address)
        if prep:
            del self._prep_dict[address]
            self._prep_list.remove(prep)

    def update(self, address: 'Address', delegated_amount: int):
        prep: 'PRep' = self.get(address)
        prep.delegated: int = delegated_amount
        self._prep_list.sort(prep)

    def get(self, address: 'Address') -> Optional['PRep']:
        return self._prep_dict.get(address)

    def __contains__(self, address: 'Address') -> bool:
        return address in self._prep_dict

    def __iter__(self):
        for prep in self._prep_list:
            yield prep

    def __getitem__(self, key: Union['Address', int]) -> 'PRep':
        if isinstance(key, Address):
            return self._prep_dict[key]
        elif isinstance(key, int):
            return self._prep_list[key]

        raise InvalidParamsException

    def __len__(self) -> int:
        return len(self._prep_list)

    def get_preps(self) -> List['PRep']:
        """Returns top 100 preps in descending order by delegated amount

        :return: P-Rep list
        """
        return self._prep_list[:PREP_SUB_PREPS]

    def get_snapshot(self) -> 'PRepContainer':
        return deepcopy(self)

    def get_ranking(self, address: 'Address') -> int:
        """The ranking is in the descending order by delegated amount
        and begins from 1

        :return: ranking
        """
        # TODO: Use binary search algorithm
        ranking: int = 1
        for prep in self._prep_list:
            if address == prep.address:
                return ranking

            ranking += 1

        raise InvalidParamsException(f"PRep not found: {str(address)}")
