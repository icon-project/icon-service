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

from enum import IntEnum, unique, IntFlag
from struct import Struct
from typing import TYPE_CHECKING

from ..base.address import AddressPrefix
from ..base.exception import InvalidParamsException, OutOfBalanceException
from ..icon_constant import DEFAULT_BYTE_SIZE, DATA_BYTE_ORDER, REVISION_4
from ..utils.msgpack_for_db import MsgPackForDB

if TYPE_CHECKING:
    from iconservice.base.address import Address


@unique
class CoinPartVersion(IntEnum):
    STRUCT = 0
    MSG_PACK = 1


@unique
class CoinPartType(IntEnum):
    """CoinPartType Type
    """
    GENERAL = 0
    GENESIS = 1
    TREASURY = 2

    def __str__(self) -> str:
        return self.name


@unique
class CoinPartFlag(IntFlag):
    """Account bitwise flags
    """
    NONE = 0
    HAS_UNSTAKE = 1


class CoinPart(object):
    """Account class
    Contains information of the account indicated by address.
    """

    # leveldb account value structure (bigendian, 36 bytes)
    # version(1) | type(1) | flags(1) | reserved(1) |
    # icx(DEFAULT_BYTE_SIZE)

    _VERSION = CoinPartVersion.MSG_PACK
    _STRUCT_PACKED_BYTES_SIZE = 36
    _STRUCT_FORMAT = Struct(f'>BBBx{DEFAULT_BYTE_SIZE}s')

    def __init__(self,
                 account_type: 'CoinPartType' = CoinPartType.GENERAL,
                 flags: int = CoinPartFlag.NONE,
                 balance: int = 0):
        """Constructor
        """
        self._type: 'CoinPartType' = account_type
        self._flags: int = flags
        self._balance: int = balance

    @staticmethod
    def make_key(address: 'Address') -> bytes:
        if address.prefix == AddressPrefix.EOA:
            return address.body
        else:
            return address.to_bytes_including_prefix()

    @property
    def type(self) -> 'CoinPartType':
        """CoinPartType getter

        :return: CoinPartType value
        """
        return self._type

    @type.setter
    def type(self, value: 'CoinPartType'):
        """CoinPartType setter

        :param value: (AccountType)
        """
        if not isinstance(value, CoinPartType):
            raise ValueError('Invalid CoinPartType')
        self._type = value

    @property
    def balance(self) -> int:
        """Returns the balance of the account in loop unit (1 icx == 1e18 loop)

        :return: balance in loop
        """
        return self._balance

    @property
    def flags(self) -> int:
        """CoinPartFlag getter

        :return: CoinPartType value
        """
        return self._flags

    def is_flag_on(self, flag: 'CoinPartFlag') -> bool:
        return self._flags & flag == flag

    def toggle_flag(self, flag: 'CoinPartFlag', on: bool):
        if on:
            self._flags |= flag
        else:
            self._flags &= ~flag

    def deposit(self, value: int):
        """Deposit coin

        :param value: amount to deposit in loop (1 icx == 1e18 loop)

        """
        if not isinstance(value, int) or value < 0:
            raise InvalidParamsException(
                'Failed to deposit: value is not int type or value < 0')

        self._balance += value

    def withdraw(self, value: int):
        """Withdraw coin

        :param value: coin amount to withdraw
        """
        if not isinstance(value, int) or value < 0:
            raise InvalidParamsException(
                'Failed to withdraw: value is not int type or value < 0')

        if self._balance < value:
            raise OutOfBalanceException('Out of balance')

        self._balance -= value

    def __eq__(self, other) -> bool:
        """operator == overriding

        :param other: (CoinPart)
        """
        return isinstance(other, CoinPart) \
            and self.balance == other.balance \
            and self.type == other.type \
            and self.flags == other.flags

    def __ne__(self, other) -> bool:
        """operator != overriding

        :param other: (CoinPart)
        """
        return not self.__eq__(other)

    @staticmethod
    def from_bytes(buf: bytes) -> 'CoinPart':
        """Create CoinPart object from bytes data

        :param buf: (bytes) bytes data including Account information
        :return: (CoinPart) account object
        """

        if len(buf) == CoinPart._STRUCT_PACKED_BYTES_SIZE and buf[0] == CoinPartVersion.STRUCT:
            return CoinPart._from_struct_packed_bytes(buf)
        else:
            return CoinPart._from_msg_packed_bytes(buf)

    @staticmethod
    def _from_struct_packed_bytes(buf: bytes) -> 'CoinPart':
        version, coin_type, flags, amount = CoinPart._STRUCT_FORMAT.unpack(buf)
        balance: int = int.from_bytes(amount, DATA_BYTE_ORDER)
        return CoinPart(coin_type, flags, balance)

    @staticmethod
    def _from_msg_packed_bytes(buf: bytes) -> 'CoinPart':
        data: list = MsgPackForDB.loads(buf)
        version: int = data[0]

        assert version <= CoinPart._VERSION

        if version != CoinPartVersion.MSG_PACK:
            raise InvalidParamsException(f"Invalid Account version: {version}")

        return CoinPart(account_type=data[1], flags=data[2], balance=data[3])

    def to_bytes(self, revision: int = 0) -> bytes:
        """Convert CoinPart object to bytes

        :return: data including information of CoinPart object
        """
        if revision >= REVISION_4:
            return self._to_msg_packed_bytes()
        else:
            return self._to_struct_packed_bytes()

    def _to_msg_packed_bytes(self) -> bytes:
        data = [
            CoinPartVersion.MSG_PACK,
            self._type,
            self._flags,
            self.balance
        ]

        return MsgPackForDB.dumps(data)

    def _to_struct_packed_bytes(self) -> bytes:
        return CoinPart._STRUCT_FORMAT.pack(CoinPartVersion.STRUCT,
                                            self._type,
                                            self._flags,
                                            self._balance.to_bytes(DEFAULT_BYTE_SIZE, DATA_BYTE_ORDER))
