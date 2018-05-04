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

from ..database.factory import DatabaseFactory
from ..iconscore.icon_score_context import ContextGetter
from ..iconscore.icon_score_loader import IconScoreLoader
from ..icx.icx_storage import IcxStorage
from ..base.address import Address
from ..base.exception import ExceptionCode, IconException, IconScoreBaseException

from typing import TYPE_CHECKING, Optional
if TYPE_CHECKING:
    from .icon_score_base import IconScoreBase
    from ..database.db import IconScoreDatabase


class IconScoreInfo(object):
    """Contains information on one icon score

    If this class is not necessary anymore, Remove it
    """
    def __init__(self, icon_score: 'IconScoreBase') -> None:
        """Constructor

        :param icon_score: icon score object
        """
        self._icon_score = icon_score

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
        return self._icon_score.owner


class IconScoreInfoMapper(dict, ContextGetter):
    """Icon score information mapping table

    This instance should be used as a singletone

    key: icon_score_address
    value: IconScoreInfo
    """
    def __init__(self, storage: IcxStorage, db_factory: DatabaseFactory, icon_score_loader: IconScoreLoader) -> None:
        """Constructor
        """
        self.__icx_storage = storage
        self.__db_factory = db_factory
        self.__icon_score_loader = icon_score_loader

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

    @staticmethod
    def __check_key_type(address: Address) -> None:
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

    @staticmethod
    def __check_value_type(info: IconScoreInfo) -> None:
        if not isinstance(info, IconScoreInfo):
            raise IconException(
                ExceptionCode.INVALID_PARAMS,
                f'{info} is not IconScoreInfo type.')

    def get_icon_score(self, address: Address) -> Optional[IconScoreBase]:
        """
        :param address:
        :return: IconScoreBase object
        """

        icon_score_info = self.get(address)
        if icon_score_info is None:
            if self.__db_factory.is_exist(address):
                icon_score_info = self.__load_score(address)

        if icon_score_info is None:
            return None

        icon_score = icon_score_info.icon_score
        return icon_score

    def __load_score(self, address: Address) -> Optional[IconScoreInfo]:
        score_wrapper = self.__load_score_wrapper(address)
        score_db = self.__create_icon_score_database(address)

        owner = self.__icx_storage.get_score_owner(self._context, address)
        if owner is None:
            return None

        icon_score = score_wrapper(score_db, owner=owner)
        return self.__add_score_to_mapper(icon_score)

    def __create_icon_score_database(self, address: Address) -> 'IconScoreDatabase':
        """Create IconScoreDatabase instance
        with icon_score_address and ContextDatabase

        :param address: icon_score_address
        """

        context_db = self.__db_factory.create_by_address(address)
        score_db = IconScoreDatabase(context_db)
        return score_db

    def __load_score_wrapper(self, address: Address) -> callable:
        """Load IconScoreBase subclass from IconScore python package

        :param address: icon_score_address
        :return: IconScoreBase subclass (NOT instance)
        """

        score_wrapper = self.__icon_score_loader.load_score(address.body.hex())
        if score_wrapper is None:
            raise IconScoreBaseException(f'score_wrapper load Fail {address}')
        return score_wrapper

    def __add_score_to_mapper(self, icon_score) -> IconScoreInfo:
        info = IconScoreInfo(icon_score)
        self[icon_score.address] = info
        return info
