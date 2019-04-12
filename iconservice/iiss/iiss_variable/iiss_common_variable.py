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

from ...icon_constant import ConfigKey
from .iiss_common_storage import IissCommonStorage

if TYPE_CHECKING:
    from ...iconscore.icon_score_context import IconScoreContext
    from ...database.db import ContextDatabase
    from iconcommons import IconConfig


class IissCommonVariable(object):

    def __init__(self, db: 'ContextDatabase'):
        self._storage: 'IissCommonStorage' = IissCommonStorage(db)

    def init_config(self, context: 'IconScoreContext', conf: 'IconConfig'):
        if self._storage.get_reward_rep(context) is None:
            reward_rep: int = conf[ConfigKey.IISS_VARIABLE][ConfigKey.REWARD_REP]
            self._storage.put_reward_rep(context, reward_rep)

        if self._storage.get_unstake_lock_period(context) is None:
            unstake_lock_period: int = conf[ConfigKey.IISS_UNSTAKE_LOCK_PERIOD]
            self._storage.put_unstake_lock_period(context, unstake_lock_period)

    def put_reward_rep(self, context: 'IconScoreContext', reward_rep: int):
        self._storage.put_reward_rep(context, reward_rep)

    def get_reward_rep(self, context: 'IconScoreContext') -> int:
        value: Optional[int] = self._storage.get_reward_rep(context)
        if value is None:
            return 0
        return value

    def put_unstake_lock_period(self, context: 'IconScoreContext', unstake_lock_period: int):
        self._storage.put_unstake_lock_period(context, unstake_lock_period)

    def get_unstake_lock_period(self, context: 'IconScoreContext') -> int:
        value: Optional[int] = self._storage.get_unstake_lock_period(context)
        if value is None:
            return 0
        return value
