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


from ..base.address import Address
from ..iconscore.icon_score_info_mapper import IconScoreInfoMapper
from .block_batch import BlockBatch


class ReadOnlyContextDatabase(object):
    """ReadonlyDatabase used by IconScore

    DB writing is not allowed.
    """
    def __init__(self,
                 icon_score_address: Address,
                 icon_score_info_mapper: IconScoreInfoMapper) -> None:
        """Constructor

        :param icon_score_address: the current icon score address which 
        :param icon_score_info_mapper: To get state db for an icon score
        """
        self.icon_score_address = icon_score_address
        self.__icon_score_info_mapper = icon_score_info_mapper

    def get(self, key: bytes) -> bytes:
        """
        :param key:
        """
        info = self.__icon_score_info_mapper[self.icon_score_address]
        return info.db.get(key)

    def put(self, key: bytes, value: bytes) -> None:
        """DB writing is not allowed on readonly mode.

        :param key:
        :param value:
        """
        raise RuntimeError('Updating state is not allowed.')


class ContextDatabase(object):
    """Database used by IconScore

    This db will be provided to IconScore made by 3-party.
    """
    def __init__(self,
                 icon_score_address: Address,
                 icon_score_info_mapper: IconScoreInfoMapper) -> None:
        """Constructor

        :param icon_score_address: the current icon score address which 
        :param icon_score_info_mapper: To get state db for an icon score
        """
        self.icon_score_address = icon_score_address
        self.__icon_score_info_mapper = icon_score_info_mapper

    def get(self, key: bytes) -> bytes:
        """
        """

    def put(self, key: bytes, value: bytes):
        """
        """

    def commit(self) -> None:
        """
        """

    def rollback(self) -> None:
        """
        """
