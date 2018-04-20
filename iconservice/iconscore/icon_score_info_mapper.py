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


class IconScoreInfo(object):
    """Contains information on one icon score
    """
    __db_factory = None

    def __init__(self,
                 icon_score: object,
                 owner: Address,
                 icon_score_address: Address,
                 db: object=None) -> None:
        """Constructor

        :param icon_score: icon score object
        :param owner: icon score uploader address
        :param icon_score_address: contract address
        :param db: state db for an icon score
        """
        self.__icon_score = icon_score
        self.__icon_score_address = icon_score_address
        self.__owner = owner
        self.__db = db

    @property
    def icon_score_address(self) -> Address:
        """Icon score address
        """
        return self.__icon_score_address

    @property
    def icon_score(self) -> object:
        """Icon score object
        """
        return self.__icon_score

    @property
    def owner(self) -> Address:
        """Icon score uploader address
        """
        return self.__owner

    @property
    def db(self) -> object:
        """State db for icon score
        """
        if self.__db is None or self.__db.closed:
            self.__db = self.__db_factory.create_by_address(
                self.__icon_score_address)

        return self.__db

    @classmethod
    def set_db_factory(cls, db_factory: DatabaseFactory) -> None:
        cls.__db_factory = db_factory


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
