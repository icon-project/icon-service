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

from enum import IntEnum, unique
from struct import Struct

from ...base.msgpack_util import MsgPackConverter, TypeTag
from ...base.exception import InvalidParamsException, OutOfBalanceException
from ...icon_constant import DEFAULT_BYTE_SIZE, DATA_BYTE_ORDER, REVISION_4

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...base.address import Address


@unique
class CoinAccountVersion(IntEnum):
    OLD = 0
    MSG_PACK = 1


@unique
class CoinAccountType(IntEnum):
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
        for _type in CoinAccountType:
            if value == _type:
                return _type

        raise ValueError('Invalid AccountType value')


@unique
class CoinAccountFlag(IntEnum):
    """Account bitwise flags
    """
    # Whether account is locked or not
    LOCKED = 0x01


class CoinAccount(object):
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
                 account_type: 'CoinAccountType' = CoinAccountType.GENERAL,
                 balance: int = 0,
                 locked: bool = False) -> None:
        """Constructor
        """
        self._address: 'Address' = address
        self._type: 'CoinAccountType' = account_type
        self._balance: int = balance
        self._locked: bool = locked

    @staticmethod
    def make_key(address: 'Address'):
        return address.to_bytes()

    @property
    def address(self) -> 'Address':
        """Address object

        :return: (Address)
        """
        return self._address

    @property
    def type(self) -> 'CoinAccountType':
        """CoinAccountType getter

        :return: CoinAccountType value
        """
        return self._type

    @type.setter
    def type(self, value: 'CoinAccountType') -> None:
        """CoinAccountType setter

        :param value: (AccountType)
        """
        if not isinstance(value, CoinAccountType):
            raise ValueError('Invalid AccountType')
        self._type = value

    @property
    def locked(self) -> bool:
        """Is this locked?

        :return: True(locked) False(unlocked)
        """
        return self._locked

    @locked.setter
    def locked(self, value: bool) -> None:
        """locked setter

        :param value: True(locked) False(unlocked)
        """
        self._locked = bool(value)

    @property
    def balance(self) -> int:
        """Returns the balance of the account in loop unit (1 icx == 1e18 loop)

        :return: balance in loop
        """
        return self._balance

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

        :param other: (CoinAccount)
        """
        return isinstance(other, CoinAccount) \
               and self.address == other.address \
               and self.balance == other.balance \
               and self.type == other.type \
               and self.locked == other.locked

    def __ne__(self, other) -> bool:
        """operator != overriding

        :param other: (CoinAccount)
        """
        return not self.__eq__(other)

    @staticmethod
    def from_bytes(buf: bytes, address: 'Address') -> 'CoinAccount':
        """Create CoinAccount object from bytes data

        :param buf: (bytes) bytes data including Account information
        :param address:
        :return: (CoinAccount) account object
        """

        if len(buf) == CoinAccount._old_bytes_length and buf[0] == 0:
            return CoinAccount._from_bytes_old(buf, address)
        else:
            return CoinAccount._from_bytes_msg_pack(buf, address)

    @staticmethod
    def _from_bytes_old(buf: bytes, address: 'Address') -> 'CoinAccount':
        version, account_type, flags, amount = CoinAccount._struct_old.unpack(buf)
        obj = CoinAccount(address)
        obj.type = CoinAccountType.from_int(account_type)
        obj._locked = bool(flags & CoinAccountFlag.LOCKED)
        obj._balance = int.from_bytes(amount, DATA_BYTE_ORDER)
        return obj

    @staticmethod
    def _from_bytes_msg_pack(buf: bytes, address: 'Address') -> 'CoinAccount':
        data: list = MsgPackConverter.loads(buf)
        version = MsgPackConverter.decode(TypeTag.INT, data[0])
        if version == CoinAccountVersion.MSG_PACK:
            obj = CoinAccount(address)
            obj.type = CoinAccountType(MsgPackConverter.decode(TypeTag.INT, data[1]))
            flags = MsgPackConverter.decode(TypeTag.INT, data[2])
            obj._locked = bool(flags & CoinAccountFlag.LOCKED)
            obj._balance = MsgPackConverter.decode(TypeTag.INT, data[3])
            return obj
        else:
            raise InvalidParamsException(f"Invalid Account version: {version}")

    def to_bytes(self, revision: int = 0) -> bytes:
        """Convert CoinAccount object to bytes

        :return: data including information of CoinAccount object
        """

        if revision >= REVISION_4:
            return self._to_bytes_msg_pack()
        else:
            return self._to_bytes_old()

    def _to_bytes_msg_pack(self) -> bytes:
        flags = 0
        if self._locked:
            flags |= CoinAccountFlag.LOCKED

        version = CoinAccountVersion.MSG_PACK
        data = [MsgPackConverter.encode(version),
                MsgPackConverter.encode(self._type),
                MsgPackConverter.encode(flags),
                MsgPackConverter.encode(self.balance)]

        return MsgPackConverter.dumps(data)

    def _to_bytes_old(self) -> bytes:
        version: int = CoinAccountVersion.OLD
        flags = 0
        if self._locked:
            flags |= CoinAccountFlag.LOCKED
        return CoinAccount._struct_old.pack(version,
                                            self._type,
                                            flags,
                                            self._balance.to_bytes(DEFAULT_BYTE_SIZE, DATA_BYTE_ORDER))
