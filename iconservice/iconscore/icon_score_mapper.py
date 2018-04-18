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


class IconScoreInfo(object):
    """Contains information on one icon score
    """

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
        return self.__db


class IconScoreMapper(object):
    """Icon score information mapping table

    key: icon_score_address
    value: IconScoreInfo
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
            info: IconScoreInfo) -> None:
        """
        :param icon_score_address:
        :param info: IconScoreInfo
        """
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
