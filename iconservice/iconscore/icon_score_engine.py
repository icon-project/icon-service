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
"""IconScoreEngine module
"""


from ..base.address import Address, AddressPrefix, create_address
from ..base.exception import ExceptionCode, IconException, IconScoreBaseException
from .icon_score_base import IconScoreBase
from .icon_score_context import IconScoreContext, call_method, call_fallback
from .icon_score_info_mapper import IconScoreInfoMapper, IconScoreInfo
from .icon_score_loader import IconScoreLoader
from ..database.factory import DatabaseFactory
from ..database.db import IconScoreDatabase


class IconScoreEngine(object):
    """Calls external functions provided by each IconScore
    """

    def __init__(self,
                 icon_score_root_path: str,
                 icx_storage: 'IcxStorage',
                 icon_score_info_mapper: IconScoreInfoMapper,
                 db_factory: DatabaseFactory) -> None:
        """Constructor

        :param icon_score_root_path:
        :param icx_storage: Get IconScore owner info from icx_storage
        :param icon_score_info_mapper:
        :param db_factory:
        """
        # handlers for processing calldata
        self._handler = {
            'install': self.__install,
            'update': self.__update,
            'call': self.__call
        }

        self.__icon_score_root_path = icon_score_root_path
        self.__icx_storage = icx_storage
        self.__icon_score_info_mapper = icon_score_info_mapper
        self.__db_factory = db_factory

    def __get_icon_score(self, address: Address) -> IconScoreBase:
        """
        :param address:
        :return: IconScoreBase object
        """

        icon_score_info = self.__icon_score_info_mapper[address]
        if icon_score_info is None:
            if not self.__db_factory.is_exist(address):
                raise IconScoreBaseException("icon_score_info is None")
            else:
                self.__load_score(address)

        icon_score = icon_score_info.icon_score
        return icon_score

    def __create_icon_score_database(self, address: Address) -> 'IconScoreDatabase':
        """Create IconScoreDatabase instance
        with icon_score_address and ContextDatabase
            
        :param address: icon_score_address    
        """
        context_db = self.__db_factory.create_by_address(address)
        score_db = IconScoreDatabase(context_db)
        return score_db

    def __load_score_wrapper(self, address: Address) -> object:
        """Load IconScoreBase subclass from IconScore python package

        :param address: icon_score_address
        :return: IconScoreBase subclass (NOT instance)
        """
        loader = IconScoreLoader(self.__icon_score_root_path)
        score_wrapper = loader.load_score(address.body.hex())
        if score_wrapper is None:
            raise IconScoreBaseException(f'score_wrapper load Fail {address}')

        return score_wrapper

    def __add_score_to_mapper(self, icon_score) -> None:
        info = IconScoreInfo(icon_score)
        self.__icon_score_info_mapper[icon_score.address] = info
        return info

    def invoke(self,
               icon_score_address: Address,
               context: IconScoreContext,
               data_type: str,
               data: dict) -> None:
        """Handle calldata contained in icx_sendTransaction message

        :param icon_score_address:
        :param context:
        :param data_type:
        :param data: calldata
        """
        if data_type == 'call':
            self.__call(context, icon_score_address, data)
        elif data_type == 'install':
            # context.tx.origin is the owner of icon_score to install
            self.__install(context, icon_score_address, data)
        elif data_type == 'update':
            self.__update(context, icon_score_address, data)
        else:
            raise IconException(ExceptionCode.INVALID_PARAMS, "Invalid data type")

    def __install(self,
                  context: 'IconScoreContext',
                  icon_score_address: Address,
                  data: dict) -> None:
        """Install an icon score

        Owner check has been already done in IconServiceEngine

        Process Order
        - Install IconScore package to file system
        - Load IconScore wrapper
        - Create Database
        - Create an IconScore instance with address, owner and database
        - Execute IconScoreBase.genesis_invoke()
        - Register IconScoreInfo to IconScoreInfoMapper

        :param icon_score_address:
        :param owner:
        :param data: zipped binary data + mime_type
        """
        # Install IconScore package

        score_wrapper = self.__load_score_wrapper(icon_score_address)
        score_db = self.__create_icon_score_database(icon_score_address)

        icon_score = score_wrapper(score_db, owner=context.tx.origin)
        icon_score.genesis_init()

        self.__add_score_to_mapper(icon_score)

    def __update(self,
                 context: 'IconScoreContext',
                 icon_score_address: Address,
                 data: dict) -> bool:
        """Update an icon score

        Owner check has been already done in IconServiceEngine

        :param icon_score_address:
        :param owner:
        :param data: zipped binary data + mime_type
        """
        raise NotImplementedError('Score update is not implemented')

    def __call(self,
               context: IconScoreContext,
               icon_score_address: Address,
               calldata: dict) -> object:
        """Handle jsonrpc

        :param icon_score_address:
        :param context:
        :param calldata:
        """
        method: str = calldata['method']
        params: dict = calldata['params']

        # TODO: Call external method of iconscore
        icon_score = self.__get_icon_score(icon_score_address)
        return call_method(addr_to=icon_score_address,
                           icon_score=icon_score,
                           func_name=method, *(), **params)

    def __fallback(self, icon_score_address: Address):
        """When an IconScore receives some coins and calldata is None,
        fallback function is called.

        :param icon_score_address:
        """

        # TODO: Call fallback method of iconscore
        icon_score = self.__get_icon_score(icon_score_address)
        call_fallback(addr_to=icon_score_address,
                      icon_score=icon_score)

    def query(self,
              icon_score_address: Address,
              context: IconScoreContext,
              data_type: str,
              data: dict) -> object:
        """Run an external method of iconscore without state changing

        Handles messagecall of icx_call
        """
        if data_type == 'call':
            return self.__call(icon_score_address, context, data)
