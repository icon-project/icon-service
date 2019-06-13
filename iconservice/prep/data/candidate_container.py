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

from typing import TYPE_CHECKING, List, Union, Optional

from .candidate import Candidate
from ...base.exception import InvalidParamsException, AccessDeniedException
from ...icon_constant import PREP_COUNT
from ...iconscore.icon_score_context import IconScoreContext

if TYPE_CHECKING:
    from ...base.address import Address


class SortedList(object):
    def __init__(self):
        self._sorted_list = []

    def add(self, new_candidate: 'Candidate'):
        index = 0

        for i in range(len(self._sorted_list)):
            candidate: 'Candidate' = self._sorted_list[i]
            if new_candidate.order() > candidate.order():
                break

            index += 1

        self._sorted_list.insert(index, new_candidate)

    def sort(self, candidate: 'Candidate'):
        self._sorted_list.remove(candidate)
        self.add(candidate)

    def index(self, candidate) -> int:
        return self._sorted_list.index(candidate)

    def remove(self, candidate: 'Candidate'):
        self._sorted_list.remove(candidate)

    def append(self, candidate: 'Candidate'):
        self._sorted_list.append(candidate)

    def __iter__(self):
        for candidate in self._sorted_list:
            yield candidate

    def __getitem__(self, index: int) -> 'Candidate':
        return self._sorted_list[index]

    def __len__(self) -> int:
        return len(self._sorted_list)


class CandidateContainer(object):
    """Contains P-Rep candidate objects

    P-Rep Candidate object contains information on registration and delegation.
    Candidate objects are sorted in descending order by delegated amount.
    """

    # bitwise flags
    NONE = 0x00
    READONLY = 0x01
    DIRTY = 0x02

    def __init__(self, flags: int = NONE):
        self.flags: int = flags
        self._candidate_dict = {}
        self._candidate_list = SortedList()

    def load(self, context: 'IconScoreContext'):
        for candidate in context.storage.prep.get_candidate_iterator():
            self._add(candidate)

    def add(self, candidate: 'Candidate'):
        if self.flags & self.READONLY:
            raise AccessDeniedException("CandidateContainer access denied")

        self._add(candidate)
        self.flags |= self.DIRTY

    def _add(self, candidate: 'Candidate'):
        self._candidate_dict[candidate.address] = candidate
        self._candidate_list.append(candidate)

    def remove(self, address: 'Address'):
        if self.flags & self.READONLY:
            raise AccessDeniedException("CandidateContainer access denied")

        candidate: 'Candidate' = self._candidate_dict.get(address)
        if candidate:
            del self._candidate_dict[address]
            self._candidate_list.remove(candidate)

    def get(self, address: 'Address') -> Optional['Candidate']:
        return self._candidate_dict.get(address)

    def __contains__(self, address: 'Address') -> bool:
        return address in self._candidate_dict

    def __iter__(self):
        for candidate in self._candidate_list:
            yield candidate

    def __getitem__(self, key: Union['Address', int]) -> 'Candidate':
        if isinstance(key, Address):
            return self._candidate_dict[key]
        elif isinstance(key, int):
            return self._candidate_list[key]

        raise InvalidParamsException

    def __len__(self) -> int:
        return len(self._candidate_list)

    def get_preps(self) -> List['Candidate']:
        """Returns top 22 candidates in descending order by delegated amount

        :return: P-Rep list
        """
        preps = []

        for candidate in self._candidate_list:
            preps.append(candidate)
            if len(preps) == PREP_COUNT:
                break

        return preps

    def get_snapshot(self) -> 'CandidateContainer':
        return None

    def get_ranking(self, address: 'Address') -> int:
        """The ranking is in the descending order by delegated amount
        and begins from 1

        :return: ranking
        """
        # TODO: Use binary search algorithm
        ranking: int = 1
        for candidate in self._candidate_list:
            if address == candidate.address:
                return ranking

            ranking += 1

        raise InvalidParamsException(f"Candidate not found: {str(address)}")
