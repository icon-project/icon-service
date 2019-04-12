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


class IissCommonStorage(object):
    PREFIX: bytes = b'common'
    REWARD_REP_KEY: bytes = PREFIX + b'rr'
    UNSTAKE_LOCK_PERIOD_KEY: bytes = PREFIX + b'ulp'

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

    def put_reward_rep(self, context: 'IconScoreContext', reward_rep: int):
        version = 0
        data: bytes = MsgPackForDB.dumps([version, reward_rep])
        self._db.put(context, self.REWARD_REP_KEY, data)

    def get_reward_rep(self, context: 'IconScoreContext') -> Optional[int]:
        value: bytes = self._db.get(context, self.REWARD_REP_KEY)
        if value:
            data = MsgPackForDB.loads(value)
            version: int = data[0]
            reward_rep: int = data[1]
            return reward_rep
        else:
            return None

    def put_unstake_lock_period(self, context: 'IconScoreContext', unstake_lock_period: int):
        version = 0
        data: bytes = MsgPackForDB.dumps([version, unstake_lock_period])
        self._db.put(context, self.UNSTAKE_LOCK_PERIOD_KEY, data)

    def get_unstake_lock_period(self, context: 'IconScoreContext') -> Optional[int]:
        value: bytes = self._db.get(context, self.UNSTAKE_LOCK_PERIOD_KEY)
        if value:
            data = MsgPackForDB.loads(value)
            version: int = data[0]
            unstake_lock_period: int = data[1]
            return unstake_lock_period
        else:
            return None
