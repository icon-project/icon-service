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
import os
from shutil import rmtree
from threading import Lock
from typing import TYPE_CHECKING, Optional

from iconcommons.logger import Logger
from ..base.address import Address, GOVERNANCE_SCORE_ADDRESS
from ..base.exception import InvalidParamsException, ServerErrorException
from ..database.db import IconScoreDatabase
from ..database.factory import ContextDatabaseFactory
from ..deploy import DeployState
from ..deploy.icon_score_deploy_engine import IconScoreDeployStorage

if TYPE_CHECKING:
    from .icon_score_base import IconScoreBase
    from .icon_score_context import IconScoreContext
    from .icon_score_loader import IconScoreLoader


class IconScoreInfo(object):
    """Contains information on one icon score

    If this class is not necessary anymore, Remove it
    """

    def __init__(self, icon_score: 'IconScoreBase', score_id: str) -> None:
        """Constructor

        :param icon_score: icon score object
        """
        self._icon_score = icon_score
        self._score_id = score_id

    @property
    def address(self) -> 'Address':
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
    def owner(self) -> 'Address':
        """The address of user who creates a tx for installing this icon_score
        """
        return self._icon_score.owner

    @property
    def score_id(self) -> str:
        return self._score_id


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


class IconScoreInfoMapper(object):
    """Icon score information mapping table

    This instance should be used as a singletone

    key: icon_score_address
    value: IconScoreInfo
    """

    def __init__(self,
                 icon_score_loader: 'IconScoreLoader',
                 deploy_storage: 'IconScoreDeployStorage') -> None:
        """Constructor
        """

        self._icon_score_loader = icon_score_loader
        self._deploy_storage = deploy_storage

        self._lock = Lock()
        self._wait_score_mapper = IconScoreMapperObject()
        self._score_mapper = IconScoreMapperObject()
        self._wait_score_remove_table = dict()

    def __contains__(self, item):
        with self._lock:
            is_in_score_mapper = item in self._score_mapper

        is_in_wait_mapper = item in self._wait_score_mapper
        return is_in_score_mapper or is_in_wait_mapper

    def __len__(self):
        with self._lock:
            return len(self._score_mapper)

    def __getitem__(self, address: 'Address') -> 'IconScoreInfo':
        with self._lock:
            return self._score_mapper[address]

    def __setitem__(self, address: 'Address', info: 'IconScoreInfo') -> None:
        with self._lock:
            self._score_mapper[address] = info

    def __delitem__(self, address: 'Address') -> None:
        with self._lock:
            del self._score_mapper[address]

    def get(self, address: 'Address') -> 'IconScoreInfo':
        with self._lock:
            return self._score_mapper.get(address)

    def close(self):
        for score_address, info in self._score_mapper.items():
            info.icon_score.db.close()
        for score_address, info in self._wait_score_mapper.items():
            info.icon_score.db.close()

    def commit(self):
        for address, info in self._wait_score_mapper.items():
            self._score_mapper[address] = info
            self._deploy_storage.put_deploy_state_info(None, address, DeployState.ACTIVE, info.score_id)
        self._wait_score_mapper.clear()
        self._wait_score_remove_table.clear()

    def rollback(self):
        for info in list(self._wait_score_remove_table.values()):
            address, score_id = info
            self._remove_score_dir(address, score_id)
        self._wait_score_mapper.clear()
        self._wait_score_remove_table.clear()

    def _remove_score_dir(self, address: 'Address', score_id: str):
        target_path = os.path.join(self.score_root_path, address.to_bytes().hex(), score_id)
        try:
            rmtree(target_path)
        except Exception as e:
            Logger.warning(e)

    @property
    def score_root_path(self) -> str:
        return self._icon_score_loader.score_root_path

    def get_icon_score(self, context: 'IconScoreContext', address: 'Address') -> Optional['IconScoreBase']:
        """
        :param context:
        :param address:
        :return: IconScoreBase object
        """

        self._validate_blacklist(address)

        icon_score_info = self.get(address)
        is_score_active = self._deploy_storage.is_score_active(context, address)
        score_id = self._deploy_storage.get_score_id(context, address)
        if score_id is None:
            raise InvalidParamsException(f'score_id is None {address}')

        if is_score_active and icon_score_info is None:
            icon_score_info = self._load_score(address, score_id)

        if icon_score_info is None:
            if is_score_active:
                raise InvalidParamsException(
                    f'icon_score_info is None: {address}')
            else:
                raise InvalidParamsException(
                    f'is_score_active is False: {address}')

        icon_score = icon_score_info.icon_score
        return icon_score

    def _validate_blacklist(self, address: 'Address'):
        governance_info = self.get(GOVERNANCE_SCORE_ADDRESS)
        if governance_info and governance_info.icon_score.isInBlackList(address):
                raise ServerErrorException(f'The Score is in Black List (address: {address})')

    def load_wait_icon_score(self,
                             address: 'Address',
                             score_id: str) -> Optional['IconScoreBase']:
        """
        :param address:
        :param score_id:
        :return: IconScoreBase object
        """
        icon_score_info = self._load_score(address, score_id)
        icon_score = icon_score_info.icon_score
        return icon_score

    def _load_score(self, address: 'Address', score_id) -> Optional['IconScoreInfo']:
        self._wait_score_remove_table[address] = (address, score_id)
        score_wrapper = self._load_score_wrapper(address, score_id)
        score_db = self._create_icon_score_database(address)
        icon_score = score_wrapper(score_db)
        return self._add_score_to_mapper(icon_score, score_id)

    @staticmethod
    def _create_icon_score_database(address: 'Address') -> 'IconScoreDatabase':
        """Create IconScoreDatabase instance
        with icon_score_address and ContextDatabase

        :param address: icon_score_address
        """

        context_db = ContextDatabaseFactory.create_by_address(address)
        score_db = IconScoreDatabase(address, context_db)
        return score_db

    def _load_score_wrapper(self, address: 'Address', score_id: str) -> callable:
        """Load IconScoreBase subclass from IconScore python package

        :param address: icon_score_address
        :return: IconScoreBase subclass (NOT instance)
        """

        score_wrapper = self._icon_score_loader.load_score(address.to_bytes().hex(), score_id)
        if score_wrapper is None:
            raise InvalidParamsException(f'score_wrapper load Fail {address}')
        return score_wrapper

    def _add_score_to_mapper(self, icon_score: 'IconScoreBase', score_id: str) -> 'IconScoreInfo':
        info = IconScoreInfo(icon_score, score_id)
        self._wait_score_mapper[icon_score.address] = info
        return info

    def delete_wait_score_mapper(self, score_address: 'Address', score_id: str):
        if score_address in self._wait_score_remove_table:
            del self._wait_score_remove_table[score_address]
        if score_address in self._wait_score_mapper:
            del self._wait_score_mapper[score_address]
        self._remove_score_dir(score_address, score_id)


