# -*- coding: utf-8 -*-

# Copyright 2017-2018 theloop Inc.
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

from .icx_config import BALANCE_BYTE_SIZE, DATA_BYTE_ORDER
from ..base.address import Address
from ..base.exception import ExceptionCode, IconException


ACCOUNT_DATA_STRUCTURE_VERSION = 0


class AccountType(IntEnum):
    """Account Type
    """
    GENERAL = 0
    GENESIS = 1
    TREASURY = 2
    CONTRACT = 3

    def __str__(self) -> str:
        return self.name

    def __int__(self) -> int:
        return self.value

    @staticmethod
    def from_int(value: int) -> IntEnum:
        for _type in AccountType:
            if value == _type:
                return _type

        raise ValueError('Invalid AccountType value')


class AccountFlag(IntEnum):
    """Account bitwise flags
    """
    # Whether account is locked or not
    LOCKED = 0x01
    # Is community representative
    C_REP = 0x02


class Account(object):
    """Account class
    Contains information of the account indicated by address.
    """

    # leveldb account value structure (bigendian, 36 bytes)
    # version(1) | type(1) | flags(1) | reserved(1) |
    # icx(BALANCE_BYTE_SIZE)
    __struct = Struct(f'>cccx{BALANCE_BYTE_SIZE}s')

    def __init__(self,
                 account_type: AccountType=AccountType.GENERAL,
                 address: Address=None,
                 icx: int=0,
                 locked: bool=False,
                 c_rep: bool=False) -> None:
        """Constructor
        """
        self.__type = account_type
        self.__address = address
        self.__icx = icx
        self.__locked = locked
        self.__c_rep = c_rep

    @property
    def address(self) -> Address:
        """Address object

        :return: (Address)
        """
        return self.__address

    @address.setter
    def address(self, value: Address) -> None:
        """address setter

        :param value: account address
        """
        self.__address = value

    @property
    def type(self) -> AccountType:
        """AccountType getter

        :return: AccountType value
        """
        return self.__type

    @type.setter
    def type(self, value: AccountType) -> None:
        """AccountType setter

        :param value: (AccountType)
        """
        if not isinstance(value, AccountType):
            raise ValueError('Invalid AccountType')
        self.__type = value

    @property
    def locked(self) -> bool:
        """Is this locked?

        :return: True(locked) False(unlocked)
        """
        return self.__locked

    @locked.setter
    def locked(self, value: bool) -> None:
        """locked setter

        :param value: True(locked) False(unlocked)
        """
        self.__locked = bool(value)

    @property
    def c_rep(self) -> bool:
        """Is this community representative?

        :return: True(c_rep) False(not c_rep)
        """
        return self.__c_rep

    @c_rep.setter
    def c_rep(self, value: bool) -> None:
        """c_rep setter

        :param value: True(c_rep) False(not c_rep)
        """
        self.__c_rep = bool(value)

    @property
    def icx(self) -> int:
        """Returns the balance of the account in loop unit (1 icx == 1e18 loop)

        :return: balance in loop
        """
        return self.__icx

    def deposit(self, value: int) -> None:
        """Deposit coin

        :param value: amount to deposit in loop (1 icx == 1e18 loop)

        """
        if not isinstance(value, int) or value <= 0:
            raise IconException(Code.INVALID_PARAMS)

        self.__icx += value

    def withdraw(self, value: int) -> None:
        """Withdraw coin

        :param value: coin amount to withdraw
        """
        if not isinstance(value, int) or value <= 0:
            raise IconException(Code.INVALID_PARAMS)
        if self.__icx < value:
            raise IconException(Code.NOT_ENOUGH_BALANCE)

        self.__icx -= value

    def __eq__(self, other) -> bool:
        """operator == overriding

        :param other: (Account)
        """
        return isinstance(other, Account) \
            and self.address == other.address \
            and self.icx == other.icx \
            and self.type == other.type \
            and self.locked == other.locked \
            and self.c_rep == other.c_rep

    def __ne__(self, other) -> bool:
        """operator != overriding

        :param other: (Account)
        """
        return not self.__eq__(other)

    @staticmethod
    def from_bytes(buf: bytes):
        """Create Account object from bytes data

        :param buf: (bytes) bytes data including Account information
        :return: (Account) account object
        """
        byteorder = DATA_BYTE_ORDER

        version, account_type, flags, amount = \
            Account.__struct.unpack(buf)

        version = int.from_bytes(version, byteorder)
        account_type = int.from_bytes(account_type, byteorder)
        flags = int.from_bytes(flags, byteorder)
        amount = int.from_bytes(amount, byteorder)

        account = Account()
        account.type = AccountType.from_int(account_type)
        account.__locked = bool(flags & AccountFlag.LOCKED)
        account.__c_rep = bool(flags & AccountFlag.C_REP)
        account.__icx = amount

        return account

    def to_bytes(self) -> bytes:
        """Convert Account object to bytes

        :return: data including information of account object
        """
        byteorder = DATA_BYTE_ORDER
        # for extendability
        version = ACCOUNT_DATA_STRUCTURE_VERSION

        flags = 0
        if self.__locked:
            flags |= AccountFlag.LOCKED
        if self.__c_rep:
            flags |= AccountFlag.C_REP

        return Account.__struct.pack(
            version.to_bytes(1, byteorder),
            self.__type.to_bytes(1, byteorder),
            flags.to_bytes(1, byteorder),
            self.__icx.to_bytes(BALANCE_BYTE_SIZE, byteorder))

    def __bytes__(self) -> bytes:
        """operator bytes() overriding

        :return: binary data including information of account object
        """
        return self.to_bytes()
