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

from typing import TYPE_CHECKING

from ..base.address import Address
from ..base.exception import InvalidParamsException
from ..icon_constant import Revision
from ..utils import is_builtin_score

if TYPE_CHECKING:
    from .icon_score_base import IconScoreBase
    from ..database.db import IconScoreDatabase


class IconScoreInfo(object):
    """Contains information on one icon score

    If this class is not necessary anymore, Remove it
    """

    def __init__(self, score_class: type, score_db: 'IconScoreDatabase', tx_hash: bytes) -> None:
        """Constructor

        :param score_class:
        :param score_db:
        :param tx_hash:
        """
        self._tx_hash = tx_hash
        self._score_class = score_class
        self._score_db = score_db
        self._score = None

    @property
    def tx_hash(self) -> bytes:
        return self._tx_hash

    @property
    def score_class(self) -> type:
        return self._score_class

    @property
    def score_db(self) -> 'IconScoreDatabase':
        return self._score_db

    @property
    def address(self) -> 'Address':
        return self._score_db.address

    def get_score(self, revision: int) -> 'IconScoreBase':
        """Provide a score instance according to the revision.
        1. revision <= 2: Returns a cached score instance
        2. revision > 2: Returns a newly created score instance

        :param revision:
        :return:
        """
        if revision <= Revision.TWO.value or is_builtin_score(str(self.address)):
            if self._score is None:
                self._score = self.create_score()

            return self._score

        return self.create_score()

    def create_score(self) -> 'IconScoreBase':
        return self._score_class(self._score_db)


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
    def _check_value_type(info: 'IconScoreInfo') -> None:
        if not isinstance(info, IconScoreInfo):
            raise InvalidParamsException(
                f'{info} is not IconScoreInfo type.')
