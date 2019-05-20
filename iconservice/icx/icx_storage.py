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

from enum import IntEnum, IntFlag
from typing import TYPE_CHECKING, Optional, Union

from .coin_part import CoinPart, CoinPartFlag
from .delegation_part import DelegationPart
from .icx_account import Account
from .stake_part import StakePart
from ..base.block import Block
from ..icon_constant import DEFAULT_BYTE_SIZE, DATA_BYTE_ORDER

if TYPE_CHECKING:
    from ..database.db import ContextDatabase
    from ..iconscore.icon_score_context import IconScoreContext
    from ..base.address import Address
    from ..base.block import Block


class AccountPartFlag(IntFlag):
    """PartFlag Type
    """
    NONE = 0
    COIN = 1
    STAKE = 2
    DELEGATION = 4


class Intent(IntEnum):
    TRANSFER = AccountPartFlag.COIN
    STAKE = AccountPartFlag.COIN | AccountPartFlag.STAKE
    DELEGATED = AccountPartFlag.DELEGATION
    DELEGATING = AccountPartFlag.COIN | AccountPartFlag.STAKE | AccountPartFlag.DELEGATION


class IcxStorage(object):
    """Icx coin state manager embedding a state db wrapper"""

    # Level db keys
    _LAST_BLOCK_KEY = b'last_block'
    _TOTAL_SUPPLY_KEY = b'total_supply'

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
        """Returns text format value from db

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
        """Saves text to db with name as a key
        All text are utf8 encoded.

        :param context:
        :param name: db key
        :param text: db value
        """
        key = name.encode()
        value = text.encode()
        self._db.put(context, key, value)

    def get_account(self,
                    context: 'IconScoreContext',
                    address: 'Address',
                    intent: 'Intent' = Intent.TRANSFER) -> 'Account':

        """Returns the account indicated by address.

        :param context:
        :param address: account address
        :param intent:
        :return: (Account)
            If the account indicated by address is not present,
            create a new account.
        """

        coin_part: Optional['CoinPart'] = None
        stake_part: Optional['StakePart'] = None
        delegation_part: Optional['DelegationPart'] = None

        part_flags: 'AccountPartFlag' = AccountPartFlag(intent)

        if AccountPartFlag.COIN in part_flags:
            coin_part: 'CoinPart' = self._get_part(context, CoinPart, address)

            if CoinPartFlag.HAS_UNSTAKE in coin_part.flags:
                part_flags |= AccountPartFlag.STAKE

        if AccountPartFlag.STAKE in part_flags:
            stake_part: 'StakePart' = self._get_part(context, StakePart, address)

        if AccountPartFlag.DELEGATION in part_flags:
            delegation_part: 'DelegationPart' = self._get_part(context, DelegationPart, address)

        return Account(address, context.block.height,
                       coin_part=coin_part,
                       stake_part=stake_part,
                       delegation_part=delegation_part)

    def _get_part(self, context: 'IconScoreContext',
                  part_class: Union[type(CoinPart), type(StakePart), type(DelegationPart)],
                  address: 'Address') -> Union['CoinPart', 'StakePart', 'DelegationPart']:
        key: bytes = part_class.make_key(address)
        value: bytes = self._db.get(context, key)

        return part_class.from_bytes(value) if value else part_class()

    def put_account(self,
                    context: 'IconScoreContext',
                    account: 'Account') -> None:

        """Put account into to db.

        :param context:
        :param account: account to save
        """
        parts = [account.coin_part, account.stake_part, account.delegation_part]

        for part in parts:
            if part and part.is_dirty():
                key: bytes = part.make_key(account.address)

                if isinstance(part, CoinPart):
                    value: bytes = part.to_bytes(context.revision)
                else:
                    value: bytes = part.to_bytes()

                self._db.put(context, key, value)

    def delete_account(self,
                       context: 'IconScoreContext',
                       account: 'Account') -> None:
        """Delete account info from db.

        :param context:
        :param account: account to delete
        """
        raise Exception("not implemented")

    def is_address_present(self,
                           context: 'IconScoreContext',
                           address: 'Address') -> bool:
        """Checks whether value indicated by address is present or not.

        :param context:
        :param address: account address
        :return: True(present) False(not present)
        """
        key = address.to_bytes()
        value = self._db.get(context, key)

        return bool(value)

    # This method being called only when open period
    def get_total_supply(self, context: 'IconScoreContext') -> int:
        """Returns the total supply.

        :return: (int) coin total supply in loop (1 icx == 1e18 loop)
        """

        value = self._db.get(context, self._TOTAL_SUPPLY_KEY)

        amount = 0
        if value:
            amount = int.from_bytes(value, DATA_BYTE_ORDER)

        return amount

    def put_total_supply(self,
                         context: 'IconScoreContext',
                         value: int) -> None:
        """Saves the total supply to db.

        :param context:
        :param value: coin total supply
        """
        value = value.to_bytes(DEFAULT_BYTE_SIZE, DATA_BYTE_ORDER)
        self._db.put(context, self._TOTAL_SUPPLY_KEY, value)

    def close(self,
              context: 'IconScoreContext') -> None:
        """Close the embedded database.

        :param context:
        """
        if self._db:
            self._db.close(context)
            self._db = None
