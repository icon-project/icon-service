# -*- coding: utf-8 -*-
# Copyright 2018 theloop Inc.
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

import json
from struct import pack, unpack
from typing import TYPE_CHECKING, Optional

from ..icon_constant import DEFAULT_BYTE_SIZE
from ..base.address import Address, ICON_EOA_ADDRESS_BYTES_SIZE, ICON_CONTRACT_ADDRESS_BYTES_SIZE
from ..base.exception import ServerErrorException
from . import DeployType

if TYPE_CHECKING:
    from ..iconscore.icon_score_context import IconScoreContext
    from ..database.db import ContextDatabase


class IconScoreDeployTXParams(object):
    _VERSION = 0
    _STRUCT_FMT = f'>BBI{ICON_CONTRACT_ADDRESS_BYTES_SIZE}s{DEFAULT_BYTE_SIZE}s'
    _PIVOT_SIZE = 1 + 1 + 4 + ICON_CONTRACT_ADDRESS_BYTES_SIZE + 32

    # leveldb IconScoreDeployTXParams value structure
    # (bigendian, 1 + 1 + 4 + ICON_CONTRACT_ADDRESS_BYTES_SIZE + 32 + data_bytes)
    # version(1)
    # | deploy_state(1)
    # | deploy_data_length(4)
    # | score_address(21)
    # | tx_hash(DEFAULT_BYTE_SIZE)
    # | deploy_data_value(deploy_data_lenth)

    def __init__(self,
                 tx_hash: 'bytes',
                 deploy_state: 'DeployType',
                 score_address: 'Address',
                 deploy_data: 'dict'):
        # key
        self._tx_hash = tx_hash
        # value
        self._score_address = score_address
        self._deploy_state = deploy_state
        self._deploy_data = deploy_data

    @property
    def tx_hash(self) -> bytes:
        return self._tx_hash

    @property
    def deploy_state(self) -> 'DeployType':
        return self._deploy_state

    @property
    def score_address(self) -> 'Address':
        return self._score_address

    @property
    def deploy_data(self) -> dict:
        return self._deploy_data

    @staticmethod
    def from_bytes(buf: bytes) -> 'IconScoreDeployTXParams':
        """Create IconScoreDeployTXParams object from bytes data

        :param buf: (bytes) bytes data including IconScoreDeployTXParams information
        :return: (IconScoreDeployTXParams) IconScoreDeployTXParams object
        """

        version, deploy_state, deploy_data_length, score_addr_bytes, hash_bytes = unpack(
            IconScoreDeployTXParams._STRUCT_FMT, buf[:IconScoreDeployTXParams._PIVOT_SIZE])

        json_str_deploy_data_bytes = unpack(
            f'{deploy_data_length}s', buf[IconScoreDeployTXParams._PIVOT_SIZE:])[0]

        score_address = Address.from_bytes(score_addr_bytes)
        deploy_data = json.loads(json_str_deploy_data_bytes.decode())
        tx_params = IconScoreDeployTXParams(hash_bytes, deploy_state, score_address, deploy_data)
        return tx_params

    def to_bytes(self) -> bytes:
        """Convert block object to bytes

        :return: data including information of IconScoreDeployInfo object
        """

        # for extendability
        json_str_deploy_data = json.dumps(self._deploy_data)
        deploy_data_length = len(json_str_deploy_data.encode())
        bytes_var1 = pack(
            IconScoreDeployTXParams._STRUCT_FMT,
            self._VERSION, self._deploy_state.value, deploy_data_length, self._score_address.to_bytes(), self._tx_hash)
        bytes_var2 = pack(f'>{deploy_data_length}s', json_str_deploy_data.encode())

        return bytes_var1 + bytes_var2


