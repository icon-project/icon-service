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
from typing import TYPE_CHECKING, Optional, Tuple

from ..icon_constant import DEFAULT_BYTE_SIZE, DATA_BYTE_ORDER
from ..base.address import Address, ICON_EOA_ADDRESS_BYTES_SIZE, ICON_CONTRACT_ADDRESS_BYTES_SIZE
from ..base.exception import ServerErrorException
from . import DeployType, DeployState, make_score_id

if TYPE_CHECKING:
    from ..iconscore.icon_score_context import IconScoreContext
    from ..database.db import ContextDatabase


class IconScoreDeployTXParams(object):
    _VERSION = 0
    _STRUCT_FMT = f'>BBI{ICON_CONTRACT_ADDRESS_BYTES_SIZE}s{DEFAULT_BYTE_SIZE}s{16}s'
    _PIVOT_SIZE = 1 + 1 + 4 + ICON_CONTRACT_ADDRESS_BYTES_SIZE + 32 + 16

    # leveldb IconScoreDeployTXParams value structure
    # (bigendian, 1 + 1 + 4+ ICON_CONTRACT_ADDRESS_BYTES_SIZE + 32 + 16 + data_bytes)
    # version(1)
    # | deploy_type(1)
    # | deploy_data_length(4)
    # | score_address(21)
    # | tx_hash(DEFAULT_BYTE_SIZE)
    # | score_id(16)
    # | deploy_data_value(deploy_data_length)

    def __init__(self,
                 tx_hash: bytes,
                 deploy_type: 'DeployType',
                 score_address: 'Address',
                 deploy_data: dict,
                 score_id: str):
        # key
        self._tx_hash = tx_hash
        # value
        self._score_address = score_address
        self._deploy_type = deploy_type
        self._deploy_data = deploy_data
        self._score_id = score_id

    @property
    def tx_hash(self) -> bytes:
        return self._tx_hash

    @property
    def deploy_type(self) -> 'DeployType':
        return self._deploy_type

    @property
    def score_address(self) -> 'Address':
        return self._score_address

    @property
    def deploy_data(self) -> dict:
        return self._deploy_data

    @property
    def score_id(self) -> str:
        return self._score_id

    @staticmethod
    def from_bytes(buf: bytes) -> 'IconScoreDeployTXParams':
        """Create IconScoreDeployTXParams object from bytes data

        :param buf: (bytes) bytes data including IconScoreDeployTXParams information
        :return: (IconScoreDeployTXParams) IconScoreDeployTXParams object
        """

        version, deploy_type, deploy_data_length, score_addr_bytes, hash_bytes, score_id_bytes = unpack(
            IconScoreDeployTXParams._STRUCT_FMT, buf[:IconScoreDeployTXParams._PIVOT_SIZE])

        json_str_deploy_data_bytes = unpack(
            f'{deploy_data_length}s', buf[IconScoreDeployTXParams._PIVOT_SIZE:])[0]

        score_address = Address.from_bytes(score_addr_bytes)
        deploy_data = json.loads(json_str_deploy_data_bytes.decode())

        block_height_bytes = score_id_bytes[:8]
        tx_index_bytes = score_id_bytes[8:]

        block_height = int.from_bytes(block_height_bytes, DATA_BYTE_ORDER)
        tx_index = int.from_bytes(tx_index_bytes, DATA_BYTE_ORDER)
        is_not_zero = block_height + tx_index
        if is_not_zero:
            score_id = make_score_id(block_height, tx_index)
        else:
            score_id = make_score_id(0, 0)

        tx_params = IconScoreDeployTXParams(hash_bytes, DeployType(deploy_type), score_address, deploy_data, score_id)
        return tx_params

    def to_bytes(self) -> bytes:
        """Convert block object to bytes

        :return: data including information of IconScoreDeployInfo object
        """

        # for extendability
        json_str_deploy_data = json.dumps(self._deploy_data)
        deploy_data_length = len(json_str_deploy_data.encode())

        score_id = self._score_id
        tmp = score_id.split('_')
        block_height = int(tmp[0])
        tx_index = int(tmp[1])
        bytes1 = block_height.to_bytes(8, DATA_BYTE_ORDER)
        bytes2 = tx_index.to_bytes(8, DATA_BYTE_ORDER)
        score_id_bytes = bytes1 + bytes2

        bytes_var1 = pack(
            IconScoreDeployTXParams._STRUCT_FMT,
            self._VERSION, self._deploy_type.value, deploy_data_length,
            self._score_address.to_bytes(), self._tx_hash, score_id_bytes)
        bytes_var2 = pack(f'>{deploy_data_length}s', json_str_deploy_data.encode())

        return bytes_var1 + bytes_var2


