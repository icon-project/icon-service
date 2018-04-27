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
import os

from .base.address import Address, AddressPrefix
from .base.exception import ExceptionCode, IconException
from .base.message import Message
from .base.transaction import Transaction
from .database.db import PlyvelDatabase
from .database.factory import DatabaseFactory
from .icx.icx_engine import IcxEngine
from .iconscore.icon_score_info_mapper import IconScoreInfo
from .iconscore.icon_score_info_mapper import IconScoreInfoMapper
from .iconscore.icon_score_context import IconScoreContext
from .iconscore.icon_score_context import IconScoreContextFactory
from .iconscore.icon_score_engine import IconScoreEngine


class IconServiceEngine(object):
    """The entry of all icon service related components

    It MUST NOT have any loopchain dependencies.
    It is contained in IconOuterService.
    """

    def __init__(self) -> None:
        """Constructor

        :param icon_score_root_path:
        :param state_db_root_path:
        """
        # jsonrpc handlers
        self._handlers = {
            'icx_getBalance': self._handle_icx_getBalance,
            'icx_getTotalSupply': self._handle_icx_getTotalSupply,
            'icx_call': self._handle_icx_call,
            'icx_sendTransaction': self._handle_icx_sendTransaction
        }

    def open(self,
             icon_score_root_path: str,
             state_db_root_path: str) -> None:
        """
        """
        if not os.path.isdir(icon_score_root_path):
            os.mkdir(icon_score_root_path)
        if not os.path.isdir(state_db_root_path):
            os.mkdir(state_db_root_path)

        self._db_factory = DatabaseFactory(state_db_root_path)
        self._context_factory = IconScoreContextFactory(max_size=5)

        self._icon_score_mapper = IconScoreInfoMapper()
        IconScoreInfo.set_db_factory(self._db_factory)

        self._icon_score_engine = IconScoreEngine(
            icon_score_root_path, self._icon_score_mapper)

        self._init_icx_engine(self._db_factory)

    def _init_icx_engine(self, db_factory: DatabaseFactory) -> None:
        """Initialize icx_engine

        :param db_factory:
        """
        db = db_factory.create_by_name('icon_dex.db')

        self._icx_engine = IcxEngine()
        self._icx_engine.open(db)

    def close(self) -> None:
        self._icx_engine.close()

    def call(self,
             context: IconScoreContext,
             method: str,
             params: dict) -> object:
        """Call invoke and query requests in jsonrpc format

        This method is designed to be called in icon_outer_service.py.
        We assume that all param values have been already converted to the proper types.

        invoke: Changes states of icon scores or icx
        query: query states of icon scores or icx without state changing

        :param context:
        :param method: 'icx_sendTransaction' only
        :param params: params in jsonrpc message
        :return:
            icx_sendTransaction: (bool) True(success) or False(failure)
            icx_getBalance, icx_getTotalSupply, icx_call:
                (dict) result or error object in jsonrpc response
        """
        try:
            handler = self._handlers[method]
            return handler(context, params)
        except KeyError as ke:
            print(ke)
        except Exception as e:
            print(e)

    def _handle_icx_getBalance(self,
                               context: IconScoreContext,
                               params: dict) -> int:
        """Returns the icx balance of the given address

        :param context:
        :param params:
        :return: icx balance in loop
        """
        address = params['address']
        return self._icx_engine.get_balance(address)

    def _handle_icx_getTotalSupply(self, context: IconScoreContext) -> int:
        """Returns the amount of icx total supply

        :param context:
        :return: icx amount in loop (1 icx == 1e18 loop)
        """
        return self._icx_engine.get_total_supply()

    def _handle_icx_call(self, params: dict) -> object:
        """Handles an icx_call jsonrpc request
        :param params:
        :return:
        """
        to: Address = params['to']
        if to.prefix != AddressPrefix.CONTRACT:
            raise IconException(
                ExceptionCode.INVALID_PARAMS,
                f'{str(to)} is not an score address')

        data_type = params.get('data_type', None)
        if data_type != 'call':
            raise IconException(ExceptionCode.INVALID_PARAMS)

        data = params.get('data', None)
        if not isinstance(data, dict):
            raise IconException(ExceptionCode.INVALID_PARAMS)

        context = self._create_context(params=params, readonly=True)
        return self._icon_score_engine.query(to, context, data_type, data)

    def _handle_icx_sendTransaction(self,
                                    params: dict,
                                    context: IconScoreContext=None) -> object:
        """Handles an icx_sendTransaction jsonrpc request

        * EOA to EOA
        * EOA to Score

        :param params: jsonrpc params
        :return: return value of an IconScoreBase method
            None is allowed
        """
        _from: Address = params['from']
        _to: Address = params['to']
        _value: int = params.get('value', 0)
        _fee: int = params['fee']

        self._icx_engine.transfer(context.readonly, _from, _to, _value)

        context: IconScoreContext = self._create_context(
            params=params, readonly=False)
        _data_type: str = params['data_type']
        _data: dict = params['data']

        return self._icon_score_engine.invoke(_to, context, _data_type, _data)

    def _create_context(self,
                        params: dict,
                        readonly: bool) -> IconScoreContext:
        """Create an IconScoreContext
        """
        _from = params['from']
        tx_hash = params.get('tx_hash', None)
        value = params.get('value', 0)

        context = self._context_factory.create()
        context.readonly = readonly
        context.tx = Transaction(tx_hash=tx_hash, origin=_from)
        context.msg = Message(sender=_from, value=value)

        return context
