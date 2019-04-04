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

from enum import IntFlag, unique
from typing import TYPE_CHECKING, Optional

from ..utils import toggle_flags
from ..base.exception import InvalidParamsException

if TYPE_CHECKING:
    from .coin_part import CoinPart
    from .stake_part import StakePart
    from .delegation_part import DelegationPart
    from ..base.address import Address


@unique
class PartFlag(IntFlag):
    """PartFlag bitwise flags
    """
    NONE = 0
    COIN_DIRTY = 1
    STAKE_DIRTY = 2
    DELEGATION_DIRTY = 4

    COIN_HAS_UNSTAKE = 8
    STAKE_COMPLETE = 16


class Account(object):
    def __init__(self, address: 'Address', current_block_height: int):
        self._address: 'Address' = address
        self._current_block_height: int = current_block_height

        self._coin_part: 'CoinPart' = None
        self._stake_part: 'StakePart' = None
        self._delegation_part: 'DelegationPart' = None

    @property
    def flags(self) -> int:
        flags = PartFlag.NONE
        if self.coin_part:
            flags |= self.coin_part.flags
        if self.stake_part:
            flags |= self.stake_part.flags
        if self.delegation_part:
            flags |= self.delegation_part.flags
        return flags

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
        self._coin_part = coin_part

    def init_stake_part_in_icx_storage(self, stake_part: Optional['StakePart']):
        self._stake_part = stake_part

    def init_delegation_part_in_icx_storage(self, delegation_part: Optional['DelegationPart']):
        self._delegation_part = delegation_part

    @property
    def balance(self) -> int:
        balance = 0

        if self.coin_part:
            balance = self.coin_part.balance
        return balance

    @property
    def stake(self) -> int:
        if self.stake_part:
            return self.stake_part.stake
        return 0

    @property
    def unstake(self) -> int:
        if self.stake_part:
            return self.stake_part.unstake
        return 0

    @property
    def total_stake(self) -> int:
        if self.stake_part:
            return self.stake_part.total_stake
        return 0

    @property
    def unstake_block_height(self) -> int:
        if self.stake_part:
            return self.stake_part.unstake_block_height
        return 0

    @property
    def delegated_amount(self) -> int:
        if self.delegation_part:
            return self.delegation_part.delegated_amount
        return 0

    @property
    def delegations(self) -> Optional[list]:
        if self.delegation_part:
            return self.delegation_part.delegations
        return None

    @property
    def delegations_amount(self) -> int:
        if self.delegation_part:
            return self.delegation_part.delegations_amount
        return 0

    def deposit(self, value: int):
        if self.coin_part is None:
            raise InvalidParamsException('Failed to delegation: InvalidAccount')

        self.coin_part.deposit(value)

    def withdraw(self, value: int):
        if self.coin_part is None:
            raise InvalidParamsException('Failed to delegation: InvalidAccount')

        self.coin_part.withdraw(value)

    def update(self):
        if self.stake_part is None:
            return

        balance: int = self.stake_part.update(self._current_block_height)
        if balance > 0:
            self.coin_part.toggle_has_unstake(False)
            self.coin_part.deposit(balance)

    def set_stake(self, value: int, unstake_lock_period: int):
        if self.coin_part is None or self.stake_part is None:
            raise InvalidParamsException('Failed to stake: InvalidAccount')

        if not isinstance(value, int) or value < 0:
            raise InvalidParamsException('Failed to stake: value is not int type or value < 0')

        total: int = self.balance + self.total_stake

        if total < value:
            raise InvalidParamsException('Failed to stake: total < stake')

        offset: int = value - self.total_stake

        if offset == 0:
            return
        elif offset > 0:
            self.coin_part.withdraw(offset)
            self.stake_part.add_stake(offset)
        else:
            unlock_block_height: int = self._current_block_height + unstake_lock_period
            self.coin_part.toggle_has_unstake(True)
            self.stake_part.set_unstake(unlock_block_height,  self.total_stake - value)

    def update_delegated_amount(self, offset: int):
        if self.delegation_part is None:
            raise InvalidParamsException('Failed to delegation: InvalidAccount')

        self.delegation_part.update_delegated_amount(offset)

    def set_delegations(self, new_delegations: list):
        if self.delegation_part is None:
            raise InvalidParamsException('Failed to delegation: InvalidAccount')
        
        self.delegation_part.set_delegations(new_delegations)

    def __eq__(self, other) -> bool:
        """operator == overriding

        :param other: (CoinPart)
        """
        return isinstance(other, Account) \
            and self._address == other.address \
            and self._coin_part == other.coin_part \
            and self._stake_part == other.stake_part \
            and self._delegation_part == other.delegation_part

    def __ne__(self, other) -> bool:
        """operator != overriding

        :param other: (CoinPart)
        """
        return not self.__eq__(other)
