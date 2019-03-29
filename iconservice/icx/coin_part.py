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

from ..base.msgpack_util import MsgPackConverter, TypeTag
from ..base.exception import InvalidParamsException, OutOfBalanceException
from ..icon_constant import DEFAULT_BYTE_SIZE, DATA_BYTE_ORDER, REVISION_4

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from iconservice.base.address import Address


@unique
class CoinPartVersion(IntEnum):
    OLD = 0
    MSG_PACK = 1


@unique
class CoinPartType(IntEnum):
    """Account Type
    """
    GENERAL = 0
    GENESIS = 1
    TREASURY = 2

    def __str__(self) -> str:
        return self.name

    def __int__(self) -> int:
        return self.value

    @staticmethod
    def from_int(value: int) -> IntEnum:
        for _type in CoinPartType:
            if value == _type:
                return _type

        raise ValueError('Invalid AccountType value')


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

    _old_bytes_length = 36
    _struct_old = Struct(f'>BBBx{DEFAULT_BYTE_SIZE}s')

    def __init__(self,
                 address: 'Address',
                 account_type: 'CoinPartType' = CoinPartType.GENERAL,
                 balance: int = 0) -> None:
        """Constructor
        """
        self._address: 'Address' = address
        self._type: 'CoinPartType' = account_type
        self._balance: int = balance
        self._flag: 'CoinPartFlag' = CoinPartFlag.NONE

    @staticmethod
    def make_key(address: 'Address'):
        # legacy EOA: 20bytes, CA: 21 bytes
        return address.to_bytes()

    @property
    def address(self) -> 'Address':
        """Address object

        :return: (Address)
        """
        return self._address

    @property
    def type(self) -> 'CoinPartType':
        """CoinPartType getter

        :return: CoinPartType value
        """
        return self._type

    @type.setter
    def type(self, value: 'CoinPartType') -> None:
        """CoinPartType setter

        :param value: (AccountType)
        """
        if not isinstance(value, CoinPartType):
            raise ValueError('Invalid AccountType')
        self._type = value

    @property
    def balance(self) -> int:
        """Returns the balance of the account in loop unit (1 icx == 1e18 loop)

        :return: balance in loop
        """
        return self._balance

    @property
    def flag(self) -> 'CoinPartFlag':
        """CoinPartFlag getter

        :return: CoinPartType value
        """
        return self._flag

    def is_coin_flag_on(self, flag: 'CoinPartFlag') -> bool:
        return self._flag & flag == flag

    def coin_flag_enable(self, flag: 'CoinPartFlag') -> None:
        self._flag |= flag

    def coin_flag_disable(self, flag: 'CoinPartFlag') -> None:
        self._flag &= ~flag

    def deposit(self, value: int) -> None:
        """Deposit coin

        :param value: amount to deposit in loop (1 icx == 1e18 loop)

        """
        if not isinstance(value, int) or value < 0:
            raise InvalidParamsException(
                'Failed to deposit: value is not int type or value < 0')

        self._balance += value

    def withdraw(self, value: int) -> None:
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
               and self.address == other.address \
               and self.balance == other.balance \
               and self.type == other.type \
               and self._flag == other.flag

    def __ne__(self, other) -> bool:
        """operator != overriding

        :param other: (CoinPart)
        """
        return not self.__eq__(other)

    @staticmethod
    def from_bytes(buf: bytes, address: 'Address') -> 'CoinPart':
        """Create CoinPart object from bytes data

        :param buf: (bytes) bytes data including Account information
        :param address:
        :return: (CoinPart) account object
        """

        if len(buf) == CoinPart._old_bytes_length and buf[0] == 0:
            return CoinPart._from_bytes_old(buf, address)
        else:
            return CoinPart._from_bytes_msg_pack(buf, address)

    @staticmethod
    def _from_bytes_old(buf: bytes, address: 'Address') -> 'CoinPart':
        version, account_type, flags, amount = CoinPart._struct_old.unpack(buf)
        obj = CoinPart(address)
        obj.type = CoinPartType.from_int(account_type)
        obj._locked = False
        obj._balance = int.from_bytes(amount, DATA_BYTE_ORDER)
        return obj

    @staticmethod
    def _from_bytes_msg_pack(buf: bytes, address: 'Address') -> 'CoinPart':
        data: list = MsgPackConverter.loads(buf)
        version = MsgPackConverter.decode(TypeTag.INT, data[0])
        if version == CoinPartVersion.MSG_PACK:
            obj = CoinPart(address)
            obj.type = CoinPartType(MsgPackConverter.decode(TypeTag.INT, data[1]))
            flags = MsgPackConverter.decode(TypeTag.INT, data[2])
            obj._locked = bool(flags & CoinPartFlag.LOCKED)
            obj._balance = MsgPackConverter.decode(TypeTag.INT, data[3])
            return obj
        else:
            raise InvalidParamsException(f"Invalid Account version: {version}")

    def to_bytes(self, revision: int = 0) -> bytes:
        """Convert CoinPart object to bytes

        :return: data including information of CoinPart object
        """

        if revision >= REVISION_4:
            return self._to_bytes_msg_pack()
        else:
            return self._to_bytes_old()

    def _to_bytes_msg_pack(self) -> bytes:
        version = CoinPartVersion.MSG_PACK
        data = [MsgPackConverter.encode(version),
                MsgPackConverter.encode(self._type),
                MsgPackConverter.encode(self._flag),
                MsgPackConverter.encode(self.balance)]

        return MsgPackConverter.dumps(data)

    def _to_bytes_old(self) -> bytes:
        version: int = CoinPartVersion.OLD
        return CoinPart._struct_old.pack(version,
                                         self._type,
                                         self._flag,
                                         self._balance.to_bytes(DEFAULT_BYTE_SIZE, DATA_BYTE_ORDER))
