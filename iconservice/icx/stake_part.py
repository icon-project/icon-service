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

from typing import TYPE_CHECKING

from ..utils import is_flags_on, toggle_flags
from ..base.exception import InvalidParamsException
from .icx_account import PartFlag
from ..utils.msgpack_for_db import MsgPackForDB

if TYPE_CHECKING:
    from ..base.address import Address


class StakePart(object):
    _VERSION = 0
    PREFIX = b"aos|"

    def __init__(self, stake: int = 0, unstake: int = 0, unstake_block_height: int = 0):
        self._stake: int = stake
        self._unstake: int = unstake
        self._unstake_block_height: int = unstake_block_height
        self._flags: int = PartFlag.NONE

    @staticmethod
    def make_key(address: 'Address') -> bytes:
        return StakePart.PREFIX + address.to_bytes_including_prefix()

    @property
    def stake(self) -> int:
        assert is_flags_on(self._flags, PartFlag.STAKE_COMPLETE)

        return self._stake

    @property
    def voting_weight(self) -> int:
        assert is_flags_on(self._flags, PartFlag.STAKE_COMPLETE)

        return self._stake

    @property
    def unstake(self) -> int:
        assert is_flags_on(self._flags, PartFlag.STAKE_COMPLETE)

        return self._unstake

    @property
    def unstake_block_height(self) -> int:
        assert is_flags_on(self._flags, PartFlag.STAKE_COMPLETE)

        return self._unstake_block_height

    @property
    def total_stake(self) -> int:
        assert is_flags_on(self._flags, PartFlag.STAKE_COMPLETE)

        return self._stake + self._unstake

    @property
    def flags(self) -> int:
        return self._flags

    def add_stake(self, value: int):
        assert is_flags_on(self._flags, PartFlag.STAKE_COMPLETE)

        self._stake += value
        self._flags = toggle_flags(self._flags, PartFlag.STAKE_DIRTY, True)

    def set_unstake(self, block_height: int, value: int):
        assert is_flags_on(self._flags, PartFlag.STAKE_COMPLETE)

        if self.total_stake < value:
            raise InvalidParamsException(f'Failed to unstake: stake_amount({self._stake}) < value({value})')

        self._stake = self.total_stake - value
        self._unstake = value
        self._unstake_block_height: int = block_height
        self._flags = toggle_flags(self._flags, PartFlag.STAKE_DIRTY, True)

    def update(self, block_height: int) -> int:

        unstake: int = self._unstake

        if block_height > self._unstake_block_height:
            self._unstake = 0
            self._unstake_block_height: int = 0
            self._flags = toggle_flags(self._flags, PartFlag.STAKE_DIRTY, True)

        self._flags = toggle_flags(self._flags, PartFlag.STAKE_COMPLETE, True)
        return unstake

    @staticmethod
    def from_bytes(buf: bytes) -> 'StakePart':
        """Create Account of Stake object from bytes data

        :param buf: (bytes) bytes data including Account of Stake information
        :return: (AccountOfStake) AccountOfStake object
        """

        data: list = MsgPackForDB.loads(buf)
        version = data[0]

        assert version == StakePart._VERSION

        return StakePart(stake=data[1], unstake=data[2], unstake_block_height=data[3])

    def to_bytes(self) -> bytes:
        """Convert Account of Stake object to bytes

        :return: data including information of StakePart object
        """

        assert is_flags_on(self._flags, PartFlag.STAKE_COMPLETE)

        data = [self._VERSION,
                self._stake,
                self._unstake,
                self._unstake_block_height]
        return MsgPackForDB.dumps(data)

    def __eq__(self, other) -> bool:
        """operator == overriding

        :param other: (StakePart)
        """

        assert is_flags_on(self._flags, PartFlag.STAKE_COMPLETE)

        return isinstance(other, StakePart) \
            and self._stake == other.stake \
            and self._unstake == other.unstake \
            and self._unstake_block_height == other.unstake_block_height

    def __ne__(self, other) -> bool:
        """operator != overriding

        :param other: (StakePart)
        """

        assert is_flags_on(self._flags, PartFlag.STAKE_COMPLETE)

        return not self.__eq__(other)
