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

from .base.address import Address
from .base.message import Message
from .base.transaction import Transaction
from .database.db import PlyvelDatabase
from .icx.icx_engine import IcxEngine
from .iconscore.icon_score_mapper import IconScoreMapper
from .iconscore.icon_score_context import IconScoreContext


class IconServiceEngine(object):
    """The entry of all icon service related components

    It MUST NOT have any loopchain dependencies.
    It is contained in IconOuterService.
    """

    def __init__(self,
                 icon_score_root_path: str,
                 state_db_root_path: str) -> None:
        """Constructor

        :param icon_score_root_path:
        :param state_db_root_path:
        """
        # jsonrpc handlers
        self.__handlers = {
            'icx_getBalance': self.__handle_getBalance,
            'icx_getTotalSupply': self.__handle_getTotalSupply,
            'icx_call': self.__handle_call,
            'icx_sendTransaction': self.__handle_sendTransaction
        }

        # data_type handlers
        self.__data_type_handlers = {
            'install': self.__install_icon_score,
            'update': self.__update_icon_score,
            'call': self.__call_icon_score
        }

        self.__init_icx_engine(state_db_root_path)
        self.__init_icon_score_mapper(state_db_root_path)

    def __init_icx_engine(self, state_db_root_path: str) -> None:
        """Initialize icx_engine

        :param state_db_root_path:
        """
        self.__icx_engine = IcxEngine()

    def __init_icon_score_mapper(self, state_db_root_path: str) -> None:
        """Initialize icon_score_mapper

        :param state_db_root_path:
        """
        self.__icon_score_mapper = IconScoreMapper()

    def call(self,
             method: str,
             params: dict) -> object:
        """Call invoke and query requests in jsonrpc format

        This method is designed to be called in icon_outer_service.py.
        We assume that all param values have been already converted to the proper types.

        invoke: Changes states of icon scores or icx
        query: query states of icon scores or icx without state changing

        :param method: 'icx_sendTransaction' only
        :param params: params in jsonrpc message
        :return:
            icx_sendTransaction: (bool) True(success) or False(failure)
            icx_getBalance, icx_getTotalSupply, icx_call:
                (dict) result or error object in jsonrpc response
        """
        try:
            handler = self.__handlers[method]
            handler(params)
        except KeyError as ke:
            pass
        except:
            pass

    def __handle_getBalance(self, params: dict) -> int:
        """Returns the icx balance of the given address

        :param params:
        :return: icx balance in loop
        """
        address = params['address']
        return self.__icx_engine.get_balance(address)
        

    def __handle_getTotalSupply(self) -> int:
        """Returns the amount of icx total supply

        :return: icx amount in loop (1 icx == 1e18 loop)
        """
        return self.__icx_engine.get_total_supply()

    def __handle_call(self, params: dict) -> object:
        """
        :param params:
        :return:
        """

    def __handle_sendTransaction(self, params: dict) -> bool:
        """Handles an icx_sendTransaction jsonrpc request

        :param params: jsonrpc params
        :return: True(success) False(Failure)
        """
        _from = params['from']
        tx_hash = params['tx_hash']
        value = params.get('value', 0)
        data_type = params.get('data_type', None)
        data = params.get('data', None)

        tx = Transaction(
            tx_hash=tx_hash,
            origin=Address.from_string(_from))

        msg = Message(sender=_from, value=value)

        if data_type == None:
            # icx transfer
            self.__icx_engine.transfer(_from, to)
        elif data_type == 'install':
            pass
        elif data_type == 'update':
            pass
        elif data_type == 'call':
            self.__call_icon_score(data)

        data = params.get('data', None)

        db = PlyvelDatabase('leveldb')

        context = IconScoreContext(tx=tx, msg=msg, db=db)

    def __call_icon_score(self, params: dict) -> object:
        """
        """
        pass
