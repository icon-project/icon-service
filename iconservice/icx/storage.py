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

import json
from enum import IntEnum, IntFlag
from typing import TYPE_CHECKING, Optional, Union

from iconcommons import Logger
from .coin_part import CoinPart, CoinPartFlag, CoinPartType
from .delegation_part import DelegationPart
from .icx_account import Account
from .stake_part import StakePart
from ..base.ComponentBase import StorageBase
from ..base.address import Address
from ..base.block import Block
from ..icon_constant import DEFAULT_BYTE_SIZE, DATA_BYTE_ORDER, ICX_LOG_TAG

if TYPE_CHECKING:
    from ..database.db import ContextDatabase
    from ..iconscore.icon_score_context import IconScoreContext


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
    INIT_PREP = AccountPartFlag.STAKE | AccountPartFlag.DELEGATION
    ALL = AccountPartFlag.COIN | AccountPartFlag.STAKE | AccountPartFlag.DELEGATION


class Storage(StorageBase):
    """Icx coin state manager embedding a state db wrapper"""

    _GENESIS_DB_KEY = 'genesis'
    _TREASURY_DB_KEY = 'fee_treasury'

    # Level db keys
    _LAST_BLOCK_KEY = b'last_block'
    _TOTAL_SUPPLY_KEY = b'total_supply'

    def __init__(self, db: 'ContextDatabase'):
        """Constructor

        :param db: (Database) state db wrapper
        """
        super().__init__(db)
        self._db = db
        self._last_block = None
        self._genesis: 'Address' = None
        self._fee_treasury: 'Address' = None

    def open(self, context: 'IconScoreContext'):
        self._load_special_address(context, self._GENESIS_DB_KEY)
        self._load_special_address(context, self._TREASURY_DB_KEY)

    @property
    def last_block(self) -> 'Block':
        return self._last_block

    @property
    def genesis(self) -> 'Address':
        return self._genesis

    @property
    def fee_treasury(self) -> 'Address':
        return self._fee_treasury

    def load_last_block_info(self, context: 'IconScoreContext'):
        block_bytes = self._db.get(context, self._LAST_BLOCK_KEY)
        if block_bytes is None:
            return

        self._last_block = Block.from_bytes(block_bytes)

    def _load_special_address(self,
                              context: 'IconScoreContext',
                              db_key: str):
        """Load address info from state db according to db_key

        :param context:
        :param db_key: db key info
        """
        Logger.debug(f'_load_address_from_storage() start(address type: {db_key})', ICX_LOG_TAG)
        text = context.storage.icx.get_text(context, db_key)
        if text:
            obj = json.loads(text)

            # Support to load MainNet 1.0 db
            address: str = obj['address']
            if len(address) == 40:
                address = f'hx{address}'

            address: Address = Address.from_string(address)
            if db_key == self._GENESIS_DB_KEY:
                self._genesis: 'Address' = address
            elif db_key == self._TREASURY_DB_KEY:
                self._fee_treasury: 'Address' = address
            Logger.info(f'{db_key}: {address}', ICX_LOG_TAG)
        Logger.debug(f'_load_address_from_storage() end(address type: {db_key})', ICX_LOG_TAG)

    def put_block_info(self, context: 'IconScoreContext', block: 'Block', revision: int):
        self._db.put(context, self._LAST_BLOCK_KEY, block.to_bytes(revision))
        self._last_block = block

    def put_genesis_accounts(self, context: 'IconScoreContext', accounts: list):
        genesis = accounts[0]
        treasury = accounts[1]
        others = accounts[2:]

        __ADDRESS_KEY = 'address'
        __AMOUNT_KEY = 'balance'

        self._put_genesis_data_account(
            context=context,
            coin_part_type=CoinPartType.GENESIS,
            address=genesis[__ADDRESS_KEY],
            amount=genesis[__AMOUNT_KEY])

        self._put_genesis_data_account(
            context=context,
            coin_part_type=CoinPartType.TREASURY,
            address=treasury[__ADDRESS_KEY],
            amount=treasury[__AMOUNT_KEY])

        for other in others:
            self._put_genesis_data_account(
                context=context,
                coin_part_type=CoinPartType.GENERAL,
                address=other[__ADDRESS_KEY],
                amount=other[__AMOUNT_KEY])

    def _put_genesis_data_account(self,
                                  context: 'IconScoreContext',
                                  coin_part_type: 'CoinPartType',
                                  address: 'Address',
                                  amount: int):
        """This method is called only on invoking the genesis block

        :param context:
        :param coin_part_type:
        :param address:
        :param amount:
        :return:
        """

        coin_part: 'CoinPart' = CoinPart(coin_part_type)
        account: 'Account' = Account(address, context.block.height, coin_part=coin_part)
        account.deposit(int(amount))
        if not account.coin_part.is_dirty():
            account.coin_part.set_dirty(True)
        self.put_account(context, account)

        if account.balance > 0:
            total_supply = self.get_total_supply(context)
            total_supply += account.balance
            context.storage.icx.put_total_supply(context, total_supply)
        if coin_part_type in [CoinPartType.GENESIS, CoinPartType.TREASURY]:
            self._put_special_account(context, account)

    def _put_special_account(self,
                             context: 'IconScoreContext',
                             account: 'Account'):
        """Compared to other general accounts,
        additional tasks should be processed
        for special accounts (genesis, treasury)

        :param context:
        :param account: genesis or treasury accounts
        """

        assert account.coin_part is not None
        assert account.coin_part.type in (CoinPartType.GENESIS, CoinPartType.TREASURY)

        if account.coin_part.type == CoinPartType.GENESIS:
            db_key = self._GENESIS_DB_KEY
            self._genesis = account.address
        else:
            db_key = self._TREASURY_DB_KEY
            self._fee_treasury = account.address

        obj = {'version': 0, 'address': str(account.address)}
        text = json.dumps(obj)

        context.storage.icx.put_text(context, db_key, text)

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
                 text: str):
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
                    account: 'Account'):

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
                       account: 'Account'):
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
                         value: int):
        """Saves the total supply to db.

        :param context:
        :param value: coin total supply
        """
        value = value.to_bytes(DEFAULT_BYTE_SIZE, DATA_BYTE_ORDER)
        self._db.put(context, self._TOTAL_SUPPLY_KEY, value)
