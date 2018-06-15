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

from ..iconscore.icon_score_context import ContextGetter
from ..iconscore.icon_score_loader import IconScoreLoader
from ..icx.icx_storage import IcxStorage
from ..base.address import Address
from ..base.exception import ExceptionCode, IconScoreException
from ..database.db import IconScoreDatabase

from typing import TYPE_CHECKING, Optional
if TYPE_CHECKING:
    from .icon_score_base import IconScoreBase
    from ..database.factory import DatabaseFactory


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
    def __init__(self, storage: IcxStorage, db_factory: 'DatabaseFactory',
                 icon_score_loader: IconScoreLoader) -> None:
        """Constructor
        """
        super().__init__()
        self._icx_storage = storage
        self._db_factory = db_factory
        self._icon_score_loader = icon_score_loader

    def __getitem__(self, icon_score_address: Address) -> IconScoreInfo:
        """operator[] overriding

        :param icon_score_address:
        :return: IconScoreInfo instance
        """
        self._check_key_type(icon_score_address)
        return super().__getitem__(icon_score_address)

    def __setitem__(self,
                    icon_score_address: Address,
                    info: IconScoreInfo) -> None:
        """
        :param icon_score_address:
        :param info: IconScoreInfo
        """
        self._check_key_type(icon_score_address)
        self._check_value_type(info)
        super().__setitem__(icon_score_address, info)

    @staticmethod
    def _check_key_type(address: Address) -> None:
        """Check if key type is an icon score address type or not.

        :param address: icon score address
        """
        if not isinstance(address, Address):
            raise IconScoreException(
                f'{address} is an invalid address',
                ExceptionCode.INVALID_PARAMS)
        if not address.is_contract:
            raise IconScoreException(
                f'{address} is not an icon score address.',
                ExceptionCode.INVALID_PARAMS)

    @staticmethod
    def _check_value_type(info: IconScoreInfo) -> None:
        if not isinstance(info, IconScoreInfo):
            raise IconScoreException(
                f'{info} is not IconScoreInfo type.',
                ExceptionCode.INVALID_PARAMS)

    @property
    def score_root_path(self):
        return self._icon_score_loader.score_root_path

    def delete_icon_score(self, address: Address) -> None:
        """
        :param address:
        """
        if address in self:
            icon_score = self[address].icon_score
            if icon_score is not None:
                icon_score.db._context_db.close(self._context)
            del self[address]

    def get_icon_score(self, address: Address) -> Optional['IconScoreBase']:
        """
        :param address:
        :return: IconScoreBase object
        """

        icon_score_info = self.get(address)
        if icon_score_info is None:
            icon_score_info = self.__load_score(address)

        if icon_score_info is None:
            return None

        icon_score = icon_score_info.icon_score
        return icon_score

    def __load_score(self, address: 'Address') -> Optional['IconScoreInfo']:
        owner = self._icx_storage.get_score_owner(self._context, address)
        if owner is None:
            return None

        score_wrapper = self._load_score_wrapper(address)
        score_db = self._create_icon_score_database(address)

        icon_score = score_wrapper(score_db, owner)
        return self._add_score_to_mapper(icon_score)

    def _create_icon_score_database(self, address: Address) -> 'IconScoreDatabase':
        """Create IconScoreDatabase instance
        with icon_score_address and ContextDatabase

        :param address: icon_score_address
        """

        context_db = self._db_factory.create_by_address(address)
        score_db = IconScoreDatabase(context_db)
        return score_db

    def _load_score_wrapper(self, address: 'Address') -> callable:
        """Load IconScoreBase subclass from IconScore python package

        :param address: icon_score_address
        :return: IconScoreBase subclass (NOT instance)
        """

        score_wrapper = self._icon_score_loader.load_score(address.body.hex())
        if score_wrapper is None:
            raise IconScoreException(f'score_wrapper load Fail {address}')
        return score_wrapper

    def _add_score_to_mapper(self, icon_score) -> IconScoreInfo:
        info = IconScoreInfo(icon_score)
        self[icon_score.address] = info
        return info

    def is_exist_db(self, address: 'Address') -> bool:
        return self._db_factory.is_exist(address)

