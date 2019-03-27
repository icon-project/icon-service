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

from enum import IntFlag
from typing import TYPE_CHECKING, Optional

from ..base.exception import InvalidParamsException

if TYPE_CHECKING:
    from .account.coin_account import CoinAccount
    from .account.stake_account import StakeAccount
    from .account.delegation_account import DelegationAccount
    from ..base.address import Address
    from collections import OrderedDict


class AccountFlag(IntFlag):
    """Account Type
    """
    NONE = 0x0
    COIN = 0x1
    STAKE = 0x2
    DELEGATION = 0x4


class Account(object):
    def __init__(self, address: 'Address'):
        self._address: 'Address' = address
        self._flag: 'AccountFlag' = AccountFlag.NONE

        self._coin_account: 'CoinAccount' = None
        self._stake_account: 'StakeAccount' = None
        self._delegation_account: 'DelegationAccount' = None

    @property
    def flag(self) -> 'AccountFlag':
        return self._flag

    @property
    def address(self):
        return self._address

    @property
    def coin_account(self) -> 'CoinAccount':
        return self._coin_account

    @coin_account.setter
    def coin_account(self, coin_account: 'CoinAccount'):
        if coin_account is None and self.is_flag_on(AccountFlag.COIN):
            self._flag &= ~AccountFlag.COIN
        elif not self.is_flag_on(AccountFlag.COIN):
            self._flag |= AccountFlag.COIN

        self._coin_account = coin_account

    @property
    def stake_account(self) -> 'StakeAccount':
        return self._stake_account

    @stake_account.setter
    def stake_account(self, stake_account: 'StakeAccount'):
        if stake_account is None and self.is_flag_on(AccountFlag.STAKE):
            self._flag &= ~AccountFlag.STAKE
        elif not self.is_flag_on(AccountFlag.STAKE):
            self._flag |= AccountFlag.STAKE

        self._stake_account = stake_account

    @property
    def delegation_account(self) -> 'DelegationAccount':
        return self._delegation_account

    @delegation_account.setter
    def delegation_account(self, delegation_account: 'DelegationAccount'):
        if delegation_account is None and self.is_flag_on(AccountFlag.DELEGATION):
            self._flag &= ~AccountFlag.DELEGATION
        elif not self.is_flag_on(AccountFlag.DELEGATION):
            self._flag |= AccountFlag.DELEGATION

        self._delegation_account = delegation_account

    def is_flag_on(self, flag: int) -> bool:
        return self.flag & flag == flag

    def deposit(self, value: int) -> None:
        if not self.is_flag_on(AccountFlag.COIN):
            raise InvalidParamsException('Failed to delegation: InvalidAccount')

        self.coin_account.deposit(value)

    def withdraw(self, value: int) -> None:
        if not self.is_flag_on(AccountFlag.COIN):
            raise InvalidParamsException('Failed to delegation: InvalidAccount')

        self.coin_account.withdraw(value)

    def get_balance(self, current_block_height: int) -> int:
        balance = 0

        if self.is_flag_on(AccountFlag.COIN):
            balance = self.coin_account.balance

        if self.is_flag_on(AccountFlag.STAKE):
            if current_block_height > self.stake_account.unstake_block_height:
                balance += self.stake_account.unstake_amount
        return balance

    def get_stake_amount(self) -> int:
        if not self.is_flag_on(AccountFlag.STAKE):
            return 0
        return self.stake_account.stake_amount

    def get_unstake_amount(self) -> int:
        if not self.is_flag_on(AccountFlag.STAKE):
            return 0
        return self.stake_account.unstake_amount

    def get_unstake_block_height(self) -> int:
        if not self.is_flag_on(AccountFlag.STAKE):
            return 0
        return self.stake_account.unstake_block_height

    def get_delegated_amount(self) -> int:
        if not self.is_flag_on(AccountFlag.STAKE):
            return 0
        return self.delegation_account.delegated_amount

    def get_delegations(self) -> Optional['OrderedDict']:
        if not self.is_flag_on(AccountFlag.STAKE):
            return None
        return self.delegation_account.delegations

    def stake(self, value: int) -> None:
        if not self.is_flag_on(AccountFlag.COIN | AccountFlag.STAKE):
            raise InvalidParamsException('Failed to stake: InvalidAccount')

        if not isinstance(value, int) or value < 0:
            raise InvalidParamsException('Failed to stake: value is not int type or value < 0')

        self.coin_account.withdraw(value)
        self.stake_account.stake(value)

    def unstake(self, next_block_height: int, value: int) -> None:
        if not self.is_flag_on(AccountFlag.STAKE):
            raise InvalidParamsException('Failed to stake: InvalidAccount')

        if not isinstance(value, int) or value < 0:
            raise InvalidParamsException('Failed to unstake: value is not int type or value < 0')

        self.stake_account.unstake(next_block_height, value)

    def delegate(self, target: 'Account', value: int) -> bool:
        if not self.is_flag_on(AccountFlag.DELEGATION) or not target.is_flag_on(AccountFlag.DELEGATION):
            raise InvalidParamsException('Failed to delegation: InvalidAccount')

        return self.delegation_account.update_delegations(target.delegation_account, value)

    def trim_deletions(self):
        if not self.is_flag_on(AccountFlag.DELEGATION):
            return

        self.delegation_account.trim_deletions()

    def __eq__(self, other) -> bool:
        """operator == overriding

        :param other: (CoinAccount)
        """
        return isinstance(other, Account) \
               and self.address == other.address \
               and self._flag == other.flag \
               and self._coin_account == other.coin_account \
               and self.stake_account == other.stake_account \
               and self.delegation_account == other.delegation_account

    def __ne__(self, other) -> bool:
        """operator != overriding

        :param other: (CoinAccount)
        """
        return not self.__eq__(other)
