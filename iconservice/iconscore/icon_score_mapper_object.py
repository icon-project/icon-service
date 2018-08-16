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

from .icon_score_base import IconScoreBase
from ..base.address import Address
from ..base.exception import InvalidParamsException


class IconScoreInfo(object):
    """Contains information on one icon score

    If this class is not necessary anymore, Remove it
    """

    def __init__(self, icon_score: 'IconScoreBase', tx_hash: bytes) -> None:
        """Constructor

        :param icon_score: icon score object
        """
        self._check_icon_score(icon_score)
        self._icon_score = icon_score
        self._tx_hash = tx_hash

    @property
    def icon_score(self) -> 'IconScoreBase':
        """Returns IconScoreBase object

        If IconScoreBase object is None, Create it here.
        """
        return self._icon_score

    @property
    def tx_hash(self) -> bytes:
        return self._tx_hash

    @staticmethod
    def _check_icon_score(icon_score: 'IconScoreBase') -> None:
        """Check if key type is an icon score address type or not.

        :param icon_score: icon score base
        """
        if not isinstance(icon_score, IconScoreBase):
            raise InvalidParamsException("score is not child from IconScoreBase")


class IconScoreMapperObject(dict):
    def __getitem__(self, key: 'Address') -> 'IconScoreInfo':
        """operator[] overriding

        :param key:
        :return: IconScoreInfo instance
        """
        self._check_key_type(key)
        return super().__getitem__(key)

    def __setitem__(self,
                    key: 'Address',
                    value: 'IconScoreInfo') -> None:
        """
        :param key:
        :param value: IconScoreInfo
        """
        self._check_key_type(key)
        self._check_value_type(value)
        super().__setitem__(key, value)

    @staticmethod
    def _check_key_type(address: 'Address') -> None:
        """Check if key type is an icon score address type or not.

        :param address: icon score address
        """
        if not isinstance(address, Address):
            raise InvalidParamsException(
                f'{address} is an invalid address')
        if not address.is_contract:
            raise InvalidParamsException(
                f'{address} is not an icon score address.')

    @staticmethod
    def _check_value_type(info: IconScoreInfo) -> None:
        if not isinstance(info, IconScoreInfo):
            raise InvalidParamsException(
                f'{info} is not IconScoreInfo type.')
