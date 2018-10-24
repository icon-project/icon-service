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
from typing import Any


class GlobalValueMapper(object):

    def __init__(self, is_lock: bool = False) -> None:
        """Constructor
        """
        self._mapper = dict()
        self._lock = Lock()
        self._is_lock = is_lock

    def __contains__(self, key: str) -> bool:
        if self._is_lock:
            with self._lock:
                return key in self._mapper
        else:
            return key in self._mapper

    def __setitem__(self, key: str, value: Any) -> None:
        if self._is_lock:
            with self._lock:
                self._mapper[key] = value
        else:
            self._mapper[key] = value

    def get(self, key: str) -> Any:
        if self._is_lock:
            with self._lock:
                return self._mapper.get(key)
        else:
            return self._mapper.get(key)

    def update(self, mapper: 'GlobalValueMapper'):
        if self._is_lock:
            with self._lock:
                self._mapper.update(mapper._mapper)
        else:
            self._mapper.update(mapper._mapper)
