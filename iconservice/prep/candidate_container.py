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

from .candidate_info_for_sort import CandidateInfoForSort
from .candidate_linked_list import CandidateLinkedList
from ..base.exception import InvalidParamsException

if TYPE_CHECKING:
    from ..base.address import Address


class CandidateInfoMapper(object):
    def __init__(self):
        self._prep_candidate_objects: dict = {}
        self._lock = Lock()

    def __setitem__(self, key: 'Address', value: 'CandidateInfoForSort'):
        with self._lock:
            self._prep_candidate_objects[key] = value

    def __getitem__(self, key: 'Address') -> 'CandidateInfoForSort':
        with self._lock:
            return self._prep_candidate_objects[key]

    def __delitem__(self, key: 'Address'):
        with self._lock:
            del self._prep_candidate_objects[key]

    def __contains__(self, address: 'Address') -> bool:
        with self._lock:
            return address in self._prep_candidate_objects

    def to_genesis_sorted_list(self) -> List['CandidateInfoForSort']:
        with self._lock:
            return sorted(self._prep_candidate_objects.values(), key=cmp_to_key(CandidateInfoForSort.compare_key))


class CandidateSortedInfos(object):

    def __init__(self):
        self._prep_candidate_objects: 'CandidateLinkedList' = CandidateLinkedList()
        self._lock = Lock()
        self._init = False

    def genesis_update(self, prep_objs: List['CandidateInfoForSort']):
        with self._lock:
            if self._init:
                raise InvalidParamsException(f'Invalid instance update : init is already True')

            for obj in prep_objs:
                self._prep_candidate_objects.append(obj)
            self._init = True

    def to_list(self) -> list:
        with self._lock:
            tmp: list = []
            for n in self._prep_candidate_objects:
                Logger.debug(f"to_list: {n.data.address}", "iiss")
                tmp.append(n.data)
            return tmp

    def to_dict(self) -> dict:
        with self._lock:
            tmp: dict = {}
            for n in self._prep_candidate_objects:
                Logger.debug(f"to_infos_dict: {n.data.address}", "iiss")
                tmp[n.data.address] = n.data
            return tmp

    def get(self, address: 'Address') -> tuple:
        with self._lock:
            for index, n in enumerate(self._prep_candidate_objects):
                if n.data.address == address:
                    return index, n.data
            return None, None

    def add_info(self, new_info: 'CandidateInfoForSort'):
        with self._lock:
            self._prep_candidate_objects.append(new_info)

    def del_info(self, address: 'Address'):
        with self._lock:
            self._prep_candidate_objects.remove(address)

    def update_info(self, address: 'Address', update_total_delegated: int):
        with self._lock:
            self._prep_candidate_objects.update(address, update_total_delegated)

    def clear(self):
        with self._lock:
            self._prep_candidate_objects.clear()
