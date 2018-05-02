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

from .base.address import Address, AddressPrefix, ICX_ENGINE_ADDRESS
from .base.exception import ExceptionCode, IconException
from .base.block import Block
from .base.message import Message
from .base.transaction import Transaction
from .database.factory import DatabaseFactory
from .database.batch import BlockBatch, TransactionBatch
from .icx.icx_engine import IcxEngine
from .iconscore.icon_score_info_mapper import IconScoreInfo
from .iconscore.icon_score_info_mapper import IconScoreInfoMapper
from .iconscore.icon_score_context import IconScoreContext
from .iconscore.icon_score_context import IconScoreContextType
from .iconscore.icon_score_context import IconScoreContextFactory
from .iconscore.icon_score_engine import IconScoreEngine
from .iconscore.icon_score_result import IconBlockResult, TransactionResult, JsonSerializer


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
        """Get necessary paramters and initialize

        :param icon_score_root_path:
        :param state_db_root_path:
        """
        if not os.path.isdir(icon_score_root_path):
            os.mkdir(icon_score_root_path)
        if not os.path.isdir(state_db_root_path):
            os.mkdir(state_db_root_path)

        self._db_factory = DatabaseFactory(state_db_root_path)
        self._context_factory = IconScoreContextFactory(max_size=5)

        self._icon_score_mapper = IconScoreInfoMapper()

        self._icon_score_engine = IconScoreEngine(
            icon_score_root_path, self._icon_score_mapper)

        self._init_icx_engine(self._db_factory)

        IconScoreContext.icx = self._icx_engine
        IconScoreContext.score_mapper = self._icon_score_mapper

    def _init_icx_engine(self, db_factory: DatabaseFactory) -> None:
        """Initialize icx_engine

        :param db_factory:
        """
        db = db_factory.create_by_name('icon_dex')
        db.address = ICX_ENGINE_ADDRESS

        self._icx_engine = IcxEngine()
        self._icx_engine.open(db)

    def close(self) -> None:
        self._icx_engine.close()

    def genesis_invoke(self, accounts: list) -> None:
        context = self._context_factory.create(IconScoreContextType.GENESIS)

        # NOTICE: context is saved on thread local data
        self._icx_engine.context = context

        genesis_account = accounts[0]
        self._icx_engine.init_genesis_account(
            address=genesis_account['address'],
            amount=genesis_account['balance'])

        fee_treasury_account = accounts[1]
        self._icx_engine.init_fee_treasury_account(
            address=fee_treasury_account['address'],
            amount=fee_treasury_account['balance'])

    def invoke(self,
               block_height: int,
               block_hash: str,
               transactions) -> 'list':
        """Process transactions in a block sent by loopchain

        :param block_height:
        :param block_hash:
        :param transactions: transactions in a block
        :return: The results of transactions
        """
        # Remaining part of a IconScoreContext will be set in each handler.
        context = self._context_factory.create(IconScoreContextType.INVOKE)
        context.block = Block(block_height, block_hash)
        context.block_batch = BlockBatch(block_height, block_hash)
        context.tx_batch = TransactionBatch()
        context.block_result = IconBlockResult(JsonSerializer())

        # NOTICE: context is saved on thread local data
        self._icx_engine.context = context

        for tx in transactions:
            method = tx['method']
            params = tx['params']
            self.call(context, method, params)

    def query(self, method: str, params: dict) -> object:
        """Process a query message call from outside

        State change is not allowed in a query message call

        * icx_getBalance
        * icx_getTotalSupply
        * icx_call

        :param method:
        :param params:
        :return: the result of query
        """
        context = self._context_factory.create(IconScoreContextType.QUERY)
        context.block = None

        # NOTICE: context is saved on thread local data
        self._icx_engine.context = context

        return self.call(context, method, params)

    def call(self,
             context: IconScoreContext,
             method: str,
             params: dict) -> object:
        """Call invoke and query requests in jsonrpc format

        This method is designed to be called in icon_outer_service.py.
        We assume that all param values have been already converted to the proper types.
        (types: Address, int, str, bool, bytes and array)

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

    def _handle_icx_call(self,
                         context: IconScoreContext,
                         params: dict) -> object:
        """Handles an icx_call jsonrpc request
        :param params:
        :return:
        """
        to: Address = params['to']
        data_type = params.get('data_type', None)
        data = params.get('data', None)

        return self._icon_score_engine.query(to, context, data_type, data)

    def _handle_icx_sendTransaction(self,
                                    context: IconScoreContext,
                                    params: dict) -> object:
        """icx_sendTransaction message handler

        * EOA to EOA
        * EOA to Score

        :param params: jsonrpc params
        :return: return value of an IconScoreBase method
            None is allowed
        """
        _tx_hash = params['tx_hash']
        _from: Address = params['from']
        _to: Address = params['to']
        _value: int = params.get('value', 0)
        _fee: int = params['fee']

        self._icx_engine.transfer(_from, _to, _value)

        if _to is None or _to.is_contract:
            # EOA to Score
            _data_type: str = params['data_type']
            _data: dict = params['data']
            _tx_result = self.__handle_score_invoke(
                _tx_hash, _to, context, _data_type, _data)
        else:
            # EOA to EOA
            _tx_result = TransactionResult(
                _tx_hash, context.block, _to, TransactionResult.SUCCESS)

        context.block_result.append(_tx_result)


    def __handle_score_invoke(self,
                              tx_hash: str,
                              to: Address,
                              context: IconScoreContext,
                              data_type: str,
                              data: dict) ->TransactionResult:
        """Handle score invocation

        :param tx_hash: transaction hash
        :param to: a recipient address
        :param context:
        :param data_type:
        :param data: calldata
        :return: A result of the score transaction
        """
        tx_result = TransactionResult(tx_hash, context.block, to)
        try:
            contract_address = self._icon_score_engine.invoke(
                to, context, data_type, data)

            context.block_batch.put_tx_batch(context.tx_batch)
            context.tx_batch.clear()

            tx_result.contract_address = contract_address
            tx_result.status = TransactionResult.SUCCESS
        except:
            tx_result.status = TransactionResult.FAILURE

        return tx_result


    def _set_tx_info_to_context(self,
                                context: IconScoreContext,
                                params: dict) -> None:
        """Set transaction and message info to IconScoreContext

        :param context:
        :param params: jsonrpc params
        """
        _from = params['from']
        _tx_hash = params.get('tx_hash', None)
        _value = params.get('value', 0)

        context.tx = Transaction(tx_hash=_tx_hash, origin=_from)
        context.msg = Message(sender=_from, value=_value)

    def commit(self):
        pass

    def rollback(self):
        pass
