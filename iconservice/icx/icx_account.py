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

from typing import TYPE_CHECKING, Optional

from ..base.exception import InvalidParamsException, InvalidBalanceException
from ..icon_constant import Revision

if TYPE_CHECKING:
    from .coin_part import CoinPart
    from .delegation_part import DelegationPart
    from .stake_part import StakePart
    from ..base.address import Address
    from ..iconscore.icon_score_context import IconScoreContext


class Account(object):
    def __init__(self, address: 'Address', current_block_height: int, revision: int, *,
                 coin_part: Optional['CoinPart'] = None,
                 stake_part: Optional['StakePart'] = None,
                 delegation_part: Optional['DelegationPart'] = None):
        self._address: 'Address' = address
        self._current_block_height: int = current_block_height

        self._coin_part: 'CoinPart' = coin_part
        self._stake_part: 'StakePart' = stake_part
        self._delegation_part: 'DelegationPart' = delegation_part

        before_asset: int = self._get_asset()
        self.normalize(revision)
        after_asset: int = self._get_asset()

        self._verify_asset_integrity(revision, before_asset, after_asset)

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

    @property
    def balance(self) -> int:
        if self.coin_part:
            return self.coin_part.balance
        raise InvalidParamsException("Invalid intend: coin_part is None")

    @property
    def stake(self) -> int:
        if self.stake_part:
            return self.stake_part.stake
        raise InvalidParamsException("Invalid intend: stake_part is None")

    @property
    def voting_weight(self) -> int:
        if self.stake_part:
            return self.stake_part.voting_weight
        raise InvalidParamsException("Invalid intend: stake_part is None")

    @property
    def unstake(self) -> int:
        if self.stake_part:
            return self.stake_part.unstake
        raise InvalidParamsException("Invalid intend: stake_part is None")

    @property
    def total_stake(self) -> int:
        if self.stake_part:
            return self.stake_part.total_stake
        raise InvalidParamsException("Invalid intend: stake_part is None")

    @property
    def unstake_block_height(self) -> int:
        if self.stake_part:
            return self.stake_part.unstake_block_height
        raise InvalidParamsException("Invalid intend: start_part is None")

    @property
    def unstakes_info(self) -> Optional[list]:
        if self.stake_part:
            return self.stake_part.unstakes_info

    @property
    def delegated_amount(self) -> int:
        if self.delegation_part:
            return self.delegation_part.delegated_amount
        raise InvalidParamsException("Invalid intend: delegation_part is None")

    @property
    def delegations(self) -> Optional[list]:
        if self.delegation_part:
            return self.delegation_part.delegations
        raise InvalidParamsException("Invalid intend: delegation_part is None")

    @property
    def delegations_amount(self) -> int:
        if self.delegation_part:
            return self.delegation_part.delegations_amount
        raise InvalidParamsException("Invalid intend: delegation_part is None")

    @property
    def voting_power(self) -> int:
        if self.stake_part and self.delegation_part:
            return self.stake_part.voting_weight - self.delegation_part.delegations_amount
        raise InvalidParamsException("Invalid intend: stake_part or delegation_part is None")

    def deposit(self, value: int):
        if self.coin_part is None:
            raise InvalidParamsException('Failed to delegation: InvalidAccount')

        self.coin_part.deposit(value)

    def withdraw(self, value: int):
        if self.coin_part is None:
            raise InvalidParamsException('Failed to withdraw: InvalidAccount')

        self.coin_part.withdraw(value)

    def normalize(self, revision: int):
        if self.coin_part is None or self.stake_part is None:
            return

        expired_unstaked_balance: int = self.stake_part.normalize(self._current_block_height, revision)
        if expired_unstaked_balance > 0:
            if self.coin_part is None:
                raise InvalidParamsException('Failed to normalize: no coin part')

            self.coin_part.toggle_has_unstake(False, revision)

            self.coin_part.deposit(expired_unstaked_balance)

    def set_stake(self, context: "IconScoreContext", value: int, unstake_lock_period: int):
        if self.coin_part is None or self.stake_part is None:
            raise InvalidParamsException('Failed to stake: InvalidAccount')

        if not isinstance(value, int) or value < 0:
            raise InvalidParamsException('Failed to stake: value is not int type or value < 0')

        total: int = self.balance + self.total_stake

        if total < value:
            raise InvalidParamsException(f'Failed to stake: total{total} < stake{value}')

        offset: int = value - self.total_stake

        if offset == 0:
            self.stake_part.reset_unstake()
        elif offset > 0:
            self.coin_part.withdraw(offset)
            self.stake_part.add_stake(offset)
            self.stake_part.reset_unstake()
        else:
            unlock_block_height: int = self._current_block_height + unstake_lock_period
            self.coin_part.toggle_has_unstake(True, context.revision)
            if context.revision >= Revision.MULTIPLE_UNSTAKE.value:
                self.stake_part.set_unstakes_info(unlock_block_height,
                                                  -offset, context.unstake_slot_max)
            else:
                self.stake_part.set_unstake(unlock_block_height, -offset)

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

    def _get_asset(self) -> int:
        balance: int = self.coin_part.balance if self.coin_part else 0
        total_stake: int = self.stake_part.get_total_stake() if self.stake_part else 0

        return balance + total_stake

    def _verify_asset_integrity(self, revision: int, before_asset: int, after_asset: int):
        """Verify if the assets before normalization is the same as the assets after normalization

        asset means balance + total_stake(=stake + total_unstake)

        """
        if revision == Revision.MULTIPLE_UNSTAKE.value:
            # Skip to verify if revision is MULTIPLE_UNSTAKE
            # because asset integrity failure exists during Revision.MULTIPLE_UNSTAKE
            return

        if before_asset != after_asset:
            raise InvalidBalanceException(
                f"Invalid asset integrity: "
                f"address={self._address} "
                f"before_asset={before_asset} "
                f"after_asset={after_asset}"
            )