class IconScoreDeployInfo(object):
    _VERSION = 0
    _STRUCT_FMT = \
        f'>B?{ICON_CONTRACT_ADDRESS_BYTES_SIZE}s{ICON_EOA_ADDRESS_BYTES_SIZE}' \
        f's{DEFAULT_BYTE_SIZE}s{DEFAULT_BYTE_SIZE}s'

    # leveldb IconScoreDeployInfo value structure
    # (bigendian, 1 + 1 + ICON_CONTRACT_ADDRESS_BYTES_SIZE + ICON_EOA_ADDRESS_BYTES_SIZE + 32 + 32 bytes)
    # version(1)
    # | status_active(1)
    # | score_address(ICON_CONTRACT_ADDRESS_BYTES_SIZE)
    # | owner(ICON_EOA_ADDRESS_BYTES_SIZE)
    # | current_tx_hash(DEFAULT_BYTE_SIZE)
    # | next_tx_hash(DEFAULT_BYTE_SIZE)

    def __init__(self,
                 score_address: 'Address',
                 status_active: bool,
                 owner: 'Address',
                 current_tx_hash: Optional[bytes],
                 next_tx_hash: Optional[bytes]):
        # key
        self._score_address = score_address

        # value
        self.status_active = status_active
        self.owner = owner
        self.current_tx_hash = current_tx_hash
        self.next_tx_hash = next_tx_hash

    @property
    def score_address(self):
        return self._score_address

    @staticmethod
    def from_bytes(buf: bytes) -> 'IconScoreDeployInfo':
        """Create IconScoreDeployInfo object from bytes data

        :param buf: (bytes) bytes data including IconScoreDeployInfo information
        :return: (IconScoreDeployInfo) IconScoreDeployInfo object
        """

        bytes_params = unpack(IconScoreDeployInfo._STRUCT_FMT, buf)
        # version = bytes_params[0]
        status_active = bytes_params[1]
        score_address_bytes = bytes_params[2]
        owner_address_bytes = bytes_params[3]
        current_tx_hash = bytes_params[4]
        next_tx_hash = bytes_params[5]

        score_addr = Address.from_bytes(score_address_bytes)
        owner_addr = Address.from_bytes(owner_address_bytes)

        if int(bytes.hex(current_tx_hash), 16) == 0:
            current_tx_hash = None
        converted_current_tx_hash = current_tx_hash

        if int(bytes.hex(next_tx_hash), 16) == 0:
            next_tx_hash = None
        converted_next_tx_hash = next_tx_hash

        info = IconScoreDeployInfo(score_addr, status_active, owner_addr,
                                   converted_current_tx_hash, converted_next_tx_hash)
        return info

    def to_bytes(self) -> bytes:
        """Convert IconScoreDeployInfo object to bytes

        :return: data including information of IconScoreDeployInfo object
        """

        # for extendability

        current_hash = self.current_tx_hash
        if current_hash is None:
            current_hash = bytes(DEFAULT_BYTE_SIZE)
        converted_current_hash = current_hash

        next_hash = self.next_tx_hash
        if next_hash is None:
            next_hash = bytes(DEFAULT_BYTE_SIZE)
        converted_next_hash = next_hash

        bytes_var = pack(self._STRUCT_FMT,
                         self._VERSION, self.status_active,
                         self._score_address.to_bytes(), self.owner.to_bytes(),
                         converted_current_hash, converted_next_hash)
        return bytes_var


