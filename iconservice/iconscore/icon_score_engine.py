# -*- coding: utf-8 -*-

# Copyright 2018 ICON Foundation
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

from typing import TYPE_CHECKING, Any

from .icon_score_constant import STR_FALLBACK
from .icon_score_context import IconScoreContext
from .icon_score_context_util import IconScoreContextUtil
from ..base.address import Address, ZERO_SCORE_ADDRESS
from ..base.exception import InvalidParamsException, ServerErrorException
from ..base.type_converter import TypeConverter

if TYPE_CHECKING:
    from ..iconscore.icon_score_base import IconScoreBase


class IconScoreEngine(object):
    """Calls external functions provided by each IconScore
    """

    @staticmethod
    def invoke(context: 'IconScoreContext',
               icon_score_address: 'Address',
               data_type: str,
               data: dict) -> None:
        """Handle calldata contained in icx_sendTransaction message

        :param icon_score_address:
        :param context:
        :param data_type:
        :param data: calldata
        """
        IconScoreEngine._validate_score_blacklist(context, icon_score_address)

        if data_type == 'call':
            IconScoreEngine._call(context, icon_score_address, data)
        else:
            IconScoreEngine._fallback(context, icon_score_address)

    @staticmethod
    def query(context: IconScoreContext,
              icon_score_address: Address,
              data_type: str,
              data: dict) -> object:
        """Execute an external method of SCORE without state changing

        Handles messagecall of icx_call
        """
        IconScoreEngine._validate_score_blacklist(context, icon_score_address)

        if data_type == 'call':
            return IconScoreEngine._call(context, icon_score_address, data)
        else:
            raise InvalidParamsException(f'Invalid dataType: ({data_type})')

    @staticmethod
    def get_score_api(context: 'IconScoreContext', icon_score_address: 'Address') -> object:
        """Handle get score api

        :param context:
        :param icon_score_address:
        """
        IconScoreEngine._validate_score_blacklist(context, icon_score_address)

        icon_score = IconScoreEngine._get_icon_score(context, icon_score_address)
        return icon_score.get_api()

    @staticmethod
    def _validate_score_blacklist(context: 'IconScoreContext', icon_score_address: 'Address'):
        if icon_score_address is None or \
                icon_score_address is ZERO_SCORE_ADDRESS or \
                not icon_score_address.is_contract:
            raise InvalidParamsException(f"Invalid score address: ({icon_score_address})")

        IconScoreContextUtil.validate_score_blacklist(context, icon_score_address)

    @staticmethod
    def _call(context: 'IconScoreContext',
              icon_score_address: 'Address',
              data: dict) -> Any:
        """Handle jsonrpc including both invoke and query

        :param context:
        :param icon_score_address:
        :param data: data to call the method of score
        """
        func_name: str = data['method']
        kw_params: dict = data.get('params', {})

        icon_score = IconScoreEngine._get_icon_score(context, icon_score_address)

        converted_params = IconScoreEngine._convert_score_params_by_annotations(icon_score, func_name, kw_params)
        context.set_func_type_by_icon_score(icon_score, func_name)

        score_func = getattr(icon_score, '_IconScoreBase__call')
        return score_func(func_name=func_name, kw_params=converted_params)

    @staticmethod
    def _convert_score_params_by_annotations(icon_score: 'IconScoreBase', func_name: str, kw_params: dict) -> dict:
        tmp_params = kw_params

        icon_score.validate_external_method(func_name)

        score_func = getattr(icon_score, func_name)
        annotation_params = TypeConverter.make_annotations_from_method(score_func)
        TypeConverter.convert_data_params(annotation_params, tmp_params)
        return tmp_params

    @staticmethod
    def _fallback(context: 'IconScoreContext',
                  score_address: 'Address'):
        """When an IconScore receives some coins and calldata is None,
        fallback function is called.

        :param score_address:
        """
        icon_score = IconScoreEngine._get_icon_score(context, score_address)

        score_func = getattr(icon_score, '_IconScoreBase__call')
        score_func(STR_FALLBACK)

    @staticmethod
    def _get_icon_score(context: 'IconScoreContext', icon_score_address: 'Address'):
        icon_score = IconScoreContextUtil.get_icon_score(context, icon_score_address)
        if icon_score is None:
            raise InvalidParamsException(
                f'SCORE not found: {icon_score_address}')
        return icon_score
