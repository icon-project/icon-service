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
from .icx_storage import IcxStorage
from ..base.address import Address
from ..base.exception import ExceptionCode, ICXException
from ..logger import Logger
from ..icon_config import *

from typing import TYPE_CHECKING, Optional
if TYPE_CHECKING:
    from ..iconscore.icon_score_context import IconScoreContext


class IcxEngine(object):
    """Manages the balances of icon accounts

    The basic unit of icx coin is loop. (1 icx == 1e18 loop)
    _context property is inherited from ContextGetter
    """

    def __init__(self) -> None:
        """Constructor
        """
        self.__storage: IcxStorage = None
        self.__total_supply_amount: int = 0
        self.__genesis_address: Address = None
        self.__fee_treasury_address: Address = None

    def open(self, storage: 'IcxStorage') -> None:
        """Open engine

        Get necessary parameters from caller and begin to use storage(leveldb)

        :param storage: IcxStorage object to access state db
        """
        self.close()

        self.__storage = storage

        context = None
        self.__load_genesis_account_from_storage(context, storage)
        self.__load_fee_treasury_account_from_storage(context, storage)
        self.__load_total_supply_amount_from_storage(context, storage)

    def close(self) -> None:
        """Close resources
        """
        if self.__storage:
            self.__storage.close(context=None)
            self.__storage = None

    def init_account(self,
                     context: 'IconScoreContext',
                     account_type: 'AccountType',
                     account_name: str,
                     address: 'Address',
                     amount: int) -> None:

        account = Account(account_type=account_type, address=address, icx=int(amount))

        obj = {
            'version': 0,
            'address': str(address)
        }

        text = json.dumps(obj)
        self.__storage.put_text(context, account_name, text)

        self.__storage.put_account(context, account.address, account)
        if account_type == AccountType.GENESIS:
            self.__genesis_address = address
            self.__total_supply_amount += account.icx
            self.__storage.put_total_supply(context, self.__total_supply_amount)
        elif account == AccountType.TREASURY:
            self.__fee_treasury_address = address
        else:
            self.__total_supply_amount += account.icx
            self.__storage.put_total_supply(context, self.__total_supply_amount)

    def __load_genesis_account_from_storage(self,
                                            context: Optional['IconScoreContext'],
                                            storage: IcxStorage) -> None:
        """Load genesis account info from state db

        :param context:
        :param storage: (IcxStorage) state db wrapper
        """
        text = storage.get_text(context, 'genesis')
        if text:
            obj = json.loads(text)
            self.__genesis_address = Address.from_string(obj['address'])

    def __load_fee_treasury_account_from_storage(self,
                                                 context: Optional['IconScoreContext'],
                                                 storage: IcxStorage) -> None:
        """Load fee_treasury_account info from state db

        :param context:
        :param storage: state db manager
        """
        text = storage.get_text(context, 'fee_treasury')
        if text:
            obj = json.loads(text)
            self.__fee_treasury_address = Address.from_string(obj['address'])

    def __load_total_supply_amount_from_storage(self,
                                                context: Optional['IconScoreContext'],
                                                storage: IcxStorage) -> None:
        """Load total coin supply amount from state db

        :param context:
        :param storage: state db manager
        """
        Logger.debug('__load_total_supply_amount() start', ICX_LOG_TAG)

        total_supply_amount = storage.get_total_supply(context)
        self.__total_supply_amount = total_supply_amount
        Logger.info(f'total_supply: {total_supply_amount}', ICX_LOG_TAG)
        Logger.debug('__load_total_supply_amount() end', ICX_LOG_TAG)

    def get_balance(self,
                    context: 'IconScoreContext',
                    address: Address) -> int:
        """Get the balance of address

        :param context:
        :param address: account address
        :return: the balance of address in loop (1 icx  == 1e18 loop)
        """
        account = self.__storage.get_account(context, address)

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
        return self.__total_supply_amount

    def transfer_with_fee(self,
                          _context: 'IconScoreContext',
                          _from: Address,
                          _to: Address,
                          _amount: int,
                          _fee: int) -> bool:
        if _context.readonly:
            raise ICXException(
                'icx transfer is not allowed on readonly context',
                ExceptionCode.INVALID_REQUEST)

        return self._transfer_with_fee(_context, _from, _to, _amount, _fee)

    def _transfer_with_fee(self,
                           context: 'IconScoreContext',
                           _from: Address,
                           _to: Address,
                           _amount: int,
                           _fee: int) -> bool:
        """Transfer the amount of icx to an account indicated by _to address

        :param context:
        :param _from: (string)
        :param _to: (string)
        :param _amount: (int) the amount of coin in loop to transfer
        :param _fee: (int) transaction fee (0.01 icx)
        :exception: ICXException
        """
        _fee_treasury_address = self.__fee_treasury_address

        Logger.debug(f'from: {_from} '
                     f'to: {_to} '
                     f'amount: {_amount} '
                     f'fee: {_fee}',
                     ICX_LOG_TAG)

        if _from == _to:
            raise ICXException('match _from and _to address', ExceptionCode.INVALID_PARAMS)
        if _from == _fee_treasury_address:
            raise ICXException('match _from and fee_treasure address', ExceptionCode.INVALID_PARAMS)
        if _to == _fee_treasury_address:
            raise ICXException('match _to and fee_treasure address', ExceptionCode.INVALID_PARAMS)
        if _fee != FIXED_FEE:
            raise ICXException('invalid fee', ExceptionCode.INVALID_PARAMS)

        # get account info from state db.
        from_account = self.__storage.get_account(context, _from)
        to_account = self.__storage.get_account(context, _to)
        fee_account = self.__storage.get_account(context, _fee_treasury_address)

        Logger.info('before:  '
                    f'from: {_from} '
                    f'from_amount: {from_account.icx} '
                    f'to: {_to} '
                    f'to_amount: {to_account.icx} '
                    f'fee_treasury: {fee_account.address} '
                    f'fee_amount: {fee_account.icx}',
                    ICX_LOG_TAG)

        from_account.withdraw(_amount + _fee)
        to_account.deposit(_amount)
        fee_account.deposit(_fee)

        # write newly updated state into state db.
        self.__storage.put_account(context, from_account.address, from_account)
        self.__storage.put_account(context, to_account.address, to_account)
        self.__storage.put_account(context, fee_account.address, fee_account)

        Logger.info('after: '
                    f'from: {_from} '
                    f'from_amount: {from_account.icx} '
                    f'to: {_to} '
                    f'to_amount: {to_account.icx} '
                    f'fee_treasury: {fee_account.address} '
                    f'fee_amount: {fee_account.icx}',
                    ICX_LOG_TAG)
        Logger.debug('send_transaction() end', ICX_LOG_TAG)

        return True

    def transfer(self,
                 _context: 'IconScoreContext',
                 _from: Address,
                 _to: Address,
                 _amount: int) -> bool:
        if _context.readonly:
            raise ICXException(
                'icx transfer is not allowed on readonly context',
                ExceptionCode.INVALID_REQUEST)

        if _amount < 0:
            raise ICXException('amount is less than zero',
                               ExceptionCode.INVALID_PARAMS)

        return self._transfer(_context, _from, _to, _amount)

    def _transfer(self,
                  context: 'IconScoreContext',
                  _from: Address,
                  _to: Address,
                  _amount: int) -> bool:
        """Transfer the amount of icx to the account indicated by _to address

        :param context:
        :param _from: icx sender
        :param _to: icx receiver
        :param _amount: the amount of coin in loop to transfer
        """
        if _from != _to and _amount > 0:
            # get account info from state db.
            from_account = self.__storage.get_account(context, _from)
            to_account = self.__storage.get_account(context, _to)

            from_account.withdraw(_amount)
            to_account.deposit(_amount)

            # write newly updated state into state db.
            self.__storage.put_account(context, from_account.address, from_account)
            self.__storage.put_account(context, to_account.address, to_account)

        return True

    def get_account(self,
                    context: 'IconScoreContext',
                    address: Address) -> Account:
        """Returns the instance of Account indicated by address

        :param context:
        :param address:
        :return: Account
        """
        return self.__storage.get_account(context, address)
