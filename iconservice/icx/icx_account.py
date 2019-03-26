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
from collections import OrderedDict
from enum import IntEnum, unique
from struct import Struct

from ..base.msgpack_util import MsgPackConverter, TypeTag
from ..base.exception import InvalidParamsException, OutOfBalanceException
from ..icon_constant import DEFAULT_BYTE_SIZE, DATA_BYTE_ORDER, REVISION_4

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..base.address import Address


@unique
class AccountVersion(IntEnum):
    OLD = 0
    MSG_PACK = 1


@unique
class AccountType(IntEnum):
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


class Account(object):
    """Account class
    Contains information of the account indicated by address.
    """

    # leveldb account value structure (bigendian, 36 bytes)
    # version(1) | type(1) | flags(1) | reserved(1) |
    # icx(DEFAULT_BYTE_SIZE)

    _old_bytes_length = 36
    _struct_old = Struct(f'>BBBx{DEFAULT_BYTE_SIZE}s')

    def __init__(self,
                 account_type: 'AccountType' = AccountType.GENERAL,
                 address: 'Address' = None,
                 balance: int = 0,
                 locked: bool = False) -> None:
        """Constructor
        """
        self._type: 'AccountType' = account_type
        self._address: 'Address' = address
        self._balance: int = balance
        self._locked: bool = locked

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

        :param other: (Account)
        """
        return isinstance(other, Account) \
               and self.address == other.address \
               and self.balance == other.balance \
               and self.type == other.type \
               and self.locked == other.locked

    def __ne__(self, other) -> bool:
        """operator != overriding

        :param other: (Account)
        """
        return not self.__eq__(other)

    @staticmethod
    def from_bytes(buf: bytes) -> 'Account':
        """Create Account object from bytes data

        :param buf: (bytes) bytes data including Account information
        :return: (Account) account object
        """

        if len(buf) == Account._old_bytes_length and buf[0] == 0:
            # old
            version, account_type, flags, amount = Account._struct_old.unpack(buf)
            obj = Account()
            obj.type = AccountType.from_int(account_type)
            obj._locked = bool(flags & AccountFlag.LOCKED)
            obj._balance = int.from_bytes(amount, DATA_BYTE_ORDER)
            return obj
        else:
            data: list = MsgPackConverter.loads(buf)
            version = MsgPackConverter.decode(TypeTag.INT, data[0])
            if version == AccountVersion.MSG_PACK:
                obj = Account()
                obj.type = AccountType(MsgPackConverter.decode(TypeTag.INT, data[1]))
                flags = MsgPackConverter.decode(TypeTag.INT, data[2])
                obj._locked = bool(flags & AccountFlag.LOCKED)
                obj._balance = MsgPackConverter.decode(TypeTag.INT, data[3])
                return obj
            else:
                raise InvalidParamsException(f"Invalid Account version: {version}")

    def to_bytes(self, revision: int = 0) -> bytes:
        """Convert Account object to bytes

        :return: data including information of Account object
        """

        if revision >= REVISION_4:
            flags = 0
            if self._locked:
                flags |= AccountFlag.LOCKED

            version = AccountVersion.MSG_PACK
            data = [MsgPackConverter.encode(version),
                    MsgPackConverter.encode(self._type),
                    MsgPackConverter.encode(flags),
                    MsgPackConverter.encode(self.balance)]

            return MsgPackConverter.dumps(data)
        else:
            version: int = AccountVersion.OLD
            flags = 0
            if self._locked:
                flags |= AccountFlag.LOCKED
            return Account._struct_old.pack(version,
                                            self._type,
                                            flags,
                                            self._balance.to_bytes(DEFAULT_BYTE_SIZE, DATA_BYTE_ORDER))


class AccountOfStake(object):
    prifix = "aos|"

    def __init__(self, address: 'Address'):
        self._address: 'Address' = address
        self._stake_amount: int = 0
        self._unstake_amount: int = 0
        self._unstake_block_height: int = 0

    @staticmethod
    def make_key(address: 'Address'):
        prefix_data: bytes = MsgPackConverter.encode(AccountOfStake.prifix)
        address_data: bytes = MsgPackConverter.encode(address)
        return prefix_data + address_data

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

    @staticmethod
    def from_bytes(buf: bytes, address: 'Address') -> 'AccountOfStake':
        """Create Account of Stake object from bytes data

        :param buf: (bytes) bytes data including Account of Stake information
        :param address:
        :return: (AccountOfStake) AccountOfStake object
        """

        data: list = MsgPackConverter.loads(buf)
        version = MsgPackConverter.decode(TypeTag.INT, data[0])

        obj = AccountOfStake(address)
        obj._stake_amount: int = MsgPackConverter.decode(TypeTag.INT, data[1])
        obj._unstake_amount: int = MsgPackConverter.decode(TypeTag.INT, data[2])
        obj._unstake_block_height: int = MsgPackConverter.decode(TypeTag.INT, data[3])
        return obj

    def to_bytes(self) -> bytes:
        """Convert Account of Stake object to bytes

        :return: data including information of AccountOfStake object
        """

        version = 0
        data = [MsgPackConverter.encode(version),
                MsgPackConverter.encode(self._stake_amount),
                MsgPackConverter.encode(self._unstake_amount),
                MsgPackConverter.encode(self._unstake_block_height)]
        return MsgPackConverter.dumps(data)

    def stake(self, value: int, account: 'Account') -> None:
        if not isinstance(value, int) or value < 0:
            raise InvalidParamsException('Failed to stake: value is not int type or value < 0')

        self._stake_amount += value
        account.withdraw(value)

    def unstake(self, next_block_height: int, value: int) -> None:
        if not isinstance(value, int) or value < 0:
            raise InvalidParamsException('Failed to unstake: value is not int type or value < 0')

        self._stake_amount -= value
        self._unstake_amount += value
        self._unstake_block_height: int = next_block_height

    def extension_balance(self, current_block_height: int) -> int:
        if current_block_height > self._unstake_block_height:
            return self._unstake_amount
        else:
            return 0

    def __eq__(self, other) -> bool:
        """operator == overriding

        :param other: (AccountOfStake)
        """

        return isinstance(other, AccountOfStake) \
               and self._address == other.address \
               and self._stake_amount == other.stake_amount \
               and self._unstake_amount == other.unstake_amount \
               and self._unstake_block_height == other.unstake_block_height

    def __ne__(self, other) -> bool:
        """operator != overriding

        :param other: (AccountOfStake)
        """
        return not self.__eq__(other)


class AccountOfDelegation(object):
    prifix = "aod|"

    def __init__(self, address: 'Address'):
        self._address: 'Address' = address
        self._delegated_amount: int = 0
        self._delegations: OrderedDict = OrderedDict()

    @staticmethod
    def make_key(address: 'Address'):
        prefix_data: bytes = MsgPackConverter.encode(AccountOfDelegation.prifix)
        address_data: bytes = MsgPackConverter.encode(address)
        return prefix_data + address_data

    @property
    def address(self) -> 'Address':
        return self._address

    @property
    def delegated_amount(self) -> int:
        return self._delegated_amount

    @property
    def delegations(self) -> OrderedDict:
        return self._delegations

    @staticmethod
    def from_bytes(buf: bytes, address: 'Address') -> 'AccountOfDelegation':
        """Create Account of Stake object from bytes data

        :param buf: (bytes) bytes data including Account of Delegation information
        :param address:
        :return: (AccountOfStake) AccountOfDelegation object
        """

        data: list = MsgPackConverter.loads(buf)
        version = MsgPackConverter.decode(TypeTag.INT, data[0])

        obj = AccountOfDelegation(address)
        obj._delegated_amount: int = MsgPackConverter.decode(TypeTag.INT, data[1])

        delegations: list = data[2]
        for i in range(0, len(delegations), 2):
            info = AccountDelegationInfo()
            info.address = MsgPackConverter.decode(TypeTag.ADDRESS, delegations[i])
            info.value = MsgPackConverter.decode(TypeTag.INT, delegations[i + 1])
            obj.delegations[info.address] = info
        return obj

    def to_bytes(self) -> bytes:
        """Convert Account of Stake object to bytes

        :return: data including information of AccountOfDelegation object
        """

        version = 0
        data = [MsgPackConverter.encode(version),
                MsgPackConverter.encode(self.delegated_amount)]
        delegations = []
        for info in self.delegations.values():
            delegations.append(MsgPackConverter.encode(info.address))
            delegations.append(MsgPackConverter.encode(info.value))
        data.append(delegations)

        return MsgPackConverter.dumps(data)

    def delegate(self, target: 'AccountOfDelegation', value: int) -> bool:
        delegation: 'AccountDelegationInfo' = self._delegations.get(target.address, None)

        if delegation is None:
            delegation: 'AccountDelegationInfo' = AccountOfDelegation.create_delegation(target.address, value)
            self._delegations[target.address] = delegation
            target._delegated_amount += value
            return True
        else:
            prev_delegation: int = delegation.value
            offset: int = value - prev_delegation

            if offset != 0:
                delegation.value += offset
                self._delegated_amount += offset

                if delegation.value == 0:
                    del self._delegations[target.address]
                return True
            else:
                return False

    @staticmethod
    def create_delegation(address: 'Address', value: int) -> 'AccountDelegationInfo':
        d = AccountDelegationInfo()
        d.address: 'Address' = address
        d.value: int = value
        return d

    def __eq__(self, other) -> bool:
        """operator == overriding

        :param other: (AccountOfDelegation)
        """

        return isinstance(other, AccountOfDelegation) \
               and self._address == other.address \
               and self._delegated_amount == other.delegated_amount \
               and self._delegations == other.delegations

    def __ne__(self, other) -> bool:
        """operator != overriding

        :param other: (AccountOfDelegation)
        """
        return not self.__eq__(other)


class AccountDelegationInfo(object):
    def __init__(self):
        self.address: 'Address' = None
        self.value: int = 0

    def __eq__(self, other) -> bool:
        """operator == overriding

        :param other: (AccountDelegationInfo)
        """
        return isinstance(other, AccountDelegationInfo) \
               and self.address == other.address \
               and self.value == other.value

    def __ne__(self, other) -> bool:
        """operator != overriding

        :param other: (AccountDelegationInfo)
        """
        return not self.__eq__(other)

    def to_dict(self):
        return {
            "address": self.address,
            "value": self.value
        }
