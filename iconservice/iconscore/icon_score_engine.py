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


from ..base.address import Address, AddressPrefix
from ..base.exception import ExceptionCode, IconException, IconScoreBaseException
from .icon_score_base import IconScoreBase
from .icon_score_context import IconScoreContext, call_method, call_fallback
from .icon_score_info_mapper import IconScoreInfoMapper
from .icon_score_loader import IconScoreLoader


class IconScoreEngine(object):
    """Calls external functions provided by each IconScore
    """

    def __init__(self,
                 icon_score_root_path: str,
                 icon_score_info_mapper: IconScoreInfoMapper) -> None:
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

    def __get_icon_score(self, address: Address) -> IconScoreBase:
        """
        :param address:
        :return: IconScoreBase object
        """

        icon_score_info = self.__icon_score_info_mapper.get(address)
        if icon_score_info is None:
            loader = IconScoreLoader()
            loader.load_score(address)
            raise IconScoreBaseException("icon_score_info is None")

        icon_score = icon_score_info.icon_score
        return icon_score

    def invoke(self,
               icon_score_address: Address,
               context: IconScoreContext,
               data_type: str,
               data: dict) -> Address:
        """Handle calldata contained in icx_sendTransaction message

        :param icon_score_address:
        :param context:
        :param data_type:
        :param data: calldata
        :return: A newly created contract address if `data_type` is `install`, otherwise None.
        """
        if data_type == 'call':
            self.__call(icon_score_address, context, data)
            return None
        elif data_type == 'install':
            return self.__install(context.address, data)
        elif data_type == 'update':
            self.__update(context, data)
            return None
        else:
            raise IconException(ExceptionCode.INVALID_PARAMS, "Invalid data type")

    def __install(self, icon_score_address: Address, data: bytes) -> bool:
        """Install an icon score

        :param data: zipped binary data
        :return: newly created contract address
        """
        pass

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
                           score_mapper=self.__icon_score_info_mapper,
                           readonly=context.readonly,
                           func_name=method, *(), **params)

    def __fallback(self,
                   icon_score_address: Address,
                   context: IconScoreContext):
        """When an IconScore receives some coins and calldata is None,
        fallback function is called.

        :param icon_score_address:
        :param context:
        """
        # TODO: Call fallback method of iconscore
        call_fallback(addr_to=icon_score_address,
                      score_mapper=self.__icon_score_info_mapper,
                      readonly=context.readonly)

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
