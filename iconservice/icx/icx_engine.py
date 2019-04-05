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
from typing import TYPE_CHECKING, Optional

from iconcommons.logger import Logger
from .icx_account import Account, AccountType
from .icx_storage import IcxStorage
from ..base.address import Address
from ..base.exception import InvalidParamsException
from ..icon_constant import ICX_LOG_TAG

if TYPE_CHECKING:
    from ..iconscore.icon_score_context import IconScoreContext


class IcxEngine(object):
    _GENESIS_DB_KEY = 'genesis'
    _TREASURY_DB_KEY = 'fee_treasury'

    """Manages the balances of icon accounts

    The basic unit of icx coin is loop. (1 icx == 1e18 loop)
    _context property is inherited from ContextGetter
    """

    def __init__(self) -> None:
        """Constructor
        """
        self._storage: IcxStorage = None
        self._total_supply_amount: int = 0
        self._genesis_address: Address = None
        self._fee_treasury_address: Address = None

    def open(self, storage: 'IcxStorage') -> None:
        """Open engine

        Get necessary parameters from caller and begin to use storage (leveldb)

        :param storage: IcxStorage object to access state db
        """
        self.close()

        self._storage = storage

        context = None
        self._storage.load_last_block_info(context)
        self._load_address_from_storage(context, storage, self._GENESIS_DB_KEY)
        self._load_address_from_storage(context, storage, self._TREASURY_DB_KEY)
        self._load_total_supply_amount_from_storage(context, storage)

    @property
    def storage(self) -> 'IcxStorage':
        return self._storage

    def close(self) -> None:
        """Close resources
        """
        if self._storage:
            self._storage.close(context=None)
            self._storage = None

    def init_account(self,
                     context: 'IconScoreContext',
                     account_type: 'AccountType',
                     account_name: str,
                     address: 'Address',
                     amount: int) -> None:
        """This method is called only on invoking the genesis block

        :param context:
        :param account_type:
        :param account_name:
        :param address:
        :param amount:
        :return:
        """

        account = Account(
            account_type=account_type, address=address, icx=int(amount))

        self._storage.put_account(context, account.address, account)

        if account.icx > 0:
            self._total_supply_amount += account.icx
            self._storage.put_total_supply(context, self._total_supply_amount)

        if account_type == AccountType.GENESIS or \
                account_type == AccountType.TREASURY:
            self._init_special_account(context, account)

    def _init_special_account(self,
                              context: 'IconScoreContext',
                              account: 'Account') -> None:
        """Compared to other general accounts,
        additional tasks should be processed
        for special accounts (genesis, treasury)

        :param context:
        :param account: genesis or treasury accounts
        """
        assert account.type in (AccountType.GENESIS, AccountType.TREASURY)

        if account.type == AccountType.GENESIS:
            db_key = self._GENESIS_DB_KEY
            self._genesis_address = account.address
        else:
            db_key = self._TREASURY_DB_KEY
            self._fee_treasury_address = account.address

        obj = {'version': 0, 'address': str(account.address)}
        text = json.dumps(obj)

        self._storage.put_text(context, db_key, text)

    def _load_address_from_storage(self,
                                   context: Optional['IconScoreContext'],
                                   storage: IcxStorage,
                                   db_key: str) -> None:
        """Load address info from state db according to db_key

        :param context:
        :param storage: state db manager
        :param db_key: db key info
        """
        Logger.debug(f'_load_address_from_storage() start(address type: {db_key})', ICX_LOG_TAG)
        text = storage.get_text(context, db_key)
        if text:
            obj = json.loads(text)

            # Support to load MainNet 1.0 db
            address: str = obj['address']
            if len(address) == 40:
                address = f'hx{address}'

            address: Address = Address.from_string(address)
            if db_key == self._GENESIS_DB_KEY:
                self._genesis_address = address
            elif db_key == self._TREASURY_DB_KEY:
                self._fee_treasury_address = address
            Logger.info(f'{db_key}: {address}', ICX_LOG_TAG)
        Logger.debug(f'_load_address_from_storage() end(address type: {db_key})', ICX_LOG_TAG)

    def _load_total_supply_amount_from_storage(
            self,
            context: Optional['IconScoreContext'],
            storage: IcxStorage) -> None:
        """Load total coin supply amount from state db

        :param context:
        :param storage: state db manager
        """
        Logger.debug('_load_total_supply_amount() start', ICX_LOG_TAG)

        total_supply_amount = storage.get_total_supply(context)
        self._total_supply_amount = total_supply_amount
        Logger.info(f'total_supply: {total_supply_amount}', ICX_LOG_TAG)
        Logger.debug('_load_total_supply_amount() end', ICX_LOG_TAG)

    def get_balance(self,
                    context: Optional['IconScoreContext'],
                    address: Address) -> int:
        """Get the balance of address

        :param context:
        :param address: account address
        :return: the balance of address in loop (1 icx  == 1e18 loop)
        """
        account = self._storage.get_account(context, address)

        # If the address is not present, its balance is 0.
        # Unit: loop (1 icx == 1e18 loop)
        amount = 0

        if account:
            amount = account.icx

        return amount

    def get_total_supply(self, context: 'IconScoreContext') -> int:
        """Get the total supply of icx coin

        :param context:
        :return: (int) amount in loop (1 icx == 1e18 loop)
        """
        return self._total_supply_amount

    def charge_fee(self,
                   context: 'IconScoreContext',
                   from_: Address,
                   fee: int) -> None:
        """Charge a fee for a tx
        It MUST NOT raise any exceptions

        :param context:
        :param from_:
        :param fee:
        :return:
        """
        self._transfer(context, from_, self._fee_treasury_address, fee)

    def transfer(self,
                 context: 'IconScoreContext',
                 from_: Address,
                 to: Address,
                 amount: int) -> bool:
        if amount < 0:
            raise InvalidParamsException('Amount is less than zero')

        return self._transfer(context, from_, to, amount)

    def _transfer(self,
                  context: 'IconScoreContext',
                  from_: Address,
                  to: Address,
                  amount: int) -> bool:
        """Transfer the amount of icx to the account indicated by _to address

        :param context:
        :param from_: icx sender
        :param to: icx receiver
        :param amount: the amount of coin in loop to transfer
        :return True
        """
        if from_ != to and amount > 0:
            # get account info from state db.
            from_account = self._storage.get_account(context, from_)
            to_account = self._storage.get_account(context, to)

            from_account.withdraw(amount)
            to_account.deposit(amount)

            # write newly updated state into state db.
            self._storage.put_account(context, from_account.address, from_account)
            self._storage.put_account(context, to_account.address, to_account)

        return True

    def get_account(self,
                    context: 'IconScoreContext',
                    address: Address) -> Account:
        """Returns the instance of Account indicated by address

        :param context:
        :param address:
        :return: Account
        """
        return self._storage.get_account(context, address)

    def get_treasury_account(self, context: 'IconScoreContext') -> Account:
        """Returns the instance of treasury account

        :param context:
        :return: Account
        """
        return self._storage.get_account(context, self._fee_treasury_address)