class IconScoreDeployStorage(object):
    _DEPLOY_STORAGE_PREFIX = b'isds|'
    _DEPLOY_STORAGE_DEPLOY_INFO_PREFIX = _DEPLOY_STORAGE_PREFIX + b'di|'
    _DEPLOY_STORAGE_DEPLOY_TX_PARAMS_PREFIX = _DEPLOY_STORAGE_PREFIX + b'dtp|'

    def __init__(self, db: 'ContextDatabase') -> None:
        """Constructor

        :param db:
        """
        super().__init__()
        self._db = db

    def put_deploy_info_and_tx_params(self,
                                      context: 'IconScoreContext',
                                      score_address: 'Address',
                                      deploy_state: 'DeployType',
                                      owner: 'Address',
                                      tx_hash: bytes,
                                      deploy_data: 'dict') -> None:

        prev_tx_params = self.get_deploy_tx_params(context, tx_hash)
        if prev_tx_params is None:
            tx_params = IconScoreDeployTXParams(tx_hash, deploy_state, score_address, deploy_data)
            self._put_deploy_tx_params(context, tx_params)
        else:
            raise ServerErrorException(f'already put deploy_params')

        is_active = False
        deploy_info = self.get_deploy_info(context, score_address)
        if deploy_info is None:
            deploy_info = IconScoreDeployInfo(score_address, is_active, owner, tx_hash, None)
            self._put_deploy_info(context, deploy_info)
        else:
            if deploy_info.owner != owner:
                raise ServerErrorException(f'deploy_info.owner[{deploy_info.owner}] != owner[{owner}]')
            if deploy_info.next_tx_hash is not None:
                self._db.delete(context, deploy_info.next_tx_hash)
            deploy_info.next_tx_hash = tx_hash
            self._put_deploy_info(context, deploy_info)

    def put_deploy_info_and_tx_params_for_builtin(self, score_address: 'Address', owner: 'Address') -> None:

        deploy_info = IconScoreDeployInfo(score_address, True, owner, None, None)
        self._put_deploy_info(None, deploy_info)

    def update_score_info(self,
                          context: 'IconScoreContext',
                          score_address: 'Address',
                          tx_hash: bytes) -> None:

        deploy_info = self.get_deploy_info(context, score_address)
        if deploy_info is None:
            raise ServerErrorException(f'deploy_info is None score_addr : {score_address}')
        else:
            next_tx_hash = deploy_info.next_tx_hash
            if next_tx_hash is None:
                next_tx_hash = tx_hash
            if tx_hash is not None and tx_hash != next_tx_hash:
                raise ServerErrorException(f'tx_hash: {tx_hash} != next_tx_hash: {next_tx_hash}')
            else:
                deploy_info.current_tx_hash = next_tx_hash
                deploy_info.next_tx_hash = None
                deploy_info.status_active = True
                self._put_deploy_info(context, deploy_info)

    def _put_deploy_info(self, context: Optional['IconScoreContext'], deploy_info: 'IconScoreDeployInfo') -> None:
        """

        :param context:
        :param deploy_info:
        :return:
        """
        value = deploy_info.to_bytes()
        self._db.put(context, self._create_db_key(
            self._DEPLOY_STORAGE_DEPLOY_INFO_PREFIX, deploy_info.score_address.to_bytes()), value)

    def get_deploy_info(self, context: 'IconScoreContext', score_addr: 'Address') -> Optional['IconScoreDeployInfo']:
        bytes_value = self._db.get(context, self._create_db_key(
            self._DEPLOY_STORAGE_DEPLOY_INFO_PREFIX, score_addr.to_bytes()))
        if bytes_value:
            return IconScoreDeployInfo.from_bytes(bytes_value)
        else:
            return None

    def _put_deploy_tx_params(self, context: 'IconScoreContext', deploy_tx_params: 'IconScoreDeployTXParams') -> None:
        """

        :param context:
        :param deploy_tx_params:
        :return:
        """
        value = deploy_tx_params.to_bytes()
        self._db.put(context, self._create_db_key(self._DEPLOY_STORAGE_PREFIX, deploy_tx_params.tx_hash), value)

    def get_deploy_tx_params(self, context: 'IconScoreContext', tx_hash: bytes) -> Optional['IconScoreDeployTXParams']:
        bytes_value = self._db.get(context, self._create_db_key(self._DEPLOY_STORAGE_PREFIX, tx_hash))
        if bytes_value:
            return IconScoreDeployTXParams.from_bytes(bytes_value)
        else:
            return None

    @staticmethod
    def _create_db_key(prefix: bytes, src_key: bytes):
        return prefix + src_key

    def is_score_status_active(self,
                               context: 'IconScoreContext',
                               icon_score_address: 'Address') -> bool:
        """Returns whether IconScore is installed or not

        :param context:
        :param icon_score_address:
        :return: True(installed) False(not installed)
        """
        deploy_info = self.get_deploy_info(context, icon_score_address)
        if deploy_info is None:
            return False

        return deploy_info.status_active

    def get_score_owner(self,
                        context: 'IconScoreContext',
                        icon_score_address: 'Address') -> Optional['Address']:
        """Returns whether IconScore is installed or not

        :param context:
        :param icon_score_address:
        :return: True(installed) False(not installed)
        """
        deploy_info = self.get_deploy_info(context, icon_score_address)
        if deploy_info is None:
            return None

        return deploy_info.owner

    def get_tx_hash_by_score_address(self,
                                     context: 'IconScoreContext',
                                     score_address: 'Address') -> Optional[bytes]:
        deploy_info = self.get_deploy_info(context, score_address)
        if deploy_info:
            return deploy_info.current_tx_hash
        else:
            return None

    def get_score_address_by_tx_hash(self,
                                     context: 'IconScoreContext',
                                     tx_hash: bytes) -> Optional['Address']:
        tx_params = self.get_deploy_tx_params(context, tx_hash)
        if tx_params:
            return tx_params.score_address
        else:
            return None
