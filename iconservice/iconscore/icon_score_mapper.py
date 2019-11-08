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
from typing import TYPE_CHECKING

from .icon_score_mapper_object import IconScoreMapperObject

if TYPE_CHECKING:
    from ..base.address import Address
    from .icon_score_mapper_object import IconScoreInfo


class IconScoreMapper(object):
    """Icon score information mapping table

    This instance should be used as a singleton

    key: icon_score_address
    value: IconScoreInfo
    """

    def __init__(self, is_threadsafe: bool = False) -> None:
        """Constructor
        """
        self._score_mapper = IconScoreMapperObject()

        if is_threadsafe:
            self._lock = Lock()
        else:
            self._lock = None

    def __contains__(self, address: 'Address'):
        if self._lock is None:
            return address in self._score_mapper

        with self._lock:
            return address in self._score_mapper

    def __getitem__(self, key: 'Address') -> 'IconScoreInfo':
        if self._lock is None:
            return self._score_mapper[key]

        with self._lock:
            return self._score_mapper[key]

    def __setitem__(self, key: 'Address', value: 'IconScoreInfo'):
        if self._lock is None:
            self._score_mapper[key] = value
        else:
            with self._lock:
                self._score_mapper[key] = value

    def __delitem__(self, key: 'Address'):
        if self._lock is None:
            del self._score_mapper[key]
        else:
            with self._lock:
                del self._score_mapper[key]

    def get(self, key: 'Address') -> 'IconScoreInfo':
        if self._lock is None:
            return self._score_mapper.get(key)

        with self._lock:
            return self._score_mapper.get(key)

    def update(self, mapper: 'IconScoreMapper'):
        if self._lock is None:
            self._score_mapper.update(mapper._score_mapper)
        else:
            with self._lock:
                self._score_mapper.update(mapper._score_mapper)

    def clear(self):
        if self._lock is None:
            self._score_mapper.clear()
        else:
            with self._lock:
                self._score_mapper.clear()

    def close(self):
        for _, score_info in self._score_mapper.items():
            score_info.score_db.close()
