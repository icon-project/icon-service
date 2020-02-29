# -*- coding: utf-8 -*-
# Copyright 2020 ICON Foundation Inc.
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

import time


class Timer(object):
    def __init__(self):
        self._start_time_s: float = 0
        self._duration_s: float = 0
        self._end_time_s: float = 0

    @property
    def duration(self) -> float:
        return self._duration_s

    def start(self) -> float:
        time_s: float = time.time()
        self._start_time_s = time_s
        return time_s

    def stop(self) -> float:
        time_s: float = time.time()
        self._end_time_s = time_s
        self._duration_s = time_s - self._start_time_s
        return time_s
