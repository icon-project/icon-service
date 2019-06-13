# Copyright 2019 ICON Foundation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
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


class IissIssueStorage(object):
    PREFIX: bytes = b'issue'
    CALC_NEXT_BLOCK_HEIGHT_KEY: bytes = PREFIX + b'cnbh'
    CALC_PERIOD_KEY: bytes = PREFIX + b'pk'
    TOTAL_CANDIDATE_DELEGATED_KEY: bytes = PREFIX + b'tcd'

    def __init__(self, db: 'ContextDatabase'):
        """Constructor

        :param db: (Database) state db wrapper
        """
        self._db: 'ContextDatabase' = db

    def close(self):
        """Close the embedded database.
        """
        if self._db:
            self._db = None

    def put_calc_next_block_height(self, context: 'IconScoreContext', calc_block_height: int):
        version = 0
        data: list = [version, calc_block_height]
        value: bytes = MsgPackForDB.dumps(data)
        self._db.put(context, self.CALC_NEXT_BLOCK_HEIGHT_KEY, value)

    def get_calc_next_block_height(self, context: 'IconScoreContext') -> Optional[int]:
        value: bytes = self._db.get(context, self.CALC_NEXT_BLOCK_HEIGHT_KEY)
        if value:
            data: list = MsgPackForDB.loads(value)
            version: int = data[0]
            calc_block_height: int = data[1]
            return calc_block_height
        return None

    def put_calc_period(self, context: 'IconScoreContext', calc_period: int):
        version = 0
        data: list = [version, calc_period]
        value: bytes = MsgPackForDB.dumps(data)
        self._db.put(context, self.CALC_PERIOD_KEY, value)

    def get_calc_period(self, context: 'IconScoreContext') -> Optional[int]:
        value: bytes = self._db.get(context, self.CALC_PERIOD_KEY)
        if value:
            data: list = MsgPackForDB.loads(value)
            version: int = data[0]
            calc_period: int = data[1]
            return calc_period
        return None

    def put_total_candidate_delegated(self, context: 'IconScoreContext', total_candidate_delegated: int):
        version = 0
        data: list = [version, total_candidate_delegated]
        value: bytes = MsgPackForDB.dumps(data)
        self._db.put(context, self.TOTAL_CANDIDATE_DELEGATED_KEY, value)

    def get_total_candidate_delegated(self, context: 'IconScoreContext') -> Optional[int]:
        value: bytes = self._db.get(context, self.TOTAL_CANDIDATE_DELEGATED_KEY)
        if value:
            data: list = MsgPackForDB.loads(value)
            version: int = data[0]
            total_candidate_delegated: int = data[1]
            return total_candidate_delegated
        return None
