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

from ...base.msgpack_util import MsgPackConverter, TypeTag
from ...base.exception import InvalidParamsException

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...base.address import Address


class StakeAccount(object):
    prefix = b"aos|"

    def __init__(self, address: 'Address'):
        self._address: 'Address' = address
        self._stake_amount: int = 0
        self._unstake_amount: int = 0
        self._unstake_block_height: int = 0

    @staticmethod
    def make_key(address: 'Address'):
        return StakeAccount.prefix + MsgPackConverter.encode(address)

    @property
    def address(self) -> 'Address':
        return self._address

    @property
    def stake_amount(self):
        return self._stake_amount

    @property
    def unstake_amount(self):
        return self._unstake_amount

    @property
    def unstake_block_height(self):
        return self._unstake_block_height

    def stake(self, value):
        self._stake_amount += value

    def unstake(self, next_block_height: int, value: int):
        if self._stake_amount < value:
            raise InvalidParamsException(f'Failed to unstake: stake_amount({self._stake_amount}) < value({value})')

        self._stake_amount -= value
        self._unstake_amount += value
        self._unstake_block_height: int = next_block_height

    @staticmethod
    def from_bytes(buf: bytes, address: 'Address') -> 'StakeAccount':
        """Create Account of Stake object from bytes data

        :param buf: (bytes) bytes data including Account of Stake information
        :param address:
        :return: (AccountOfStake) AccountOfStake object
        """

        data: list = MsgPackConverter.loads(buf)
        version = MsgPackConverter.decode(TypeTag.INT, data[0])

        obj = StakeAccount(address)
        obj._stake_amount: int = MsgPackConverter.decode(TypeTag.INT, data[1])
        obj._unstake_amount: int = MsgPackConverter.decode(TypeTag.INT, data[2])
        obj._unstake_block_height: int = MsgPackConverter.decode(TypeTag.INT, data[3])
        return obj

    def to_bytes(self) -> bytes:
        """Convert Account of Stake object to bytes

        :return: data including information of StakeAccount object
        """

        version = 0
        data = [MsgPackConverter.encode(version),
                MsgPackConverter.encode(self._stake_amount),
                MsgPackConverter.encode(self._unstake_amount),
                MsgPackConverter.encode(self._unstake_block_height)]
        return MsgPackConverter.dumps(data)

    def __eq__(self, other) -> bool:
        """operator == overriding

        :param other: (StakeAccount)
        """

        return isinstance(other, StakeAccount) \
               and self._address == other.address \
               and self._stake_amount == other.stake_amount \
               and self._unstake_amount == other.unstake_amount \
               and self._unstake_block_height == other.unstake_block_height

    def __ne__(self, other) -> bool:
        """operator != overriding

        :param other: (StakeAccount)
        """
        return not self.__eq__(other)