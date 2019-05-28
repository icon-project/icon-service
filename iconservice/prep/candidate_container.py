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

from functools import cmp_to_key
from threading import Lock
from typing import TYPE_CHECKING, List

from iconcommons import Logger
from .candidate import Candidate
from .candidate_list import CandidateList
from .candidate_utils import CandidateUtils
from ..base.exception import InvalidParamsException

if TYPE_CHECKING:
    from ..base.address import Address


class CandidateInfoMapper(object):
    def __init__(self):
        self._candidates: dict = {}
        self._lock = Lock()

    def __setitem__(self, key: 'Address', value: 'Candidate'):
        with self._lock:
            self._candidates[key] = value

    def __getitem__(self, key: 'Address') -> 'Candidate':
        with self._lock:
            return self._candidates[key]

    def __delitem__(self, key: 'Address'):
        with self._lock:
            del self._candidates[key]

    def __contains__(self, address: 'Address') -> bool:
        with self._lock:
            return address in self._candidates

    def to_genesis_sorted_list(self) -> List['Candidate']:
        with self._lock:
            return sorted(self._candidates.values(), key=cmp_to_key(CandidateUtils.compare_key))


class SortedCandidates(object):

    def __init__(self):
        self._candidates: 'CandidateList' = CandidateList()
        self._lock = Lock()
        self._init = False

    def genesis_update(self, prep_objs: List['Candidate']):
        with self._lock:
            if self._init:
                raise InvalidParamsException(f'Invalid instance update : init is already True')

            for obj in prep_objs:
                self._candidates.append(obj)
            self._init = True

    def to_list(self) -> list:
        with self._lock:
            tmp: list = []
            for data in self._candidates:
                Logger.debug(f"to_list: {data.address}", "iiss")
                tmp.append(data)
            return tmp

    def get_candidate(self, address: 'Address') -> tuple:
        with self._lock:
            for index, data in enumerate(self._candidates):
                if data.address == address:
                    return index, data
            return None, None

    def add_candidate(self, new_info: 'Candidate'):
        with self._lock:
            self._candidates.append(new_info)

    def del_candidate(self, address: 'Address'):
        with self._lock:
            self._candidates.remove(address)

    def update_candidate(self, address: 'Address', update_total_delegated: int):
        with self._lock:
            self._candidates.update(address, update_total_delegated)

    def clear(self):
        with self._lock:
            self._candidates.clear()
