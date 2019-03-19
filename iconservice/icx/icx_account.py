# -*- coding: utf-8 -*-

# Copyright 2018 ICON Foundation
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

from ..base.exception import InvalidParamsException, OutOfBalanceException
from ..icon_constant import DEFAULT_BYTE_SIZE, DATA_BYTE_ORDER

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..base.address import Address

ACCOUNT_DATA_STRUCTURE_VERSION = 0


@unique
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


@unique
class AccountFlag(IntEnum):
    """Account bitwise flags
    """
    # Whether account is locked or not
    LOCKED = 0x01
    # Is community representative
    C_REP = 0x02
    # Is this score installed successfully?
    INSTALLED = 0x04


class Account(object):
    """Account class
    Contains information of the account indicated by address.
    """

    # leveldb account value structure (bigendian, 36 bytes)
    # version(1) | type(1) | flags(1) | reserved(1) |
    # icx(DEFAULT_BYTE_SIZE)
    _struct = Struct(f'>BBBx{DEFAULT_BYTE_SIZE}s')

    def __init__(self,
                 account_type: 'AccountType'=AccountType.GENERAL,
                 address: 'Address'=None,
                 icx: int=0,
                 locked: bool=False,
                 c_rep: bool=False,
                 installed: bool=False) -> None:
        """Constructor
        """
        self._type = account_type
        self._address = address
        self._icx = icx
        self._locked = locked
        self._c_rep = c_rep
        self._installed = installed

    @property
    def address(self) -> 'Address':
        """Address object

        :return: (Address)
        """
        return self._address

    @address.setter
    def address(self, value: 'Address') -> None:
        """address setter

        :param value: account address
        """
        self._address = value

    @property
    def type(self) -> 'AccountType':
        """AccountType getter

        :return: AccountType value
        """
        return self._type

    @type.setter
    def type(self, value: 'AccountType') -> None:
        """AccountType setter

        :param value: (AccountType)
        """
        if not isinstance(value, AccountType):
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
    def c_rep(self) -> bool:
        """Is this community representative?

        :return: True(c_rep) False(not c_rep)
        """
        return self._c_rep

    @c_rep.setter
    def c_rep(self, value: bool) -> None:
        """c_rep setter

        :param value: True(c_rep) False(not c_rep)
        """
        self._c_rep = bool(value)

    @property
    def installed(self) -> bool:
        """Is this score installed successfully?
        """
        return self._installed

    @installed.setter
    def installed(self, value: bool) -> None:
        """Is this score installed successfully?
        """
        self._installed = bool(value)

    @property
    def icx(self) -> int:
        """Returns the balance of the account in loop unit (1 icx == 1e18 loop)

        :return: balance in loop
        """
        return self._icx

    def deposit(self, value: int) -> None:
        """Deposit coin

        :param value: amount to deposit in loop (1 icx == 1e18 loop)

        """
        if not isinstance(value, int) or value < 0:
            raise InvalidParamsException(
                'Failed to deposit: value is not int type or value < 0')

        self._icx += value

    def withdraw(self, value: int) -> None:
        """Withdraw coin

        :param value: coin amount to withdraw
        """
        if not isinstance(value, int) or value < 0:
            raise InvalidParamsException(
                'Failed to withdraw: value is not int type or value < 0')
        if self._icx < value:
            raise OutOfBalanceException('Out of balance')

        self._icx -= value

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

        version, account_type, flags, amount = \
            Account._struct.unpack(buf)

        amount = int.from_bytes(amount, DATA_BYTE_ORDER)

        account = Account()
        account.type = AccountType.from_int(account_type)
        account._locked = bool(flags & AccountFlag.LOCKED)
        account._c_rep = bool(flags & AccountFlag.C_REP)
        account._icx = amount

        return account

    def to_bytes(self) -> bytes:
        """Convert Account object to bytes

        :return: data including information of account object
        """

        # for extendability
        version = ACCOUNT_DATA_STRUCTURE_VERSION

        flags = 0
        if self._locked:
            flags |= AccountFlag.LOCKED
        if self._c_rep:
            flags |= AccountFlag.C_REP

        return Account._struct.pack(version, self._type, flags, self._icx.to_bytes(DEFAULT_BYTE_SIZE, DATA_BYTE_ORDER))

    def __bytes__(self) -> bytes:
        """operator bytes() overriding

        :return: binary data including information of account object
        """
        return self.to_bytes()
