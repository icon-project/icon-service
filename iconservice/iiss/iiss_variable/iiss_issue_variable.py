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
from .iiss_issue_storage import IissIssueStorage

if TYPE_CHECKING:
    from ...iconscore.icon_score_context import IconScoreContext
    from ...database.db import ContextDatabase
    from iconcommons import IconConfig


class IissIssueVariable(object):

    def __init__(self, db: 'ContextDatabase'):
        self._storage: 'IissIssueStorage' = IissIssueStorage(db)

    def init_config(self, context: 'IconScoreContext', conf: 'IconConfig'):
        if self._storage.get_reward_rep(context) is None:
            reward_rep: int = conf[ConfigKey.REWARD_REP]
            self._storage.put_reward_rep(context, reward_rep)

        if self._storage.get_liner_point(context) is None:
            liner_point: int = conf[ConfigKey.LINER_POINT]
            self._storage.put_liner_point(context, liner_point)

        if self._storage.get_calc_period(context) is None:
            calc_period: int = conf[ConfigKey.IISS_CALCULATE_PERIOD]
            self._storage.put_calc_period(context, calc_period)

    def put_reward_rep(self, context: 'IconScoreContext', reward_rep: int):
        self._storage.put_reward_rep(context, reward_rep)

    def get_reward_rep(self, context: 'IconScoreContext') -> int:
        value: Optional[int] = self._storage.get_reward_rep(context)
        if value is None:
            return 0
        return value

    def put_liner_point(self, context: 'IconScoreContext', liner_point: int):
        self._storage.put_reward_rep(context, liner_point)

    def get_liner_point(self, context: 'IconScoreContext') -> Optional[int]:
        value: Optional[int] = self._storage.get_liner_point(context)
        if value is None:
            return 0
        return value

    def put_calc_next_block_height(self, context: 'IconScoreContext', calc_block_height: int):
        self._storage.put_calc_next_block_height(context, calc_block_height)

    def get_calc_next_block_height(self, context: 'IconScoreContext') -> Optional[int]:
        value: Optional[int] = self._storage.get_calc_next_block_height(context)
        return value

    def put_calc_period(self, context: 'IconScoreContext', calc_period: int):
        self._storage.put_calc_period(context, calc_period)

    def get_calc_period(self, context: 'IconScoreContext') -> Optional[int]:
        value: Optional[int] = self._storage.get_calc_period(context)
        return value

    def put_total_candidate_delegated(self, context: 'IconScoreContext', total_candidate_delegated: int):
        self._storage.put_total_candidate_delegated(context, total_candidate_delegated)

    def get_total_candidate_delegated(self, context: 'IconScoreContext') -> int:
        value: Optional[int] = self._storage.get_total_candidate_delegated(context)
        if value is None:
            return 0
        return value
