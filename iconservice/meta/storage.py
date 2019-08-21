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

from typing import TYPE_CHECKING, Tuple, List

from ..base.ComponentBase import StorageBase
from ..base.address import Address
from ..prep.data import PRep
from ..utils.msgpack_for_db import MsgPackForDB

if TYPE_CHECKING:
    from ..iconscore.icon_score_context import IconScoreContext


class Storage(StorageBase):
    _KEY_LAST_CALC_INFO = b'last_calc_info'
    _KEY_LAST_TERM_INFO = b'last_term_info'
    _KEY_LAST_MAIN_PREPS = b'last_main_preps'

    def put_last_calc_info(self,
                           context: 'IconScoreContext',
                           start: int,
                           end: int):
        version = 0
        value: bytes = MsgPackForDB.dumps([version, start, end])
        # self._db.put(context, self._KEY_LAST_CALC_INFO, value, include_root_hash=False)
        self._db.put(context, self._KEY_LAST_CALC_INFO, value)

    def get_last_calc_info(self, context: 'IconScoreContext') -> Tuple[int, int]:
        value: bytes = self._db.get(context, self._KEY_LAST_CALC_INFO)
        if value is None:
            return -1, -1
        data: list = MsgPackForDB.loads(value)
        version = data[0]
        return data[1], data[2]

    def put_last_term_info(self,
                           context: 'IconScoreContext',
                           start: int,
                           end: int):
        version = 0
        value: bytes = MsgPackForDB.dumps([version, start, end])
        # self._db.put(context, self._KEY_LAST_TERM_INFO, value, include_root_hash=False)
        self._db.put(context, self._KEY_LAST_TERM_INFO, value)

    def get_last_term_info(self, context: 'IconScoreContext') -> Tuple[int, int]:
        value: bytes = self._db.get(context, self._KEY_LAST_TERM_INFO)
        if value is None:
            return -1, -1
        data: list = MsgPackForDB.loads(value)
        version = data[0]
        return data[1], data[2]

    def put_last_main_preps(self,
                            context: 'IconScoreContext',
                            main_preps: List['PRep']):
        version = 0
        preps: List['Address'] = [prep.address for prep in main_preps]
        value: bytes = MsgPackForDB.dumps([version, preps])
        # self._db.put(context, self._KEY_LAST_MAIN_PREPS, value, include_root_hash=False)
        self._db.put(context, self._KEY_LAST_MAIN_PREPS, value)

    def get_last_main_preps(self, context: 'IconScoreContext') -> List['Address']:
        value: bytes = self._db.get(context, self._KEY_LAST_MAIN_PREPS)
        if value is None:
            return []
        data: list = MsgPackForDB.loads(value)
        version = data[0]
        return data[1]
