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

from typing import TYPE_CHECKING, Optional

from ...base.ComponentBase import StorageBase
from ...utils.msgpack_for_db import MsgPackForDB

if TYPE_CHECKING:
    from ...iconscore.icon_score_context import IconScoreContext


class Storage(StorageBase):
    _REGULATOR_VARIABLE_KEY = b'regulator_variable'

    def get_regulator_variable(self, context: 'IconScoreContext'):
        regulator_variable: Optional[bytes] = self._db.get(context, self._REGULATOR_VARIABLE_KEY)
        if regulator_variable:
            return RegulatorVariable.from_bytes(regulator_variable)
        return RegulatorVariable(current_calc_period_issued_icx=0,
                                 prev_calc_period_issued_icx=-1,
                                 over_issued_iscore=0)

    def put_regulator_variable(self, context: 'IconScoreContext', rv: 'RegulatorVariable'):
        self._db.put(context, self._REGULATOR_VARIABLE_KEY, rv.to_bytes())


class RegulatorVariable:
    _VERSION = 0

    def __init__(self,
                 current_calc_period_issued_icx: int,
                 prev_calc_period_issued_icx: int,
                 over_issued_iscore: int):
        """

        :param current_calc_period_issued_icx: The sum of issued ICX amount on the current period (mutable)
        :param prev_calc_period_issued_icx: The sum of issued ICX amount on the previous period (immutable)
        :param over_issued_iscore: I-SCORE amount which over issued than Reward calculator (mutable)
        """
        self.current_calc_period_issued_icx = current_calc_period_issued_icx
        self.prev_calc_period_issued_icx = prev_calc_period_issued_icx
        self.over_issued_iscore = over_issued_iscore

    @classmethod
    def from_bytes(cls, buf: bytes) -> 'RegulatorVariable':
        data: list = MsgPackForDB.loads(buf)
        version = data[0]

        return cls(*data[1:])

    def to_bytes(self):
        data: list = [
            self._VERSION,
            self.current_calc_period_issued_icx,
            self.prev_calc_period_issued_icx,
            self.over_issued_iscore
        ]
        return MsgPackForDB.dumps(data)

    def __str__(self):
        return f"Current calc period issued ICX: {self.current_calc_period_issued_icx} " \
               f"Prev calc period issued ICX: {self.prev_calc_period_issued_icx} " \
               f"Remain over issued I-SCORE: {self.over_issued_iscore} "
