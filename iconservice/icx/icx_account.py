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
from typing import TYPE_CHECKING, Optional, Any

from ..base.exception import InvalidParamsException
from .coin_part import CoinPartFlag

if TYPE_CHECKING:
    from .coin_part import CoinPart
    from .stake_part import StakePart
    from .delegation_part import DelegationPart
    from ..base.address import Address
    from collections import OrderedDict


class PartFlag(IntFlag):
    """PartFlag Type
    """
    NONE = 0
    COIN = 1
    STAKE = 2
    COIN_STAKE = COIN | STAKE
    DELEGATION = 4


class Account(object):
    def __init__(self, address: 'Address', current_block_height: int):
        self._address: 'Address' = address
        self._current_block_height: int = current_block_height
        self._flag: 'PartFlag' = PartFlag.NONE

        self._coin_part: 'CoinPart' = None
        self._stake_part: 'StakePart' = None
        self._delegation_part: 'DelegationPart' = None

    @property
    def flag(self) -> 'PartFlag':
        return self._flag

    @property
    def address(self):
        return self._address

    @property
    def coin_part(self) -> 'CoinPart':
        return self._coin_part

    @property
    def stake_part(self) -> 'StakePart':
        return self._stake_part

    @property
    def delegation_part(self) -> 'DelegationPart':
        return self._delegation_part

    def init_coin_part_in_icx_storage(self, coin_part: Optional['CoinPart']):
        self._setter_flag_set(coin_part, PartFlag.COIN)
        self._coin_part = coin_part

    def init_stake_part_in_icx_storage(self, stake_part: Optional['StakePart']):
        self._setter_flag_set(stake_part, PartFlag.STAKE)
        self._stake_part = stake_part

    def init_delegation_part_in_icx_storage(self, delegation_part: Optional['DelegationPart']):
        self._setter_flag_set(delegation_part, PartFlag.DELEGATION)
        self._delegation_part = delegation_part

    def _setter_flag_set(self, dest: Any, flag: 'PartFlag'):
        if dest is None and self.is_flag_on(flag):
            self._flag &= ~flag
        elif not self.is_flag_on(flag):
            self._flag |= flag

    def is_flag_on(self, flag: int) -> bool:
        return self.flag & flag == flag

    def deposit(self, value: int):
        if not self.is_flag_on(PartFlag.COIN):
            raise InvalidParamsException('Failed to delegation: InvalidAccount')

        self.coin_part.deposit(value)

    def withdraw(self, value: int):
        if not self.is_flag_on(PartFlag.COIN):
            raise InvalidParamsException('Failed to delegation: InvalidAccount')

        self.coin_part.withdraw(value)

    def update(self):
        if not self.is_flag_on(PartFlag.COIN_STAKE):
            return

        balance: int = self.stake_part.update(self._current_block_height)
        if balance > 0:
            self.coin_part.toggle_flag(CoinPartFlag.HAS_UNSTAKE, False)
            self.coin_part.deposit(balance)

    @property
    def balance(self) -> int:
        balance = 0

        if self.is_flag_on(PartFlag.COIN):
            balance = self.coin_part.balance

        if self.is_flag_on(PartFlag.STAKE):
            if self._current_block_height > self.stake_part.unstake_block_height:
                balance += self.stake_part.unstake
        return balance

    @property
    def stake(self) -> int:
        if self.is_flag_on(PartFlag.STAKE):
            return self.stake_part.stake
        return 0

    @property
    def unstake(self) -> int:
        if self.is_flag_on(PartFlag.STAKE):
            return self.stake_part.unstake
        return 0

    @property
    def unstake_block_height(self) -> int:
        if self.is_flag_on(PartFlag.STAKE):
            return self.stake_part.unstake_block_height
        return 0

    @property
    def delegated_amount(self) -> int:
        if self.is_flag_on(PartFlag.STAKE):
            return self.delegation_part.delegated_amount
        return 0

    @property
    def delegations(self) -> Optional[list]:
        if self.is_flag_on(PartFlag.STAKE):
            return self.delegation_part.delegations
        return None

    def set_stake(self, value: int, unstake_lock_period: int) -> None:
        if not self.is_flag_on(PartFlag.COIN | PartFlag.STAKE):
            raise InvalidParamsException('Failed to stake: InvalidAccount')

        if not isinstance(value, int) or value < 0:
            raise InvalidParamsException('Failed to stake: value is not int type or value < 0')

        total: int = self.balance + self.stake

        if total < value:
            raise InvalidParamsException('Failed to stake: total < stake')

        offset: int = value - self.stake

        if offset == 0:
            return
        elif offset > 0:
            self.coin_part.withdraw(value)
            self.stake_part.add_stake(abs(offset))
        else:
            unlock_block_height: int = self._current_block_height + unstake_lock_period
            self.coin_part.toggle_flag(CoinPartFlag.HAS_UNSTAKE, True)
            self.stake_part.set_unstake(unlock_block_height, abs(offset))

    def update_delegated_amount(self, offset: int):
        if not self.is_flag_on(PartFlag.DELEGATION):
            raise InvalidParamsException('Failed to delegation: InvalidAccount')

        self.delegation_part.update_delegated_amount(offset)

    def set_delegations(self, new_delegations: list):
        if not self.is_flag_on(PartFlag.DELEGATION):
            raise InvalidParamsException('Failed to delegation: InvalidAccount')
        
        self.delegation_part.set_delegations(new_delegations)

    def __eq__(self, other) -> bool:
        """operator == overriding

        :param other: (CoinPart)
        """
        return isinstance(other, Account) \
               and self.address == other.address \
               and self._flag == other.flag \
               and self._coin_part == other.coin_part \
               and self.stake_part == other.stake_part \
               and self.delegation_part == other.delegation_part

    def __ne__(self, other) -> bool:
        """operator != overriding

        :param other: (CoinPart)
        """
        return not self.__eq__(other)
