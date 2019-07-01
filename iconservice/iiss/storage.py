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

from ..base.ComponentBase import StorageBase
from ..icon_constant import IISS_MAX_REWARD_RATE, ConfigKey
from ..utils.msgpack_for_db import MsgPackForDB

if TYPE_CHECKING:
    from ..iconscore.icon_score_context import IconScoreContext


class Storage(StorageBase):
    PREFIX: bytes = b'iiss'
    UNSTAKE_LOCK_PERIOD_KEY: bytes = PREFIX + b'ulp'
    REWARD_PREP_KEY: bytes = PREFIX + b'rprep'
    CALC_NEXT_BLOCK_HEIGHT_KEY: bytes = PREFIX + b'cnbh'
    CALC_PERIOD_KEY: bytes = PREFIX + b'pk'
    TOTAL_PREP_DELEGATED_KEY: bytes = PREFIX + b'tcd'

    def open(self,
             context: 'IconScoreContext',
             unstake_lock_period: int,
             reward_meta_data: dict,
             calc_period: int):
        self.check_config_before_init(reward_meta_data)

        if self.get_unstake_lock_period(context) is None:
            self.put_unstake_lock_period(context, unstake_lock_period)

        if self.get_reward_prep(context) is None:
            reward_prep = Reward(reward_rate=None,
                                 reward_min=reward_meta_data[ConfigKey.REWARD_MIN],
                                 reward_max=reward_meta_data[ConfigKey.REWARD_MAX],
                                 reward_point=reward_meta_data[ConfigKey.REWARD_POINT])
            self.put_reward_prep(context, reward_prep)

        if self.get_calc_period(context) is None:
            self.put_calc_period(context, calc_period)

    @staticmethod
    def check_config_before_init(reward_variable: dict):
        for value in reward_variable.values():
            if not 0 < value <= IISS_MAX_REWARD_RATE:
                raise AssertionError(f"Invalid reward variable: Cannot set zero or under "
                                     f"and more than {IISS_MAX_REWARD_RATE}")

    def put_reward_prep(self, context: 'IconScoreContext', reward_prep: 'Reward'):
        self._db.put(context, self.REWARD_PREP_KEY, reward_prep.to_bytes())

    def get_reward_prep(self, context: 'IconScoreContext') -> Optional['Reward']:
        reward_prep: Optional[bytes] = self._db.get(context, self.REWARD_PREP_KEY)
        if reward_prep:
            return Reward.from_bytes(reward_prep)

    def put_end_block_height_of_calc(self, context: 'IconScoreContext', calc_block_height: int):
        version = 0
        data: list = [version, calc_block_height]
        value: bytes = MsgPackForDB.dumps(data)
        self._db.put(context, self.CALC_NEXT_BLOCK_HEIGHT_KEY, value)

    def get_end_block_height_of_calc(self, context: 'IconScoreContext') -> Optional[int]:
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

    def put_total_prep_delegated(self, context: 'IconScoreContext', total_prep_delegated: int):
        version = 0
        data: list = [version, total_prep_delegated]
        value: bytes = MsgPackForDB.dumps(data)
        self._db.put(context, self.TOTAL_PREP_DELEGATED_KEY, value)

    def get_total_prep_delegated(self, context: 'IconScoreContext') -> int:
        value: bytes = self._db.get(context, self.TOTAL_PREP_DELEGATED_KEY)
        if value:
            data: list = MsgPackForDB.loads(value)
            version: int = data[0]
            total_prep_delegated: int = data[1]
            return total_prep_delegated
        return 0

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


class Reward:
    _VERSION = 0

    def __init__(self,
                 reward_rate: Optional[int],
                 reward_min: int,
                 reward_max: int,
                 reward_point: int):
        self.reward_rate: Optional[int] = reward_rate
        self.reward_min: int = reward_min
        self.reward_max: int = reward_max
        self.reward_point: int = reward_point

    @classmethod
    def from_bytes(cls, buf: bytes) -> 'Reward':
        data: list = MsgPackForDB.loads(buf)
        version = data[0]

        return cls(*data[1:])

    def to_bytes(self):
        data: list = [
            self._VERSION,
            self.reward_rate,
            self.reward_min,
            self.reward_max,
            self.reward_point
        ]
        return MsgPackForDB.dumps(data)
