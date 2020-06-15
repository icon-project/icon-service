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
from ..base.exception import FatalException
from ..icon_constant import IISS_MAX_REWARD_RATE, ConfigKey
from ..utils.msgpack_for_db import MsgPackForDB

if TYPE_CHECKING:
    from ..iconscore.icon_score_context import IconScoreContext
    from ..database.db import ContextDatabase


class Storage(StorageBase):
    PREFIX: bytes = b'iiss'

    IISS_META_DATA_KEY: bytes = PREFIX + b'md'
    REWARD_RATE_KEY: bytes = PREFIX + b'rr'
    TOTAL_STAKE_KEY: bytes = PREFIX + b'ts'

    CALC_END_BLOCK_HEIGHT_KEY: bytes = PREFIX + b'cebh'
    CALC_PERIOD_KEY: bytes = PREFIX + b'pk'

    def __init__(self, db: 'ContextDatabase'):
        super().__init__(db)
        self._meta_data: Optional['IISSMetaData'] = None

    def open(self,
             context: 'IconScoreContext',
             iiss_meta_data: dict,
             calc_period: int):
        self.check_config_before_init(iiss_meta_data)

        meta_data: Optional['IISSMetaData'] = self.get_meta_data(context)
        if meta_data is None:
            meta_data = IISSMetaData(reward_min=iiss_meta_data[ConfigKey.REWARD_MIN],
                                     reward_max=iiss_meta_data[ConfigKey.REWARD_MAX],
                                     reward_point=iiss_meta_data[ConfigKey.REWARD_POINT],
                                     lock_min=iiss_meta_data[ConfigKey.UN_STAKE_LOCK_MIN],
                                     lock_max=iiss_meta_data[ConfigKey.UN_STAKE_LOCK_MAX])
            self.put_meta_data(context, meta_data)

        if self.get_calc_period(context) is None:
            self.put_calc_period(context, calc_period)

        self._meta_data: 'IISSMetaData' = meta_data

    def rollback(self, context: 'IconScoreContext', block_height: int, block_hash: bytes):
        pass

    @property
    def reward_min(self) -> int:
        return self._meta_data.reward_min

    @property
    def reward_max(self) -> int:
        return self._meta_data.reward_max

    @property
    def reward_point(self) -> int:
        return self._meta_data.reward_point

    @property
    def lock_min(self) -> int:
        return self._meta_data.lock_min

    @property
    def lock_max(self) -> int:
        return self._meta_data.lock_max

    @staticmethod
    def check_config_before_init(iiss_variable: dict):
        for k, v in iiss_variable.items():
            if k.startswith('reward') and not 0 < v <= IISS_MAX_REWARD_RATE:
                raise FatalException(f"Out of reward rate range: 0 < {v} <= {IISS_MAX_REWARD_RATE}")

    def put_meta_data(self, context: 'IconScoreContext', constant: 'IISSMetaData'):
        self._db.put(context, self.IISS_META_DATA_KEY, constant.to_bytes())

    def get_meta_data(self, context: 'IconScoreContext') -> Optional['IISSMetaData']:
        value: Optional[bytes] = self._db.get(context, self.IISS_META_DATA_KEY)
        if value:
            return IISSMetaData.from_bytes(value)
        else:
            return None

    def put_reward_rate(self, context: 'IconScoreContext', reward_rate: 'RewardRate'):
        self._db.put(context, self.REWARD_RATE_KEY, reward_rate.to_bytes())

    def get_reward_rate(self, context: 'IconScoreContext') -> Optional['RewardRate']:
        value: Optional[bytes] = self._db.get(context, self.REWARD_RATE_KEY)
        if value:
            return RewardRate.from_bytes(value)
        else:
            return RewardRate(reward_prep=None)

    def put_total_stake(self, context: 'IconScoreContext', total_stake: int):
        version = 0
        data: bytes = MsgPackForDB.dumps([version, total_stake])
        self._db.put(context, self.TOTAL_STAKE_KEY, data)

    def get_total_stake(self, context: 'IconScoreContext') -> int:
        value: bytes = self._db.get(context, self.TOTAL_STAKE_KEY)
        if value:
            data = MsgPackForDB.loads(value)
            version: int = data[0]
            assert version == 0
            total_stake: int = data[1]
            return total_stake
        else:
            return 0

    def put_end_block_height_of_calc(self, context: 'IconScoreContext', calc_block_height: int):
        version = 0
        data: list = [version, calc_block_height]
        value: bytes = MsgPackForDB.dumps(data)
        self._db.put(context, self.CALC_END_BLOCK_HEIGHT_KEY, value)

    def get_end_block_height_of_calc(self, context: 'IconScoreContext') -> Optional[int]:
        value: bytes = self._db.get(context, self.CALC_END_BLOCK_HEIGHT_KEY)
        if value:
            data: list = MsgPackForDB.loads(value)
            version: int = data[0]
            assert version == 0
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
            assert version == 0
            calc_period: int = data[1]
            return calc_period
        return None


class RewardRate:
    _VERSION = 0

    def __init__(self,
                 reward_prep: Optional[int]):
        # todo: if eep, dapp is added, eep_rate, dapp rate is added as a member variable
        self.reward_prep: Optional[int] = reward_prep

    def __str__(self):
        return f"reward_prep={self.reward_prep}"

    @classmethod
    def from_bytes(cls, buf: bytes) -> 'RewardRate':
        data: list = MsgPackForDB.loads(buf)
        version = data[0]
        assert version == cls._VERSION

        return cls(*data[1:])

    def to_bytes(self):
        data: list = [
            self._VERSION,
            self.reward_prep
        ]
        return MsgPackForDB.dumps(data)


class IISSMetaData:
    _VERSION = 0

    def __init__(self,
                 reward_min: int,
                 reward_max: int,
                 reward_point: int,
                 lock_min: int,
                 lock_max: int):
        self.reward_min: int = reward_min
        self.reward_max: int = reward_max
        self.reward_point: int = reward_point
        self.lock_min: int = lock_min
        self.lock_max: int = lock_max

    def __str__(self):
        return f"reward_min={self.reward_min}, " \
               f"reward_max={self.reward_max}, " \
               f"reward_point={self.reward_point}, " \
               f"lock_min={self.lock_min}, " \
               f"lock_max={self.lock_max}"

    @classmethod
    def from_bytes(cls, buf: bytes) -> 'IISSMetaData':
        data: list = MsgPackForDB.loads(buf)
        version = data[0]
        assert version == cls._VERSION

        return cls(*data[1:])

    def to_bytes(self):
        data: list = [
            self._VERSION,
            self.reward_min,
            self.reward_max,
            self.reward_point,
            self.lock_min,
            self.lock_max
        ]
        return MsgPackForDB.dumps(data)
