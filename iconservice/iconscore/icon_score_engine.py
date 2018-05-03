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

TEST_OWNER = create_address(AddressPrefix.EOA, b'owner')


class IconScoreEngine(object):
    """Calls external functions provided by each IconScore
    """

    def __init__(self,
                 icon_score_root_path: str,
                 icon_score_info_mapper: IconScoreInfoMapper,
                 db_factory: DatabaseFactory) -> None:
        """Constructor

        :param icon_score_root_path:
        :param icon_score_info_mapper:
        """
        # handlers for processing calldata
        self._handler = {
            'install': self.__install,
            'update': self.__update,
            'call': self.__call
        }
        self.__icon_score_info_mapper = icon_score_info_mapper
        self.__db_factory = db_factory
        self.__icon_score_root_path = icon_score_root_path

    def __get_icon_score(self, address: Address) -> IconScoreBase:
        """
        :param address:
        :return: IconScoreBase object
        """

        icon_score_info = self.__icon_score_info_mapper.get(address)
        if icon_score_info is None:
            if not self.__db_factory.is_exist(address):
                raise IconScoreBaseException("icon_score_info is None")
            else:
                self.__load_score(address)

        icon_score = icon_score_info.icon_score
        return icon_score

    def __install_score(self, address: Address, owner: Address):
        loader = IconScoreLoader(self.__icon_score_root_path)
        score_wrapper = loader.load_score(address.body.hex())
        if score_wrapper is None:
            raise IconScoreBaseException(f'score_wrapper load Fail {address}')

        context_db = self.__db_factory.create_by_address(address)
        score_db = IconScoreDatabase(context_db)

        score = score_wrapper(score_db, owner)
        score.genesis_init()

        info = IconScoreInfo(score, owner)
        self.__icon_score_info_mapper[address] = info
        return info

    def __load_score(self, address: Address):
        loader = IconScoreLoader()
        score_wrapper = loader.load_score(address.body.hex())
        if score_wrapper is None:
            raise IconScoreBaseException(f'score_wrapper load Fail {address}')

        context_db = self.__db_factory.create_by_address(address)
        score_db = IconScoreDatabase(context_db)

        # TODO have to get owner from anywhere.
        owner = address
        score = score_wrapper(score_db, owner)

        info = IconScoreInfo(score, owner)
        self.__icon_score_info_mapper[Address] = info
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
            self.__call(icon_score_address, context, data)
        elif data_type == 'install':
            # TODO have to owner setting!
            self.__install(icon_score_address, TEST_OWNER, data)
        elif data_type == 'update':
            self.__update(icon_score_address, data)
        else:
            raise IconException(ExceptionCode.INVALID_PARAMS, "Invalid data type")

    def __install(self, icon_score_address: Address, owner: Address, data: dict):
        """Install an icon score

        :param data: zipped binary data
        """

        self.__install_score(icon_score_address, owner)

    def __update(self, icon_score_address: Address, data: dict) -> bool:
        """Update an icon score

        :param data: zipped binary data
        """
        pass

    def __call(self,
               icon_score_address: Address,
               context: IconScoreContext,
               calldata: dict) -> object:
        """Handle jsonrpc

        :param icon_score_address:
        :param context:
        :param calldata:
        """
        method: str = calldata['method']
        params: dict = calldata['params']

        # TODO: Call external method of iconscore
        return call_method(addr_to=icon_score_address,
                           icon_score=self.__get_icon_score(icon_score_address),
                           func_name=method, *(), **params)

    def __fallback(self, icon_score_address: Address):
        """When an IconScore receives some coins and calldata is None,
        fallback function is called.

        :param icon_score_address:
        """

        # TODO: Call fallback method of iconscore
        call_fallback(addr_to=icon_score_address,
                      icon_score=self.__get_icon_score(icon_score_address))

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
