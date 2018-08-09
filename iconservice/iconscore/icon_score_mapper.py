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
from typing import TYPE_CHECKING, Optional
from threading import Lock

from iconcommons import Logger
from ..icon_constant import DEFAULT_BYTE_SIZE
from ..base.address import Address
from ..base.exception import InvalidParamsException
from ..database.db import IconScoreDatabase
from ..database.factory import ContextDatabaseFactory
from ..deploy.icon_score_deploy_engine import IconScoreDeployStorage
from .icon_score_base import IconScoreBase

if TYPE_CHECKING:
    from .icon_score_context import IconScoreContext
    from .icon_score_loader import IconScoreLoader


class IconScoreInfo(object):
    """Contains information on one icon score

    If this class is not necessary anymore, Remove it
    """

    def __init__(self, icon_score: 'IconScoreBase', tx_hash: bytes) -> None:
        """Constructor

        :param icon_score: icon score object
        """
        self._icon_score = icon_score
        self._tx_hash = tx_hash

    @property
    def icon_score(self) -> 'IconScoreBase':
        """Returns IconScoreBase object

        If IconScoreBase object is None, Create it here.
        """
        return self._icon_score

    @property
    def tx_hash(self) -> bytes:
        return self._tx_hash


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


class IconScoreMapper(object):
    """Icon score information mapping table

    This instance should be used as a singletone

    key: icon_score_address
    value: IconScoreInfo
    """

    icon_score_loader: 'IconScoreLoader' = None
    deploy_storage: 'IconScoreDeployStorage' = None

    def __init__(self, is_lock: bool = False) -> None:
        """Constructor
        """
        self.score_mapper = IconScoreMapperObject()
        self._lock = Lock()
        self._is_lock = is_lock

    def __contains__(self, item):
        if self._is_lock:
            with self._lock:
                return item in self.score_mapper
        else:
            return item in self.score_mapper

    def __setitem__(self, key, value):
        if self._is_lock:
            with self._lock:
                self.score_mapper[key] = value
        else:
            self.score_mapper[key] = value

    def get(self, key):
        if self._is_lock:
            with self._lock:
                return self.score_mapper.get(key)
        else:
            return self.score_mapper.get(key)

    def update(self, mapper: 'IconScoreMapper'):
        if self._is_lock:
            with self._lock:
                self.score_mapper.update(mapper.score_mapper)
        else:
            self.score_mapper.update(mapper.score_mapper)

    def close(self):
        for addr, info in self.score_mapper.items():
            info.icon_score.db.close()

    @property
    def score_root_path(self) -> str:
        return self.icon_score_loader.score_root_path

    def get_icon_score(self, context: 'IconScoreContext', address: 'Address') -> Optional['IconScoreBase']:
        """
        :param context:
        :param address:
        :return: IconScoreBase object
        """
        icon_score_info = self.score_mapper.get(address)
        is_score_active = self.deploy_storage.is_score_active(context, address)
        tx_hash = self.deploy_storage.get_current_tx_hash(context, address)
        if tx_hash is None:
            raise InvalidParamsException(f'tx_hash is None {address}')

        if is_score_active and icon_score_info is None:
            score = self._load_score(address, tx_hash)
            icon_score_info = IconScoreInfo(score, tx_hash)

        if icon_score_info is None:
            if is_score_active:
                raise InvalidParamsException(
                    f'icon_score_info is None: {address}')
            else:
                raise InvalidParamsException(
                    f'is_score_active is False: {address}')

        icon_score = icon_score_info.icon_score
        return icon_score

    def load_icon_score(self,
                        address: 'Address',
                        tx_hash: bytes) -> Optional['IconScoreBase']:
        """
        :param address:
        :param tx_hash:
        :return: IconScoreBase object
        """

        return self._load_score(address, tx_hash)

    def put_icon_info(self,
                      address: 'Address',
                      icon_score: 'IconScoreBase',
                      tx_hash: bytes):
        self.score_mapper[address] = IconScoreInfo(icon_score, tx_hash)

    def _load_score(self, address: 'Address', tx_hash: bytes) -> Optional['IconScoreBase']:
        score_wrapper = self._load_score_wrapper(address, tx_hash)
        score_db = self._create_icon_score_database(address)
        score = score_wrapper(score_db)
        if not isinstance(score, IconScoreBase):
            raise InvalidParamsException("score is not child from IconScoreBase")
        return score

    @staticmethod
    def _create_icon_score_database(address: 'Address') -> 'IconScoreDatabase':
        """Create IconScoreDatabase instance
        with icon_score_address and ContextDatabase

        :param address: icon_score_address
        """

        context_db = ContextDatabaseFactory.create_by_address(address)
        score_db = IconScoreDatabase(address, context_db)
        return score_db

    def _load_score_wrapper(self, address: 'Address', tx_hash: bytes) -> callable:
        """Load IconScoreBase subclass from IconScore python package

        :param address: icon_score_address
        :return: IconScoreBase subclass (NOT instance)
        """

        score_wrapper = self.icon_score_loader.load_score(address.to_bytes().hex(), tx_hash)
        if score_wrapper is None:
            raise InvalidParamsException(f'score_wrapper load Fail {address}')
        return score_wrapper

    def _clear_garbage_score(self):
        if self.icon_score_loader is None:
            return
        score_root_path = self.icon_score_loader.score_root_path
        try:
            dir_list = os.listdir(score_root_path)
        except:
            return

        for dir_name in dir_list:
            try:
                address = Address.from_bytes(bytes.fromhex(dir_name))
            except:
                continue
            deploy_info = self.deploy_storage.get_deploy_info(None, address)
            if deploy_info is None:
                self._remove_score_dir(address)
                continue
            else:
                try:
                    sub_dir_list = os.listdir(os.path.join(score_root_path, bytes.hex(address.to_bytes())))
                except:
                    continue
                for sub_dir_name in sub_dir_list:
                    try:
                        tx_hash = bytes.fromhex(sub_dir_name[2:])
                    except:
                        continue

                    if tx_hash == bytes(DEFAULT_BYTE_SIZE):
                        continue
                    if tx_hash == deploy_info.current_tx_hash:
                        continue
                    elif tx_hash == deploy_info.next_tx_hash:
                        continue
                    else:
                        self._remove_score_dir(address, sub_dir_name)

    @classmethod
    def _remove_score_dir(cls, address: 'Address', converted_tx_hash: Optional[str] = None):
        if cls.icon_score_loader is None:
            return
        score_root_path = cls.icon_score_loader.score_root_path

        if converted_tx_hash is None:
            target_path = os.path.join(score_root_path, bytes.hex(address.to_bytes()))
        else:
            target_path = os.path.join(score_root_path, bytes.hex(address.to_bytes()), converted_tx_hash)

        try:
            rmtree(target_path)
        except Exception as e:
            Logger.warning(e)
