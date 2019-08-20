# -*- coding: utf-8 -*-
# Copyright 2019 ICON Foundation
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

from enum import Flag

from ..utils import set_flag


class BasePartState(Flag):
    NONE = 0
    DIRTY = 1
    COMPLETE = 2


class BasePart(object):
    def __init__(self, states: 'BasePartState' = BasePartState.NONE):
        self._states = states

    @property
    def states(self) -> 'BasePartState':
        return self._states

    def toggle_state(self, state: 'BasePartState', on: bool):
        self._states = set_flag(self._states, state, on)

    def is_dirty(self) -> bool:
        return self.is_set(BasePartState.DIRTY)

    def set_dirty(self, on: bool):
        self.toggle_state(BasePartState.DIRTY, on)

    def set_complete(self, on: bool):
        self.toggle_state(BasePartState.COMPLETE, on)

    def is_set(self, states: 'BasePartState') -> bool:
        return self._states & states == states
