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

from .icx_account import Account
from ..base.address import Address
from ..base.block import Block
from ..icon_constant import DEFAULT_BYTE_SIZE, DATA_BYTE_ORDER

if TYPE_CHECKING:
    from ..database.db import ContextDatabase
    from ..iconscore.icon_score_context import IconScoreContext


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
                    address: 'Address') -> 'Account':
        """Returns the account indicated by address.

        :param context:
        :param address: account address
        :return: (Account)
            If the account indicated by address is not present,
            create a new account.
        """
        key = address.to_bytes()
        value = self._db.get(context, key)

        if value:
            account = Account.from_bytes(value)
        else:
            account = Account()

        account.address = address
        return account

    def put_account(self,
                    context: 'IconScoreContext',
                    address: 'Address',
                    account: 'Account') -> None:
        """Puts account info to db.

        :param context:
        :param address: account address
        :param account: account to save
        """
        key = address.to_bytes()
        value = account.to_bytes()
        self._db.put(context, key, value)

    def delete_account(self,
                       context: 'IconScoreContext',
                       address: 'Address') -> None:
        """Deletes account info from db.

        :param context:
        :param address: account address
        """
        key = address.to_bytes()
        self._db.delete(context, key)

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
