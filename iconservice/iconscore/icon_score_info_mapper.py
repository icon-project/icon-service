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


from ..base.address import Address, AddressPrefix
from ..base.exception import ExceptionCode, IconException

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .icon_score_base import IconScoreBase


class IconScoreInfo(object):
    """Contains information on one icon score
    """
    def __init__(self,
                 icon_score: 'IconScoreBase',
                 owner: Address) -> None:
        """Constructor

        :param icon_score: icon score object
        :param owner:
            the address of user
            who creates a tx for installing this icon_score
        :param icon_score_address: contract address
        """
        self._icon_score = icon_score
        self._owner = owner

    @property
    def address(self) -> Address:
        """Icon score address
        """
        return self._icon_score.address

    @property
    def icon_score(self) -> 'IconScoreBase':
        """Returns IconScoreBase object

        If IconScoreBase object is None, Create it here.
        """
        return self._icon_score

    @property
    def owner(self) -> Address:
        """The address of user who creates a tx for installing this icon_score
        """
        return self._owner


class IconScoreInfoMapper(dict):
    """Icon score information mapping table

    This instance should be used as a singletone

    key: icon_score_address
    value: IconScoreInfo
    """
    def __init__(self) -> None:
        """Constructor
        """

    def __getitem__(self, icon_score_address: Address) -> IconScoreInfo:
        """operator[] overriding

        :param icon_score_address:
        :return: IconScoreInfo instance
        """
        self.__check_key_type(icon_score_address)
        return super().__getitem__(icon_score_address)

    def __setitem__(self,
                    icon_score_address: Address,
                    info: IconScoreInfo) -> None:
        """
        :param icon_score_address:
        :param info: IconScoreInfo
        """
        self.__check_key_type(icon_score_address)
        self.__check_value_type(info)
        super().__setitem__(icon_score_address, info)

    def __check_key_type(self, address: Address) -> None:
        """Check if key type is an icon score address type or not.

        :param address: icon score address
        """
        if not isinstance(address, Address):
            raise IconException(
                ExceptionCode.INVALID_PARAMS,
                f'{address} is an invalid address')
        if not address.is_contract:
            raise IconException(
                ExceptionCode.INVALID_PARAMS,
                f'{address} is not an icon score address.')

    def __check_value_type(self, info: IconScoreInfo) -> None:
        if not isinstance(info, IconScoreInfo):
            raise IconException(
                ExceptionCode.INVALID_PARAMS,
                f'{info} is not IconScoreInfo type.')