class IconScoreDeployInfo(object):
    _VERSION = 0
    _STRUCT_FMT = \
        f'>B{ICON_CONTRACT_ADDRESS_BYTES_SIZE}s{ICON_EOA_ADDRESS_BYTES_SIZE}' \
        f's{DEFAULT_BYTE_SIZE}s{DEFAULT_BYTE_SIZE}s'

    # leveldb IconScoreDeployInfo value structure
    # (bigendian, 1 + ICON_CONTRACT_ADDRESS_BYTES_SIZE + ICON_EOA_ADDRESS_BYTES_SIZE + 32 + 32 bytes)
    # version(1)
    # | score_address(ICON_CONTRACT_ADDRESS_BYTES_SIZE)
    # | owner(ICON_EOA_ADDRESS_BYTES_SIZE)
    # | current_tx_hash(DEFAULT_BYTE_SIZE)
    # | next_tx_hash(DEFAULT_BYTE_SIZE)

    def __init__(self,
                 score_address: 'Address',
                 owner: 'Address',
                 current_tx_hash: Optional[bytes],
                 next_tx_hash: Optional[bytes]):
        # key
        self._score_address = score_address

        # value
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
        score_address_bytes = bytes_params[1]
        owner_address_bytes = bytes_params[2]
        current_tx_hash = bytes_params[3]
        next_tx_hash = bytes_params[4]

        score_addr = Address.from_bytes(score_address_bytes)
        owner_addr = Address.from_bytes(owner_address_bytes)

        if int(bytes.hex(current_tx_hash), 16) == 0:
            current_tx_hash = None
        converted_current_tx_hash = current_tx_hash

        if int(bytes.hex(next_tx_hash), 16) == 0:
            next_tx_hash = None
        converted_next_tx_hash = next_tx_hash

        info = IconScoreDeployInfo(score_addr, owner_addr,
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
                         self._VERSION,
                         self._score_address.to_bytes(), self.owner.to_bytes(),
                         converted_current_hash, converted_next_hash)
        return bytes_var


class IconScoreDeployStateInfo(object):
    _VERSION = 0
    _STRUCT_FMT = f'>BB{16}s'
    _PIVOT_SIZE = 1 + 1 + 16

    # leveldb IconScoreDeployInfo value structure
    # (bigendian, 1 + 1 + 16
    # version(1)
    # deploystate(1)
    # score_id(16)

    def __init__(self,
                 deploy_state: 'DeployState',
                 score_id: str):

        self._deploy_state = deploy_state
        self._score_id = score_id

    @property
    def deploy_state(self) -> 'DeployState':
        return self._deploy_state

    @property
    def score_id(self) -> str:
        return self._score_id

    @staticmethod
    def from_bytes(buf: bytes) -> 'IconScoreDeployStateInfo':
        """Create IconScoreDeployInfo object from bytes data

        :param buf: (bytes) bytes data including IconScoreDeployInfo information
        :return: (IconScoreDeployInfo) IconScoreDeployInfo object
        """

        bytes_params = unpack(IconScoreDeployStateInfo._STRUCT_FMT, buf[: IconScoreDeployStateInfo._PIVOT_SIZE])
        # version = bytes_params[0]
        deploy_state = bytes_params[1]
        score_id_bytes = bytes_params[2]

        block_height_bytes = score_id_bytes[:8]
        tx_index_bytes = score_id_bytes[8:]

        block_height = int.from_bytes(block_height_bytes, DATA_BYTE_ORDER)
        tx_index = int.from_bytes(tx_index_bytes, DATA_BYTE_ORDER)
        is_not_zero = block_height + tx_index
        if is_not_zero:
            score_id = make_score_id(block_height, tx_index)
        else:
            score_id = make_score_id(0, 0)

        info = IconScoreDeployStateInfo(DeployState(deploy_state), score_id)
        return info

    def to_bytes(self) -> bytes:
        """Convert IconScoreDeployInfo object to bytes

        :return: data including information of IconScoreDeployInfo object
        """
        score_id = self._score_id
        tmp = score_id.split('_')
        block_height = int(tmp[0])
        tx_index = int(tmp[1])
        bytes1 = block_height.to_bytes(8, DATA_BYTE_ORDER)
        bytes2 = tx_index.to_bytes(8, DATA_BYTE_ORDER)
        score_id_bytes = bytes1 + bytes2

        bytes_var = pack(self._STRUCT_FMT,
                         self._VERSION,
                         self._deploy_state.value,
                         score_id_bytes)
        return bytes_var


