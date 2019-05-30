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

from ...utils.msgpack_for_db import MsgPackForDB

if TYPE_CHECKING:
    from ...database.db import ContextDatabase
    from ...iconscore.icon_score_context import IconScoreContext


class RegulatorStorage(object):

    _CURRENT_CALC_PERIOD_ISSUED_ICX_KEY = b'current_calc_period_issued_icx'
    _PREV_CALC_PERIOD_ISSUED_ICX_KEY = b'prev_calc_period_issued_icx'
    _OVER_ISSUED_ICX_KEY = b'over_issued_icx'
    _OVER_ISSUED_I_SCORE_KEY = b'over_issued_i_score'

    def __init__(self, db: 'ContextDatabase'):
        self._db: 'ContextDatabase' = db

    def close(self,
              context: 'IconScoreContext') -> None:
        """Close the embedded database.

        :param context:
        """
        if self._db:
            self._db.close(context)
            self._db = None

    def put_current_calc_period_issued_icx(self,
                                           context: 'IconScoreContext',
                                           current_calc_period_issued_amount: int):

        encoded_current_issued_amount = MsgPackForDB.dumps(current_calc_period_issued_amount)
        self._db.put(context, self._CURRENT_CALC_PERIOD_ISSUED_ICX_KEY, encoded_current_issued_amount)

    def get_current_calc_period_issued_icx(self, context: 'IconScoreContext') -> int:

        encoded_current_issued_amount = self._db.get(context, self._CURRENT_CALC_PERIOD_ISSUED_ICX_KEY)
        current_issued_amount = MsgPackForDB.loads(encoded_current_issued_amount)
        if current_issued_amount is None:
            current_issued_amount = 0
        return current_issued_amount

    def put_prev_calc_period_issued_icx(self, context: 'IconScoreContext', prev_calc_period_issued_amount: int):
        encoded_prev_issued_amount = MsgPackForDB.dumps(prev_calc_period_issued_amount)
        self._db.put(context, self._PREV_CALC_PERIOD_ISSUED_ICX_KEY, encoded_prev_issued_amount)

    def get_prev_calc_period_issued_icx(self, context: 'IconScoreContext') -> Optional[int]:
        encoded_prev_issued_amount = self._db.get(context, self._PREV_CALC_PERIOD_ISSUED_ICX_KEY)
        prev_issued_amount: Optional[int] = None
        if encoded_prev_issued_amount is not None:
            prev_issued_amount = MsgPackForDB.loads(encoded_prev_issued_amount)
        return prev_issued_amount

    def put_over_issued_icx(self, context: 'IconScoreContext', over_issued_icx: int):
        encoded_over_issued_icx = MsgPackForDB.dumps(over_issued_icx)
        self._db.put(context, self._OVER_ISSUED_ICX_KEY, encoded_over_issued_icx)

    def get_over_issued_icx(self, context: 'IconScoreContext') -> int:
        encoded_over_issued_icx = self._db.get(context, self._OVER_ISSUED_ICX_KEY)
        over_issued_icx = 0
        if encoded_over_issued_icx is not None:
            over_issued_icx = MsgPackForDB.loads(encoded_over_issued_icx)
        return over_issued_icx

    def put_over_issued_i_score(self, context: 'IconScoreContext', over_issued_i_score: int):
        encoded_over_issued_i_score = MsgPackForDB.dumps(over_issued_i_score)
        self._db.put(context, self._OVER_ISSUED_I_SCORE_KEY, encoded_over_issued_i_score)

    def get_over_issued_i_score(self, context: 'IconScoreContext') -> int:
        encoded_over_issued_i_score = self._db.get(context, self._OVER_ISSUED_I_SCORE_KEY)
        over_issued_i_score = 0
        if encoded_over_issued_i_score is not None:
            over_issued_i_score = MsgPackForDB.loads(encoded_over_issued_i_score)
        return over_issued_i_score
