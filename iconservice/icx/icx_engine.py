# -*- coding: utf-8 -*-

# Copyright 2017-2018 theloop Inc.
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

from .icx_account import Account, AccountType
from .icx_config import FIXED_FEE
from .icx_logger import IcxLogger, logd, logi, logw, loge
from .icx_storage import IcxStorage
from ..base.address import Address, AddressPrefix
from ..base.exception import ExceptionCode, IconException


class IcxEngine(object):
    """Manages the balances of icon accounts

    The basic unit of icx coin is loop. (1 icx == 1e18 loop)
    """

    def __init__(self) -> None:
        """Constructor
        """
        self.__storage: IcxStorage = None
        self.__logger: IcxLogger = None
        self.__total_supply_amount: int = 0
        self.__genesis_address: Address = None
        self.__fee_treasury_address: Address = None

    def open(self, db: 'InternalScoreDatabase', logger: IcxLogger=None) -> None:
        """Open engine

        Get necessary parameters from caller and begin to use storage(leveldb)

        :param storage: IcxStorage object to access state db
        :param logger: IcxLogger to log debugging info.
        """
        self.close()

        storage = IcxStorage(db)
        self.__storage = storage
        self.__logger = logger
        self.__db = db

        self.__load_genesis_account_from_storage(storage)
        self.__load_fee_treasury_account_from_storage(storage)
        self.__load_total_supply_amount_from_storage(storage)

    def close(self) -> None:
        """Close resources
        """
        if self.__storage:
            self.__storage.close()
            self.__storage = None

    def init_genesis_account(self, address: Address, amount: int) -> None:
        """Initialize the state of genesis account
        with the info from genesis block

        :param address: account address
        :param amount: the initial balance of genesis_account
        """
        account = Account(account_type=AccountType.GENESIS,
                          address=address,
                          icx=amount)

        obj = {
            'version': 0,
            'address': str(address)
        }
        text = json.dumps(obj)
        self.__storage.put_text('genesis', text)

        self.__storage.put_account(account.address, account)
        self.__genesis_address = address

        # icx amount of genesis account is equal to total supply at the first time.
        self.__total_supply_amount = account.icx
        self.__storage.put_total_supply(self.__total_supply_amount)

    def init_fee_treasury_account(self, address: Address, amount: int=0) -> None:
        """Initialize fee treasury account with genesis block.

        :param address: account address
        :param amount: the initial balance of fee_treasury_account
        """
        account = Account(account_type=AccountType.TREASURY,
                          address=address,
                          icx=amount)

        # Save fee_treasury info in json format to state db.
        obj = {
            'version': 0,
            'address': str(address)
        }
        text = json.dumps(obj)
        self.__storage.put_text('fee_treasury', text)

        self.__storage.put_account(account.address, account)
        self.__fee_treasury_address = address

    def __load_genesis_account_from_storage(self, storage: IcxStorage) -> None:
        """Load genesis account info from state db

        :param storage: (IcxStorage) state db wrapper
        """
        text = storage.get_text('genesis')
        if text:
            obj = json.loads(text)
            self.__genesis_address = Address.from_string(obj['address'])

    def __load_fee_treasury_account_from_storage(self,
                                                 storage: IcxStorage) -> None:
        """Load fee_treasury_account info from state db

        :param storage: state db manager
        """
        text = storage.get_text('fee_treasury')
        if text:
            obj = json.loads(text)
            self.__fee_treasury_address = Address.from_string(obj['address'])

    def __load_total_supply_amount_from_storage(self,
                                                storage: IcxStorage) -> None:
        """Load total coin supply amount from state db

        :param storage: state db manager
        """
        logd(self.__logger, '__load_total_supply_amount() start')

        self.__total_supply_amount = storage.get_total_supply()
        logi(self.__logger, f'total_supply: {self.__total_supply_amount}')

        logd(self.__logger, '__load_total_supply_amount() end')

    def get_balance(self, address: Address) -> int:
        """Get the balance of address

        :param address: account address
        :return: the balance of address in loop (1 icx  == 1e18 loop)
        """

        account = self.__storage.get_account(address)

        # If the address is not present, its balance is 0.
        # Unit: loop (1 icx == 1e18 loop)
        amount = 0

        if account:
            amount = account.icx

        return amount

    def get_total_supply(self) -> int:
        """Get the total supply of icx coin

        :return: (int) amount in loop (1 icx == 1e18 loop)
        """
        return self.__total_supply_amount

    def transfer_with_fee(self,
                          _from: Address,
                          _to: Address,
                          _amount: int,
                          _fee: int) -> bool:
        if self.context.readonly:
            raise IconException(
                ExceptionCode.INVALID_REQUEST,
                'icx transfer is not allowed on readonly context')

        return self._transfer_with_fee(_from, _to, _amount, _fee)

    def _transfer_with_fee(self, _from: Address, _to: Address, _amount: int, _fee: int) -> bool:
        """Transfer the amount of icx to an account indicated by _to address

        :param _from: (string)
        :param _to: (string)
        :param _amount: (int) the amount of coin in loop to transfer
        :param _fee: (int) transaction fee (0.01 icx)
        :exception: IconException
        """
        _fee_treasury_address = self.__fee_treasury_address

        logd(self.__logger,
             f'from: {_from} '
             f'to: {_to} '
             f'amount: {_amount} '
             f'fee: {_fee}')

        if _from == _to:
            raise IconException(ExceptionCode.INVALID_PARAMS)
        if _from == _fee_treasury_address:
            raise IconException(ExceptionCode.INVALID_PARAMS)
        if _to == _fee_treasury_address:
            raise IconException(ExceptionCode.INVALID_PARAMS)
        if _fee != FIXED_FEE:
            raise IconException(ExceptionCode.INVALID_FEE)

        # get account info from state db.
        from_account = self.__storage.get_account(_from)
        to_account = self.__storage.get_account(_to)
        fee_account = self.__storage.get_account(_fee_treasury_address)

        logi(self.__logger,
             'before:  '
             f'from: {_from} '
             f'from_amount: {from_account.icx} '
             f'to: {_to} '
             f'to_amount: {to_account.icx} '
             f'fee_treasury: {fee_account.address} '
             f'fee_amount: {fee_account.icx}')

        from_account.withdraw(_amount + _fee)
        to_account.deposit(_amount)
        fee_account.deposit(_fee)

        # write newly updated state into state db.
        self.__storage.put_account(from_account.address, from_account)
        self.__storage.put_account(to_account.address, to_account)
        self.__storage.put_account(fee_account.address, fee_account)

        logi(self.__logger,
             'after: '
             f'from: {_from} '
             f'from_amount: {from_account.icx} '
             f'to: {_to} '
             f'to_amount: {to_account.icx} '
             f'fee_treasury: {fee_account.address} '
             f'fee_amount: {fee_account.icx}')
        logd(self.__logger, 'send_transaction() end')

        return True

    def transfer(self,
                 _from: Address,
                 _to: Address,
                 _amount: int) -> bool:
        if self.context.readonly:
            raise IconException(
                ExceptionCode.INVALID_REQUEST,
                'icx transfer is not allowed on readonly context')

        return self._transfer(_from, _to, _amount)

    def _transfer(self, _from: Address, _to: Address, _amount: int) -> bool:
        """Transfer the amount of icx to the account indicated by _to address

        :param _from: icx sender
        :param _to: icx receiver
        :param _amount: the amount of coin in loop to transfer
        """
        if _from != _to and _amount > 0:
            # get account info from state db.
            from_account = self.__storage.get_account(_from)
            to_account = self.__storage.get_account(_to)

            from_account.withdraw(_amount)
            to_account.deposit(_amount)

            # write newly updated state into state db.
            self.__storage.put_account(from_account.address, from_account)
            self.__storage.put_account(to_account.address, to_account)

        return True

    @property
    def context(self) -> 'IconScoreContext':
        """context is saved in thread local data

        :param value:
        """
        return self.__db.context

    @context.setter
    def context(self, value: 'IconScoreContext') -> None:
        """context is saved in thread local data

        :param value:
        """
        self.__db.context = value

    def get_account(self, address: Address) -> Account:
        """Returns the instance of Account indicated by address

        :param address:
        :return: Account
        """
        return self.__storage.get_account(address)