class IconScoreDeployStorage(object):
    _DEPLOY_STORAGE_PREFIX = b'isds|'
    _DEPLOY_STORAGE_DEPLOY_INFO_PREFIX = _DEPLOY_STORAGE_PREFIX + b'di|'
    _DEPLOY_STORAGE_DEPLOY_STATE_INFO_PREFIX = _DEPLOY_STORAGE_PREFIX + b'si|'
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
            if context:
                score_id = make_score_id(context.block.height, context.tx.index)
            else:
                score_id = make_score_id(0, 0)
            tx_params = IconScoreDeployTXParams(tx_hash, deploy_state, score_address, deploy_data, score_id)
            self._put_deploy_tx_params(context, tx_params)
        else:
            raise ServerErrorException(f'already put deploy_params')

        deploy_info = self.get_deploy_info(context, score_address)
        if deploy_info is None:
            deploy_info = IconScoreDeployInfo(score_address, owner, None, tx_hash)
            self._put_deploy_info(context, deploy_info)
        else:
            if deploy_info.owner != owner:
                raise ServerErrorException(f'invalid owner: {deploy_info.owner} != {owner}')
            if deploy_info.next_tx_hash is not None:
                self._db.delete(context, deploy_info.next_tx_hash)
            deploy_info.next_tx_hash = tx_hash
            self._put_deploy_info(context, deploy_info)

    def put_deploy_info_and_tx_params_for_builtin(self, score_address: 'Address', owner: 'Address') -> None:

        deploy_info = IconScoreDeployInfo(score_address, owner, None, None)
        self._put_deploy_info(None, deploy_info)
        score_id = make_score_id(0, 0)
        self.put_deploy_state_info(None, score_address, DeployState.WAIT_TO_DEPLOY, score_id)

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
                self._put_deploy_info(context, deploy_info)

                tx_params = self.get_deploy_tx_params(context, deploy_info.current_tx_hash)
                if tx_params is None:
                    raise ServerErrorException(f'tx_params is None {deploy_info.current_tx_hash}')
                score_id = tx_params.score_id
                self.put_deploy_state_info(context, score_address, DeployState.WAIT_TO_DEPLOY, score_id)

    def put_deploy_state_info(self, context: Optional['IconScoreContext'],
                              score_address: 'Address',
                              deploy_state: 'DeployState',
                              score_id: str) -> None:

        state_info = IconScoreDeployStateInfo(deploy_state, score_id)
        value = state_info.to_bytes()
        self._db.put(context, self._create_db_key(
            self._DEPLOY_STORAGE_DEPLOY_STATE_INFO_PREFIX, score_address.to_bytes()), value)

    def _get_deploy_state_info(self,
                               context: 'IconScoreContext',
                               score_address: 'Address') -> Optional[IconScoreDeployStateInfo]:
        bytes_value = self._db.get(context, self._create_db_key(
            self._DEPLOY_STORAGE_DEPLOY_STATE_INFO_PREFIX, score_address.to_bytes()))
        if bytes_value:
            return IconScoreDeployStateInfo.from_bytes(bytes_value)
        else:
            return None

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

    def is_score_active(self,
                        context: 'IconScoreContext',
                        icon_score_address: 'Address') -> bool:
        """Returns whether IconScore is active or not

        :param context:
        :param icon_score_address:
        :return: True(deployed) False(not deployed)
        """

        deploy_state_info = self._get_deploy_state_info(context, icon_score_address)
        if deploy_state_info is None:
            return False
        else:
            return deploy_state_info.deploy_state == DeployState.ACTIVE

    def get_score_id(self,
                     context: 'IconScoreContext',
                     icon_score_address: 'Address') -> Optional[str]:
        """
        """

        deploy_state_info = self._get_deploy_state_info(context, icon_score_address)
        if deploy_state_info is None:
            return None
        else:
            return deploy_state_info.score_id

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

    def get_tx_hashes_by_score_address(self,
                                       context: 'IconScoreContext',
                                       score_address: 'Address') -> Tuple[Optional[bytes], Optional[bytes]]:
        deploy_info = self.get_deploy_info(context, score_address)
        if deploy_info:
            return deploy_info.current_tx_hash, deploy_info.next_tx_hash
        else:
            return None, None

    def get_score_address_by_tx_hash(self,
                                     context: 'IconScoreContext',
                                     tx_hash: bytes) -> Optional['Address']:
        tx_params = self.get_deploy_tx_params(context, tx_hash)
        if tx_params:
            return tx_params.score_address
        else:
            return None
