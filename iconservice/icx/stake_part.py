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

from typing import TYPE_CHECKING, Optional, List

from .base_part import BasePart, BasePartState
from ..base.exception import InvalidParamsException
from ..icon_constant import Revision, UNSTAKE_SLOT_MAX
from ..utils.msgpack_for_db import MsgPackForDB

if TYPE_CHECKING:
    from ..base.address import Address


class StakePart(BasePart):
    _VERSION = 0
    PREFIX = b"aos|"

    def __init__(self,
                 stake: int = 0,
                 unstake: int = 0,
                 unstake_block_height: int = 0,
                 unstakes_info: Optional[List] = None):
        super().__init__()

        self._stake: int = stake
        self._unstake: int = unstake
        self._unstake_block_height: int = unstake_block_height
        self._unstakes_info: List[List[int, int]] = unstakes_info if unstakes_info else []

    @staticmethod
    def make_key(address: 'Address') -> bytes:
        return StakePart.PREFIX + address.to_bytes_including_prefix()

    @property
    def stake(self) -> int:
        assert self.is_set(BasePartState.COMPLETE)
        return self._stake

    @property
    def voting_weight(self) -> int:
        assert self.is_set(BasePartState.COMPLETE)
        return self._stake

    @property
    def unstake(self) -> int:
        assert self.is_set(BasePartState.COMPLETE)
        return self._unstake

    @property
    def unstake_block_height(self) -> int:
        assert self.is_set(BasePartState.COMPLETE)
        return self._unstake_block_height

    @property
    def total_stake(self) -> int:
        assert self.is_set(BasePartState.COMPLETE)
        return self._stake + self.total_unstake

    @property
    def unstakes_info(self) -> List:
        assert self.is_set(BasePartState.COMPLETE)
        return self._unstakes_info

    @property
    def total_unstake(self) -> int:
        assert self.is_set(BasePartState.COMPLETE)
        return self._total_unstake()

    def _total_unstake(self) -> int:
        if self._unstakes_info:
            return sum(map(lambda unstakes_info: unstakes_info[0], self._unstakes_info)) + self._unstake
        return self._unstake

    def add_stake(self, value: int):
        assert self.is_set(BasePartState.COMPLETE)

        if value <= 0:
            raise InvalidParamsException("Failed to stake: value <= 0")

        self._stake += value
        self.set_dirty(True)

    def set_unstake(self, block_height: int, value: int):
        assert self.is_set(BasePartState.COMPLETE)

        if self.total_stake < value:
            raise InvalidParamsException(f'Failed to unstake: stake_amount({self._stake}) < value({value})')

        # FIXME: Consider the case when value is 0
        self._stake = self.total_stake - value
        self._unstake = value
        self._unstake_block_height: int = block_height

        self.set_dirty(True)

    def set_unstakes_info(self, block_height: int, new_total_unstake: int):
        total_stake = self.total_stake

        if new_total_unstake < self.total_unstake:
            self.withdraw_unstake(self.total_unstake - new_total_unstake)

        elif self.total_unstake < new_total_unstake:
            increment_unstake = new_total_unstake - self.total_unstake
            if len(self._unstakes_info) == UNSTAKE_SLOT_MAX:
                old_value_pair = self._unstakes_info.pop()
                increment_unstake += old_value_pair[0]
            new_value_index = self.find_index_highest_in_lower_height(block_height)
            self._unstakes_info.insert(new_value_index + 1, [increment_unstake, block_height])

        self._stake = total_stake - new_total_unstake
        self.set_dirty(True)

    def withdraw_unstake(self, amount: int):
        unstakes_length = len(self._unstakes_info)
        accumulated_unstake = 0
        total_unstake = self.total_unstake
        new_total_unstake = total_unstake - amount
        for index in range(unstakes_length):
            accumulated_unstake += self.unstakes_info[index][0]
            if new_total_unstake > accumulated_unstake:
                continue
            elif new_total_unstake == accumulated_unstake:
                self._unstakes_info = self.unstakes_info[:index + 1]
                return
            elif new_total_unstake < accumulated_unstake:
                self._unstakes_info = self.unstakes_info[:index + 1]
                old_value_pair = self._unstakes_info.pop()
                new_value_pair = \
                    [(total_unstake - accumulated_unstake + old_value_pair[0]) - amount, old_value_pair[1]]
                self._unstakes_info.append(new_value_pair)
                return

    def reset_unstake(self):
        assert self.is_set(BasePartState.COMPLETE)

        self._stake = self.total_stake
        self._unstake = 0
        self._unstake_block_height: int = 0
        self._unstakes_info = []

        self.set_dirty(True)

    def normalize(self, block_height: int, revision: int) -> int:
        unstake: int = 0
        state: 'BasePartState' = BasePartState.COMPLETE

        if revision >= Revision.MULTIPLE_UNSTAKE.value and self._unstake_block_height:
            self._unstakes_info.append([self._unstake, self._unstake_block_height])
            self._unstake = 0
            self._unstake_block_height = 0

        if self._unstakes_info:
            total_unstake = self._total_unstake()
            self._unstakes_info = [info for info in self._unstakes_info if info[1] >= block_height]
            new_total_unstake = self._total_unstake()
            if total_unstake > new_total_unstake:
                state |= BasePartState.DIRTY
                unstake = total_unstake - new_total_unstake

        if 0 < self._unstake_block_height < block_height:
            unstake: int = self._unstake
            self._unstake = 0
            self._unstake_block_height: int = 0

            state |= BasePartState.DIRTY

        self.toggle_state(state, True)

        return unstake

    @staticmethod
    def from_bytes(buf: bytes) -> 'StakePart':
        """Create Account of Stake object from bytes data

        :param buf: (bytes) bytes data including Account of Stake information
        :return: (AccountOfStake) AccountOfStake object
        """

        data: list = MsgPackForDB.loads(buf)
        version = data[0]

        if version == 0:
            data.append(None)

        return StakePart(stake=data[1], unstake=data[2], unstake_block_height=data[3], unstakes_info=data[4])

    def to_bytes(self, revision: int) -> bytes:
        """Convert Account of Stake object to bytes

        :return: data including information of StakePart object
        """

        assert self.is_set(BasePartState.COMPLETE)

        if revision >= Revision.MULTIPLE_UNSTAKE.value:
            version = 1
        else:
            version = 0

        data = [version,
                self._stake,
                self._unstake,
                self._unstake_block_height]

        if version >= 1:
            data.append(self._unstakes_info)

        return MsgPackForDB.dumps(data)

    def __eq__(self, other) -> bool:
        """operator == overriding

        :param other: (StakePart)
        """

        assert self.is_set(BasePartState.COMPLETE)

        return isinstance(other, StakePart) \
            and self._stake == other.stake \
            and self._unstake == other.unstake \
            and self._unstake_block_height == other.unstake_block_height \
            and self._unstakes_info == other.unstakes_info

    def __ne__(self, other) -> bool:
        """operator != overriding

        :param other: (StakePart)
        """

        assert self.is_set(BasePartState.COMPLETE)

        return not self.__eq__(other)

    def find_index_highest_in_lower_height(self, block_height: int):
        low: int = 0
        high: int = len(self._unstakes_info) - 1
        if high == -1:
            return 0
        elif high == 0:
            return 0 if block_height < self._unstakes_info[high][1] else 1
        while low < high:
            mid = (high + low) // 2
            if self._unstakes_info[mid][1] <= block_height < self._unstakes_info[mid + 1][1]:
                return mid
            elif self._unstakes_info[mid][1] > block_height:
                high = mid - 1
            elif self._unstakes_info[mid][1] <= block_height:
                low = mid + 1

        return low
