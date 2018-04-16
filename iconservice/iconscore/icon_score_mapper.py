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


from .. base.address import Address, AddressPrefix
from .icon_score_base import IconScoreBase
from .icon_score_context import IconScoreContext


class IconScoreInfo(object):
    """Contains information on an icon score managed in IconScoreStorage
    """

    def __init__(self,
                 icon_score: object,
                 owner: Address,
                 icon_score_address: Address,
                 db: object=None) -> None:
        """Constructor

        :param icon_score:
        :param owner:
        :param icon_score_address:
        :
        """
        self.__icon_score = icon_score
        self.__icon_score_address = icon_score_address
        self.__owner = owner
        self.__db = db

    @property
    def icon_score_address(self) -> Address:
        return self.__icon_score_address

    @property
    def icon_score(self) -> IconScoreBase:
        return self.__icon_score

    @property
    def owner(self) -> Address:
        return self.__owner

    @property
    def db(self) -> object:
        """State db for icon score
        """
        return self.__db


class IconScoreMapper(object):
    """Manages IconScore objects
    """
    def __init__(self):
        """Constructor
        """
        self.__icon_score_infos = {}

    def get(self, icon_score_address: Address) -> IconScoreInfo:
        """
        """
        if icon_score_address in self.__icon_score_infos:
            return self.__icon_score_infos[icon_score_address]
        else:
            return None

    def put(self,
            icon_score_address: Address,
            icon_score: IconScoreBase,
            owner: Address) -> None:
        """
        """
        info = self.get(icon_score_address)
        if info is None:
            info = IconScoreInfo(icon_score_address, icon_score, owner)
            self.__icon_score_infos[icon_score_address] = info

    def delete(self, icon_score_address: Address):
        """Delete icon score from mapper

        :param icon_score_address:
        """
        if icon_score_address in self.__icon_score_infos:
            del self.__icon_score_infos[icon_score_address]

    def contains(self, icon_score_address: Address) -> bool:
        """Check if the icon score indicated by address is present or not.

        :param icon_score_address: icon score address
        :return:
        """
        return icon_score_address.prefix == AddressPrefix.CONTRACT and \
            icon_score_address in self.__icon_score_infos
