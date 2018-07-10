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

from typing import TYPE_CHECKING

from .icon_score_context import ContextContainer
from .icon_score_context import IconScoreContext, call_method, call_fallback
from .icon_score_info_mapper import IconScoreInfoMapper
from ..base.address import Address
from ..base.exception import InvalidParamsException, ServerErrorException

if TYPE_CHECKING:
    from ..icx.icx_storage import IcxStorage


class IconScoreEngine(ContextContainer):
    """Calls external functions provided by each IconScore
    """

    def __init__(self,
                 icx_storage: 'IcxStorage',
                 icon_score_info_mapper: 'IconScoreInfoMapper') -> None:
        """Constructor

        :param icx_storage: Get IconScore owner info from icx_storage
        :param icon_score_info_mapper:
        """
        super().__init__()

        self.__icx_storage = icx_storage
        self.__icon_score_info_mapper = icon_score_info_mapper

    def invoke(self,
               context: 'IconScoreContext',
               icon_score_address: 'Address',
               data_type: str,
               data: dict) -> None:
        """Handle calldata contained in icx_sendTransaction message

        :param icon_score_address:
        :param context:
        :param data_type:
        :param data: calldata
        """
        if data_type == 'call':
            self._call(context, icon_score_address, data)
        else:
            self._fallback(context, icon_score_address)

    def query(self,
              context: IconScoreContext,
              icon_score_address: Address,
              data_type: str,
              data: dict) -> object:
        """Execute an external method of SCORE without state changing

        Handles messagecall of icx_call
        """
        if data_type == 'call':
            return self._call(context, icon_score_address, data)
        else:
            raise InvalidParamsException(f'Invalid dataType: ({data_type})')

    def get_score_api(self,
                      context: 'IconScoreContext',
                      icon_score_address: 'Address') -> object:
        """Handle get score api

        :param context:
        :param icon_score_address:
        """

        icon_score = self._get_icon_score(context, icon_score_address)
        return icon_score.get_api()

    def _call(self,
              context: 'IconScoreContext',
              icon_score_address: 'Address',
              data: dict) -> object:
        """Handle jsonrpc including both invoke and query

        :param context:
        :param icon_score_address:
        :param data: data to call the method of score
        """
        method: str = data['method']
        kw_params: dict = data['params']

        icon_score = self._get_icon_score(context, icon_score_address)

        try:
            self._put_context(context)
            return call_method(icon_score=icon_score, func_name=method, kw_params=kw_params)
        finally:
            self._delete_context(context)

    def _fallback(self,
                  context: 'IconScoreContext',
                  icon_score_address: 'Address'):
        """When an IconScore receives some coins and calldata is None,
        fallback function is called.

        :param icon_score_address:
        """

        icon_score = self._get_icon_score(context, icon_score_address)

        try:
            self._put_context(context)
            call_fallback(icon_score)
        finally:
            self._delete_context(context)

    def _get_icon_score(self, context: 'IconScoreContext',icon_score_address: 'Address'):
        icon_score = self.__icon_score_info_mapper.get_icon_score(context, icon_score_address)
        if icon_score is None:
            raise ServerErrorException(
                f'SCORE not found: {icon_score_address}')
        return icon_score

    def commit(self, context: 'IconScoreContext') -> None:
        """It is called when the previous block has been confirmed
        """
        pass

    def rollback(self) -> None:
        """It is called when the previous block has been canceled

        Rollback install, update or remove tasks cached in the previous block
        """
        pass
