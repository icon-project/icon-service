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
from ..database.factory import DatabaseFactory

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .icon_score_base import IconScoreBase


class IconScoreInfo(object):
    """Contains information on one icon score
    """
    _db_factory = None

    def __init__(self,
                 icon_score: object,
                 owner: Address,
                 icon_score_address: Address,
                 db: object=None) -> None:
        """Constructor

        :param icon_score: icon score object
        :param owner:
            the address of user
            who creates a tx for installing this icon_score
        :param icon_score_address: contract address
        :param db: state db for an icon score
        """
        self._icon_score = None
        self._readonly_icon_score = None
        self._icon_score_address = icon_score_address
        self._owner = owner
        self._db = db

    @classmethod
    def set_db_factory(cls, db_factory: DatabaseFactory) -> None:
        """DatabaseFactory will be shared among all IconScoreInfo instances

        :param db_factory: state_db creator
        """
        cls._db_factory = db_factory

    @property
    def icon_score_address(self) -> Address:
        """Icon score address
        """
        return self._icon_score_address

    def get_icon_score(self, readonly) -> 'IconScoreBase':
        """Returns IconScoreBase object

        If IconScoreBase object is None, Create it here.
        """
        if readonly:
            return self._readonly_icon_score
        else:
            return self._icon_score

    @property
    def owner(self) -> Address:
        """The address of user who creates a tx for installing this icon_score
        """
        return self._owner

    @property
    def db(self) -> object:
        """State db for icon score
        """
        if self._db is None or self._db.closed:
            self._db = self._db_factory.create_by_address(
                self._icon_score_address)

        return self._db


class IconScoreInfoMapper(dict):
    """Icon score information mapping table

    key: icon_score_address
    value: IconScoreInfo
    """
    def __init__(self):
        """Constructor
        """

    def __getitem__(self, icon_score_address: Address) -> IconScoreInfo:
        """
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
            raise KeyError(f'{address} is not Address type.')
        if address.prefix != AddressPrefix.CONTRACT:
            raise KeyError(f'{address} is not an icon score address.')

    def __check_value_type(self, info: IconScoreInfo) -> None:
        if not isinstance(info, IconScoreInfo):
            raise ValueError(f'{info} is not IconScoreInfo type.')
