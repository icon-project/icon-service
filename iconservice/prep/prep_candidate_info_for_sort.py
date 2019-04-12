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

from threading import Lock
from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from ..base.address import Address


class PRepCandidateInfoForSort(object):
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

    def update(self, total_delegated: int):
        self._total_delegated: int = total_delegated

    @staticmethod
    def create_object(address: 'Address',
                      name: str,
                      block_height: int,
                      tx_index: int) -> 'PRepCandidateInfoForSort':
        return PRepCandidateInfoForSort(address, name, block_height, tx_index)


class PRepCandiateInfoMapper(object):
    def __init__(self):
        self._prep_candidate_objects: dict = {}
        self._lock = Lock()

    def __setitem__(self, key: 'Address', value: 'PRepCandidateInfoForSort'):
        with self._lock:
            self._prep_candidate_objects[key] = value

    def __getitem__(self, key: 'Address') -> 'PRepCandidateInfoForSort':
        with self._lock:
            return self._prep_candidate_objects[key]

    def __delitem__(self, key: 'Address'):
        with self._lock:
            del self._prep_candidate_objects[key]

    def __contains__(self, address: 'Address') -> bool:
        with self._lock:
            return address in self._prep_candidate_objects

    def to_sorted_list(self) -> List['PRepCandidateInfoForSort']:
        with self._lock:
            return list(self._prep_candidate_objects.values())


class PRepCandidateSortedInfos(object):

    def __init__(self):
        self._prep_candidate_objects: List['PRepCandidateInfoForSort'] = []
        self._lock = Lock()

    def update(self, prep_objs: List['PRepCandidateInfoForSort']):
        with self._lock:
            self._prep_candidate_objects = prep_objs

    def get(self) -> list:
        with self._lock:
            return self._prep_candidate_objects.copy()
