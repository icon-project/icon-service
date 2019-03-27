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

from typing import TYPE_CHECKING, Optional

from ..utils import is_flag_on
from .icx_account import Account, AccountFlag
from .account.coin_account import CoinAccount
from .account.stake_account import StakeAccount
from .account.delegation_account import DelegationAccount

from ..base.block import Block
from ..icon_constant import DEFAULT_BYTE_SIZE, DATA_BYTE_ORDER

if TYPE_CHECKING:
    from ..database.db import ContextDatabase
    from ..iconscore.icon_score_context import IconScoreContext
    from ..base.address import Address
    from ..base.block import Block


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

    def get_account(self,
                    context: 'IconScoreContext',
                    address: 'Address',
                    flag: 'AccountFlag' = AccountFlag.COIN) -> 'Account':

        """Returns the account indicated by address.

        :param context:
        :param address: account address
        :param flag:
        :return: (Account)
            If the account indicated by address is not present,
            create a new account.
        """

        account = Account(address)
        if is_flag_on(flag, AccountFlag.COIN):
            key: bytes = CoinAccount.make_key(address)
            value: bytes = self._db.get(context, key)
            if value:
                coin_account = CoinAccount.from_bytes(value, address)
                account.coin_account: CoinAccount = coin_account
            else:
                account.coin_account: 'CoinAccount' = CoinAccount(address)

        if is_flag_on(flag, AccountFlag.STAKE):
            key: bytes = StakeAccount.make_key(address)
            value: bytes = self._db.get(context, key)
            if value:
                stake_account: 'StakeAccount' = StakeAccount.from_bytes(value, address)
                account.stake_account: StakeAccount = stake_account
            else:
                account.stake_account: 'StakeAccount' = StakeAccount(address)

        if is_flag_on(flag, AccountFlag.DELEGATION):
            key: bytes = DelegationAccount.make_key(address)
            value: bytes = self._db.get(context, key)
            if value:
                delegation_account: 'StakeAccount' = DelegationAccount.from_bytes(value, address)
                account.delegation_account: DelegationAccount = delegation_account
            else:
                account.delegation_account: 'DelegationAccount' = DelegationAccount(address)

        return account

    def put_account(self,
                    context: 'IconScoreContext',
                    account: 'Account') -> None:
        """Put account info to db.

        :param context:
        :param account: account to save
        """

        if account.is_flag_on(AccountFlag.COIN):
            key: bytes = CoinAccount.make_key(account.address)
            value: bytes = account.coin_account.to_bytes(context.revision)
            self._db.put(context, key, value)

        if account.is_flag_on(AccountFlag.STAKE):
            key: bytes = StakeAccount.make_key(account.address)
            value: bytes = account.stake_account.to_bytes()
            self._db.put(context, key, value)

        if account.is_flag_on(AccountFlag.DELEGATION):
            key: bytes = DelegationAccount.make_key(account.address)
            value: bytes = account.delegation_account.to_bytes()
            self._db.put(context, key, value)

    def delete_account(self,
                       context: 'IconScoreContext',
                       account: 'Account') -> None:
        """Delete account info from db.

        :param context:
        :param account: account to delete
        """

        if account.is_flag_on(AccountFlag.COIN):
            key: bytes = CoinAccount.make_key(account.address)
            self._db.delete(context, key)

        if account.is_flag_on(AccountFlag.STAKE):
            key: bytes = StakeAccount.make_key(account.address)
            self._db.delete(context, key)

        if account.is_flag_on(AccountFlag.DELEGATION):
            key: bytes = DelegationAccount.make_key(account.address)
            self._db.delete(context, key)

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
