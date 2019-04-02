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

from ..utils.msgpack_for_db import MsgPackForDB
from ..base.exception import InvalidParamsException

if TYPE_CHECKING:
    from ..base.address import Address


class StakePart(object):
    prefix = b"aos|"

    def __init__(self, address: 'Address'):
        self._address: 'Address' = address
        self._stake: int = 0
        self._unstake: int = 0
        self._unstake_block_height: int = 0

    @staticmethod
    def make_key(address: 'Address'):
        return StakePart.prefix + address.to_bytes_including_prefix()

    @property
    def address(self) -> 'Address':
        return self._address

    @property
    def stake(self):
        return self._stake

    @property
    def unstake(self):
        return self._unstake

    @property
    def unstake_block_height(self):
        return self._unstake_block_height

    def update_stake(self, value):
        self._stake += value

    def update_unstake(self, next_block_height: int, value: int):
        if self._stake < value:
            raise InvalidParamsException(f'Failed to unstake: stake_amount({self._stake}) < value({value})')

        self._stake -= value
        self._unstake += value
        self._unstake_block_height: int = next_block_height

    def finish_unstake(self) -> int:
        unstake: int = self._unstake
        self._unstake = 0
        self._unstake_block_height: int = 0
        return unstake

    @staticmethod
    def from_bytes(buf: bytes, address: 'Address') -> 'StakePart':
        """Create Account of Stake object from bytes data

        :param buf: (bytes) bytes data including Account of Stake information
        :param address:
        :return: (AccountOfStake) AccountOfStake object
        """

        data: list = MsgPackForDB.loads(buf)
        version = data[0]

        obj = StakePart(address)
        obj._stake_amount: int = data[1]
        obj._unstake_amount: int = data[2]
        obj._unstake_block_height: int = data[3]
        return obj

    def to_bytes(self) -> bytes:
        """Convert Account of Stake object to bytes

        :return: data including information of StakePart object
        """

        version = 0
        data = [version,
                self._stake,
                self._unstake,
                self._unstake_block_height]
        return MsgPackForDB.dumps(data)

    def __eq__(self, other) -> bool:
        """operator == overriding

        :param other: (StakePart)
        """

        return isinstance(other, StakePart) \
               and self._address == other.address \
               and self._stake == other.stake_amount \
               and self._unstake == other.unstake_amount \
               and self._unstake_block_height == other.unstake_block_height

    def __ne__(self, other) -> bool:
        """operator != overriding

        :param other: (StakePart)
        """
        return not self.__eq__(other)