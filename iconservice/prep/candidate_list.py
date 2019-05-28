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

from typing import Optional

from .candidate import Candidate
from ..base.address import Address
from ..base.exception import InvalidParamsException


class CandidateList(list):

    def append(self, data: 'Candidate'):
        super().append(data)

    def remove(self, address: 'Address'):
        if self._is_empty():
            return

        data: 'Candidate' = self._get(address)
        if data is None:
            return

        super().remove(data)

    def update(self, address: 'Address', new_delegated: int):
        if self._is_empty():
            return

        data: Optional['Candidate'] = self._get(address)
        if data is None:
            raise InvalidParamsException(f"Fail update_sort: node is None")

        super().remove(data)
        data.delegated = new_delegated

        # TODO optimize
        if self._is_empty():
            super().append(data)
        else:
            index: int = self._index(data)

            if index == 0:
                # head node
                super().insert(0, data)
            elif index == -1:
                # tail node
                super().append(data)
            else:
                super().insert(index, data)

    def _is_empty(self):
        return len(self) == 0

    def _get(self, address: 'Address') -> Optional['Candidate']:
        for data in self:
            if data.address == address:
                return data
        return None

    def _index(self, target: 'Candidate') -> int:
        for i, data in enumerate(self):
            if target > data:
                return i
        return -1
