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
from ..base.exception import Address, AddressPrefix
from .icon_score_base import IconScoreBase
from .icon_score_context import IconScoreContext
from .icon_score_info_mapper import IconScoreInfoMapper
from ..utils import call_method


def call_icon_score_method(
        icon_score: object,
        method_name: str,
        context: IconScoreContext,
        params: dict=None) -> object:
    """Call a method of an icon score in a generic way.

    :param icon_score:
    :param method_name:
    :param params:
    """
    method = getattr(icon_score, method_name)
    if not isinstance(method, callable):
        raise ValueError('Invalid method name')

    if params:
        return method(context, **params)
    else:
        return method(context)


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
            'install': self._install,
            'update': self._update,
            'call': self._call_in_invoke
        }
        self._icon_score_info_mapper = icon_score_info_mapper

    def _get_icon_score(self,
                        address: Address,
                        readonly: bool) -> IconScoreBase:
        """
        :param address:
        :param readonly:
        :return: IconScoreBase object
        """
        info = self._icon_score_info_mapper[address]
        return info.get_icon_score(readonly)

    def invoke(self,
               icon_score_address: Address,
               context: IconScoreContext,
               data_type: str,
               data: dict) -> bool:
        """Handle calldata contained in icx_sendTransaction message

        :param icon_score_address:
        :param context:
        :param data: calldata
        """
        if data_type == 'call':
            self._call_in_invoke(icon_score_address, context, data)
        elif data_type == 'install':
            self._install(context, data)
        elif data_type == 'update':
            self._install(context, data)
        else:


    def _install(self, icon_score_address: Address, data: bytes) -> bool:
        """Install an icon score

        :param data: zipped binary data
        """

    def _update(self, icon_score_address: Address, data: bytes) -> bool:
        """Update an icon score

        :param data: zipped binary data
        """

    def _call_in_invoke(self,
                        icon_score_address: Address,
                        context: IconScoreContext,
                        calldata: dict) -> object:
        """Handle jsonrpc

        :param icon_score_address:
        :param context:
        :param calldata:
        """
        # TODO: Call external method of iconscore

    def _fallback(self,
                  icon_score_address: Address,
                  context: IconScoreContext):
        """When an IconScore receives some coins and calldata is None,
        fallback function is called.

        :param icon_score_address:
        :param context:
        """
        # TODO: Call fallback method of iconscore

    def query(self,
              icon_score_address: Address,
              context: IconScoreContext,
              data_type: str,
              data: dict) -> object:
        """Run an external method of iconscore without state changing

        Handles messagecall of icx_call
        """
        if data_type == 'call':
            return self._call_in_query(icon_score_address, context, data)

    def _call_in_query(self,
                       icon_score_address: Address,
                       context: IconScoreContext,
                       calldata: dict):
        """Run an external method of iconscore indicated by icon_score_address
        without state changing

        :param icon_score_address:
        :param context:
        :param calldata:
        """
