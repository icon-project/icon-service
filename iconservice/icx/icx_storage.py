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
from struct import Struct

from .icx_account import Account
from ..base.address import Address
from ..base.block import Block
from ..icon_constant import DEFAULT_BYTE_SIZE, DATA_BYTE_ORDER
from ..fee.deposit import Deposit

if TYPE_CHECKING:
    from ..database.db import ContextDatabase
    from ..iconscore.icon_score_context import IconScoreContext


class Fee(object):
    """SCORE Fee Information"""

    # Fee Structure for level db (big endian, 14 bytes)
    # ratio(2) | head_id(4) | tail_id(4) | available_head_id(4)
    # icx(DEFAULT_BYTE_SIZE)
    _struct = Struct(f'>BBBx{DEFAULT_BYTE_SIZE}s')

    def __init__(self, ratio: int = 0, head_id: bytes = None, tail_id: bytes = None, available_head_id: bytes = None):
        self.ratio = ratio
        self.head_id = head_id
        self.tail_id = tail_id
        self.available_head_id = available_head_id

    @staticmethod
    def from_bytes(buf: bytes):
        """Converts Fee in bytes into Fee Object

        :param buf: Fee in bytes
        :return: Fee Object
        """
        return Fee

    def to_bytes(self) -> bytes:
        """Converts Fee object into bytes

        :return: Fee in bytes
        """
        return Fee._struct.pack()


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
        """Put account info to db.

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
        """Delete account info from db.

        :param context:
        :param address: account address
        """
        key = address.to_bytes()
        self._db.delete(context, key)

    def is_address_present(self,
                           context: 'IconScoreContext',
                           address: 'Address') -> bool:
        """Check whether value indicated by address is present or not.

        :param context:
        :param address: account address
        :return: True(present) False(not present)
        """
        key = address.to_bytes()
        value = self._db.get(context, key)

        return bool(value)

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

    def get_score_fee(self, context: 'IconScoreContext', score_address: 'Address') -> Fee:
        """Returns the contract fee

        :param context: Object that contains the useful information to process user's JSON-RPC request
        :param score_address: SCORE address
        :return: Fee object
        """
        pass

    def put_score_fee(self, context: 'IconScoreContext', score_address: 'Address', fee: Fee) -> None:
        """Puts the contract fee data into db

        :param context: Object that contains the useful information to process user's JSON-RPC request
        :param score_address: SCORE address
        :param fee: Fee object
        :return: None
        """
        pass

    def delete_score_fee(self, context: 'IconScoreContext', score_address: 'Address') -> None:
        """Deletes the contract fee from db

        :param context: Object that contains the useful information to process user's JSON-RPC request
        :param score_address: SCORE address
        :return: None
        """
        pass

    # TODO : unpack 하고 deposit_id 주입해서 return
    def get_deposit(self, context: 'IconScoreContext', deposit_id: bytes) -> Deposit:
        """Returns the deposit

        :param context: Object that contains the useful information to process user's JSON-RPC request
        :param deposit_id: Deposit id
        :return: Deposit Object
        """
        pass

    def put_deposit(self, context: 'IconScoreContext', deposit_id: bytes, deposit: Deposit) -> None:
        """Puts the deposit data into db

        :param context: Object that contains the useful information to process user's JSON-RPC request
        :param deposit_id: Deposit id
        :param deposit: Deposit Object
        :return: None
        """
        pass

    def delete_deposit(self, context: 'IconScoreContext', deposit_id: bytes) -> None:
        """Deletes the deposit from db

        :param context: Object that contains the useful information to process user's JSON-RPC request
        :param deposit_id: Deposit id
        :return: None
        """
        pass

    def close(self,
              context: 'IconScoreContext') -> None:
        """Close the embedded database.

        :param context:
        """
        if self._db:
            self._db.close(context)
            self._db = None
