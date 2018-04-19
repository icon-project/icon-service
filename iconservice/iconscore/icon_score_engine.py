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


from .icon_score_context import IconScoreContext
from .icon_score_info_mapper import IconScoreInfoMapper
from ..base.address import Address, AddressPrefix
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
    """Multiple IconScore management

    Managed items
    - Context
    - DB
    - IconScore
    """

    def __init__(self, icon_score_info_mapper: IconScoreInfoMapper) -> None:
        """Constructor
        """
        self.__icon_score_info_mapper = icon_score_info_mapper

    def invoke(self,
               icon_score_address: Address,
               method: str,
               params: dict) -> bool:
        """
        """
        icon_score_info = self.__icon_score_info_mapper.get(icon_score_address)
        return call_icon_score_method(
            icon_score_info.icon_score,
            icon_score_info.icon_score_context,
            method,
            params)

    def query(self,
              icon_score_address: Address,
              method: str,
              params: dict) -> object:
        """
        """
        icon_score_info = self.__icon_score_info_mapper.get(icon_score_address)
        return call_icon_score_method(
            icon_score_info.icon_score,
            icon_score_info.icon_score_context,
            method,
            params)
