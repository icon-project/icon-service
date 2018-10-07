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

import os

from shutil import rmtree
from threading import Lock
from typing import TYPE_CHECKING, Optional

from iconcommons import Logger
from iconservice.builtin_scores.governance.governance import Governance
from .icon_score_mapper_object import IconScoreInfo, IconScoreMapperObject
from ..base.address import Address, GOVERNANCE_SCORE_ADDRESS
from ..base.exception import InvalidParamsException
from ..database.db import IconScoreDatabase
from ..database.factory import ContextDatabaseFactory
from ..deploy.icon_score_deploy_engine import IconScoreDeployStorage
from ..icon_constant import DEFAULT_BYTE_SIZE

if TYPE_CHECKING:
    from .icon_score_base import IconScoreBase
    from .icon_score_loader import IconScoreLoader


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
        self._score_mapper = IconScoreMapperObject()
        self._lock = Lock()
        self._is_lock = is_lock

    def __contains__(self, address: 'Address'):
        if self._is_lock:
            with self._lock:
                return address in self._score_mapper
        else:
            return address in self._score_mapper

    def __setitem__(self, key, value):
        if self._is_lock:
            with self._lock:
                self._score_mapper[key] = value
        else:
            self._score_mapper[key] = value

    def get(self, key):
        if self._is_lock:
            with self._lock:
                return self._score_mapper.get(key)
        else:
            return self._score_mapper.get(key)

    def update(self, mapper: 'IconScoreMapper'):
        if self._is_lock:
            with self._lock:
                self._score_mapper.update(mapper._score_mapper)
        else:
            self._score_mapper.update(mapper._score_mapper)

    def close(self):
        for addr, info in self._score_mapper.items():
            info.icon_score.db.close()

    @property
    def score_root_path(self) -> str:
        return self.icon_score_loader.score_root_path

    def get_icon_score(self, address: 'Address', tx_hash: bytes) -> Optional['IconScoreBase']:
        """
        :param address:
        :param tx_hash:
        :return: IconScoreBase object
        """
        score = None
        icon_score_info = self.get(address)

        if icon_score_info is None:
            score = self.load_score(address, tx_hash)
            if score is None:
                raise InvalidParamsException(f"score is None address: {address}")
            self.put_score_info(address, score, tx_hash)

        if icon_score_info is not None:
            score = icon_score_info.icon_score

        return score

    def try_score_package_validate(self, address: 'Address', tx_hash: bytes):
        score_path = self.icon_score_loader.make_score_path(address, tx_hash)
        whitelist_table = self._get_score_package_validator_table()
        self.icon_score_loader.try_score_package_validate(whitelist_table, score_path)

    def _get_score_package_validator_table(self) -> dict:
        governance_info = self.get(GOVERNANCE_SCORE_ADDRESS)
        if governance_info:
            governance: 'Governance' = governance_info.icon_score
            return governance.import_white_list_cache
        else:
            return {"iconservice": ['*']}

    def load_score(self, address: 'Address', tx_hash: bytes) -> Optional['IconScoreBase']:
        score_wrapper = self._load_score_wrapper(address, tx_hash)
        score_db = self._create_icon_score_database(address)
        score = score_wrapper(score_db)
        return score

    def put_score_info(self,
                       address: 'Address',
                       icon_score: 'IconScoreBase',
                       tx_hash: bytes):
        self[address] = IconScoreInfo(icon_score, tx_hash)

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
        score_path = self.icon_score_loader.make_score_path(address, tx_hash)
        score_wrapper = self.icon_score_loader.load_score(score_path)
        if score_wrapper is None:
            raise InvalidParamsException(f'score_wrapper load Fail {address}')
        return score_wrapper

    def clear_garbage_score(self):
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
