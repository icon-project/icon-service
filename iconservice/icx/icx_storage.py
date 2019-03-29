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

from enum import IntEnum
from typing import TYPE_CHECKING, Optional

from ..base.exception import InvalidParamsException
from ..utils import is_flag_on
from .icx_account import Account, PartFlag
from .coin_part import CoinPart, CoinPartFlag
from .stake_part import StakePart
from .delegation_part import DelegationPart

from ..base.block import Block
from ..icon_constant import DEFAULT_BYTE_SIZE, DATA_BYTE_ORDER

if TYPE_CHECKING:
    from ..database.db import ContextDatabase
    from ..iconscore.icon_score_context import IconScoreContext
    from ..base.address import Address
    from ..base.block import Block


class AccountType(IntEnum):
    COIN = 0
    STAKE = 1
    DELEGATION = 2


class IcxStorage(object):
    _LAST_BLOCK_KEY = b'last_block'

    """Icx coin state manager embedding a state db wrapper
    """

    def __init__(self, db: 'ContextDatabase') -> None:
        """Constructor

        :param db: (Database) state db wrapper
        """
        self._db = db
        self._last_block = None

    @property
    def db(self) -> 'ContextDatabase':
        """Returns state db wrapper.

        :return: (Database) state db wrapper
        """
        return self._db

    @property
    def last_block(self) -> 'Block':
        return self._last_block

    def load_last_block_info(self, context: Optional['IconScoreContext']) -> None:
        block_bytes = self._db.get(context, self._LAST_BLOCK_KEY)
        if block_bytes is None:
            return

        self._last_block = Block.from_bytes(block_bytes)

    def put_block_info(self, context: 'IconScoreContext', block: 'Block') -> None:
        self._db.put(context, self._LAST_BLOCK_KEY, bytes(block))
        self._last_block = block

    def get_text(self, context: 'IconScoreContext', name: str) -> Optional[str]:
        """Return text format value from db

        :return: (str or None)
            text value mapped by name
            default encoding: utf8
        """
        key = name.encode()
        value = self._db.get(context, key)
        if value:
            return value.decode()
        else:
            return None

    def put_text(self,
                 context: 'IconScoreContext',
                 name: str,
                 text: str) -> None:
        """save text to db with name as a key
        All text are utf8 encoded.

        :param context:
        :param name: db key
        :param text: db value
        """
        key = name.encode()
        value = text.encode()
        self._db.put(context, key, value)

    @classmethod
    def _convert_account_type_to_part_flag(cls, flag: 'AccountType') -> 'PartFlag':
        if flag == AccountType.COIN:
            return PartFlag.COIN
        elif flag == AccountType.STAKE:
            return PartFlag.COIN_STAKE
        elif flag == AccountType.DELEGATION:
            return PartFlag.DELEGATION

    def get_account(self,
                    context: 'IconScoreContext',
                    address: 'Address',
                    account_type: 'AccountType' = AccountType.COIN) -> 'Account':

        """Returns the account indicated by address.

        :param context:
        :param address: account address
        :param account_type:
        :return: (Account)
            If the account indicated by address is not present,
            create a new account.
        """

        flag: 'PartFlag' = self._convert_account_type_to_part_flag(account_type)

        account: 'Account' = Account(address, context.block.height)
        is_stake_needed: bool = False
        if is_flag_on(flag, PartFlag.COIN):
            key: bytes = CoinPart.make_key(address)
            value: bytes = self._db.get(context, key)
            if value:
                coin_part: 'CoinPart' = CoinPart.from_bytes(value, address)
                is_stake_needed = coin_part.is_flag_on(CoinPartFlag.HAS_UNSTAKE)
                account.init_coin_part_in_icx_storage(coin_part)
            else:
                coin_part: 'CoinPart' = CoinPart(address)
                account.init_coin_part_in_icx_storage(coin_part)

        if is_flag_on(flag, PartFlag.STAKE) or is_stake_needed:
            key: bytes = StakePart.make_key(address)
            value: bytes = self._db.get(context, key)
            if value:
                stake_part: 'StakePart' = StakePart.from_bytes(value, address)
                account.init_stake_part_in_icx_storage(stake_part)
            else:
                stake_part: 'StakePart' = StakePart(address)
                account.init_stake_part_in_icx_storage(stake_part)

        if is_flag_on(flag, PartFlag.DELEGATION):
            key: bytes = DelegationPart.make_key(address)
            value: bytes = self._db.get(context, key)
            if value:
                delegation_part: 'DelegationPart' = DelegationPart.from_bytes(value, address)
                account.init_delegation_part_in_icx_storage(delegation_part)
            else:
                delegation_part: DelegationPart = DelegationPart(address)
                account.init_delegation_part_in_icx_storage(delegation_part)

        return account

    def put_account(self,
                    context: 'IconScoreContext',
                    account: 'Account',
                    account_type: 'AccountType' = AccountType.COIN) -> None:
        """Put account info to db.

        :param context:
        :param account: account to save
        :param account_type:
        """

        flag: 'PartFlag' = self._convert_account_type_to_part_flag(account_type)

        if is_flag_on(flag, PartFlag.COIN):
            if not account.is_flag_on(PartFlag.COIN):
                raise InvalidParamsException("mispatch account_type")

            key: bytes = CoinPart.make_key(account.address)
            value: bytes = account.coin_part.to_bytes(context.revision)
            self._db.put(context, key, value)

        if is_flag_on(flag, PartFlag.STAKE):
            if not account.is_flag_on(PartFlag.STAKE):
                raise InvalidParamsException("mispatch account_type")

            key: bytes = StakePart.make_key(account.address)
            value: bytes = account.stake_part.to_bytes()
            self._db.put(context, key, value)

        if is_flag_on(flag, PartFlag.DELEGATION):
            if not account.is_flag_on(PartFlag.DELEGATION):
                raise InvalidParamsException("mispatch account_type")

            key: bytes = DelegationPart.make_key(account.address)
            value: bytes = account.delegation_part.to_bytes()
            self._db.put(context, key, value)

    def delete_account(self,
                       context: 'IconScoreContext',
                       account: 'Account') -> None:
        """Delete account info from db.

        :param context:
        :param account: account to delete
        """
        raise Exception("not implemented")

    def get_total_supply(self, context: 'IconScoreContext') -> int:
        """Get the total supply

        :return: (int) coin total supply in loop (1 icx == 1e18 loop)
        """
        key = b'total_supply'
        value = self._db.get(context, key)

        amount = 0
        if value:
            amount = int.from_bytes(value, DATA_BYTE_ORDER)

        return amount

    def put_total_supply(self,
                         context: 'IconScoreContext',
                         value: int) -> None:
        """Save the total supply to db

        :param context:
        :param value: coin total supply
        """
        key = b'total_supply'
        value = value.to_bytes(DEFAULT_BYTE_SIZE, DATA_BYTE_ORDER)
        self._db.put(context, key, value)

    def close(self,
              context: 'IconScoreContext') -> None:
        """Close the embedded database.

        :param context:
        """
        if self._db:
            self._db.close(context)
            self._db = None
