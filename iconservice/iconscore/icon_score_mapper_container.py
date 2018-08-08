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
from ..base.exception import ServerErrorException
from ..icon_constant import DEFAULT_BYTE_SIZE
from ..iconscore.icon_score_mapper import IconScoreMapper
from ..iconscore.icon_score_context import IconScoreContextType

if TYPE_CHECKING:
    from ..base.address import Address
    from ..iconscore.icon_score_base import IconScoreBase
    from ..deploy.icon_score_deploy_engine import IconScoreDeployStorage
    from .icon_score_loader import IconScoreLoader
    from .icon_score_context import IconScoreContext


class IconScoreMapperContainer(object):
    """Icon score information mapping table

    This instance should be used as a singletone

    key: icon_score_address
    value: IconScoreInfo
    """

    icon_score_loader: 'IconScoreLoader' = None
    deploy_storage: 'IconScoreDeployStorage' = None

    def __init__(self) -> None:
        """Constructor
        """
        self._lock = Lock()
        IconScoreMapper.icon_score_loader = self.icon_score_loader
        IconScoreMapper.deploy_storage = self.deploy_storage

        self._score_mapper = IconScoreMapper()
        self._context_score_mapper = dict()

    @property
    def score_root_path(self) -> str:
        return self.icon_score_loader.score_root_path

    def close(self):
        self._score_mapper.close()
        self._clear_garbage_score()

    def create_context_score_mapper(self, context: 'IconScoreContext'):
        if context.type == IconScoreContextType.QUERY:
            return
        self._context_score_mapper[context.block.hash] = IconScoreMapper()

    def get_icon_score(self,
                       context: 'IconScoreContext',
                       address: 'Address') -> Optional['IconScoreBase']:
        if context.type == IconScoreContextType.QUERY:
            return self._score_mapper.get_icon_score(context, address)

        mapper: 'IconScoreMapper' = self._context_score_mapper.get(context.block.hash)
        if mapper is None:
            raise ServerErrorException(f"mapper is None {context.block.hash}")

        if address in mapper:
            return mapper.get_icon_score(context, address)
        else:
            return self._score_mapper.get_icon_score(context, address)

    def load_icon_score(self,
                        context: Optional['IconScoreContext'],
                        address: 'Address',
                        score_id: str) -> Optional['IconScoreBase']:
        if context is None:
            return self._score_mapper.load_icon_score(address, score_id)
        if context.type == IconScoreContextType.QUERY:
            raise ServerErrorException("mismatch context type have to invoke type")

        mapper: 'IconScoreMapper' = self._context_score_mapper.get(context.block.hash)
        if mapper is None:
            raise ServerErrorException(f"mapper is None {context.block.hash}")

        return mapper.load_icon_score(address, score_id)

    def commit(self, block_hash: bytes):
        with self._lock:
            self._score_mapper.update(self._context_score_mapper.get(block_hash))
        self._context_score_mapper.clear()

    def rollback(self, block_hash: bytes):
        mapper = self._context_score_mapper.get(block_hash)
        if mapper is not None:
            mapper.clear()

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
    def _remove_score_dir(cls, address: 'Address', score_id: Optional[str] = None):
        if cls.icon_score_loader is None:
            return
        score_root_path = cls.icon_score_loader.score_root_path

        if score_id is None:
            target_path = os.path.join(score_root_path, bytes.hex(address.to_bytes()))
        else:
            target_path = os.path.join(score_root_path, bytes.hex(address.to_bytes()), score_id)

        try:
            rmtree(target_path)
        except Exception as e:
            Logger.warning(e)
