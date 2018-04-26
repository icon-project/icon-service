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

from ..base.address import Address
from .icon_score_base import IconScoreBase
from .icon_score_context import IconScoreContext, call_method, call_fallback
from .icon_score_info_mapper import IconScoreInfoMapper


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

    def __get_icon_score(self,
                         address: Address,
                         readonly: bool) -> IconScoreBase:
        """
        :param address:
        :param readonly:
        :return: IconScoreBase object
        """
        info = self.__icon_score_info_mapper[address]
        return info.get_icon_score(readonly)

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
            self.__install(context.address, data)
        elif data_type == 'update':
            self.__install(context.address, data)
        else:
            pass

    def __install(self, icon_score_address: Address, data: dict) -> bool:
        """Install an icon score

        :param data: zipped binary data
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
        # TODO: Call external method of iconscore
        return call_method(addr_to=icon_score_address,
                           score_mapper=self.__icon_score_info_mapper,
                           readonly=context.readonly,
                           func_name=str(), *(), **{})

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
