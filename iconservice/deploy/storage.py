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

import json
import warnings
from struct import pack, unpack
from typing import TYPE_CHECKING, Optional, Tuple

from ..base.ComponentBase import StorageBase
from ..base.address import Address, ICON_EOA_ADDRESS_BYTES_SIZE, ICON_CONTRACT_ADDRESS_BYTES_SIZE
from ..base.exception import InvalidParamsException, AccessDeniedException
from ..icon_constant import DEFAULT_BYTE_SIZE, Revision, ZERO_TX_HASH, DeployState, DeployType

if TYPE_CHECKING:
    from ..iconscore.icon_score_context import IconScoreContext


class IconScoreDeployTXParams(object):
    _VERSION = 0
    _STRUCT_FMT = f'>BBI{ICON_CONTRACT_ADDRESS_BYTES_SIZE}s{DEFAULT_BYTE_SIZE}s'
    _PIVOT_SIZE = 1 + 1 + 4 + ICON_CONTRACT_ADDRESS_BYTES_SIZE + DEFAULT_BYTE_SIZE

    # leveldb IconScoreDeployTXParams value structure
    # (bigendian, 1 + 1 + 4+ ICON_CONTRACT_ADDRESS_BYTES_SIZE + DEFAULT_BYTE_SIZE + data_bytes)
    # version(1)
    # | deploy_type(1)
    # | deploy_data_length(4)
    # | score_address(21)
    # | tx_hash(DEFAULT_BYTE_SIZE)
    # | deploy_data_value(deploy_data_length)

    def __init__(self,
                 tx_hash: bytes,
                 deploy_type: 'DeployType',
                 score_address: 'Address',
                 deploy_data: dict):
        # key
        self._tx_hash = tx_hash
        # value
        self._score_address = score_address
        self._deploy_type = deploy_type
        self._deploy_data = deploy_data

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

    @staticmethod
    def from_bytes(buf: bytes) -> 'IconScoreDeployTXParams':
        """Create IconScoreDeployTXParams object from bytes data

        :param buf: (bytes) bytes data including IconScoreDeployTXParams information
        :return: (IconScoreDeployTXParams) IconScoreDeployTXParams object
        """

        version, deploy_type, deploy_data_length, score_addr_bytes, hash_bytes = unpack(
            IconScoreDeployTXParams._STRUCT_FMT, buf[:IconScoreDeployTXParams._PIVOT_SIZE])

        json_str_deploy_data_bytes = unpack(
            f'{deploy_data_length}s', buf[IconScoreDeployTXParams._PIVOT_SIZE:])[0]

        score_address = Address.from_bytes(score_addr_bytes)
        deploy_data = json.loads(json_str_deploy_data_bytes.decode())

        tx_params = IconScoreDeployTXParams(hash_bytes, DeployType(deploy_type), score_address, deploy_data)
        return tx_params

    def to_bytes(self) -> bytes:
        """Convert block object to bytes

        :return: data including information of IconScoreDeployInfo object
        """

        # for extendability
        json_str_deploy_data: str = json.dumps(self._deploy_data)
        deploy_data: bytes = json_str_deploy_data.encode(encoding='utf-8')
        deploy_data_length: int = len(deploy_data)

        bytes_var1 = pack(
            IconScoreDeployTXParams._STRUCT_FMT,
            self._VERSION, self._deploy_type.value, deploy_data_length,
            self._score_address.to_bytes(), self._tx_hash)
        bytes_var2 = pack(f'>{deploy_data_length}s', deploy_data)

        return bytes_var1 + bytes_var2


class IconScoreDeployInfo(object):
    """
    leveldb IconScoreDeployInfo value structure
    (bigendian, 1 + 1 + ICON_CONTRACT_ADDRESS_BYTES_SIZE + ICON_EOA_ADDRESS_BYTES_SIZE +
    DEFAULT_BYTE_SIZE + DEFAULT_BYTE_SIZE bytes)
    | version(1)
    | deploystate(1)
    | score_address(ICON_CONTRACT_ADDRESS_BYTES_SIZE)
    | owner(ICON_EOA_ADDRESS_BYTES_SIZE)
    | current_tx_hash(DEFAULT_BYTE_SIZE)
    | next_tx_hash(DEFAULT_BYTE_SIZE)
    """

    _VERSION = 0
    _STRUCT_FMT = f'>BB' \
        f'{ICON_CONTRACT_ADDRESS_BYTES_SIZE}s' \
        f'{ICON_EOA_ADDRESS_BYTES_SIZE}s' \
        f'{DEFAULT_BYTE_SIZE}s' \
        f'{DEFAULT_BYTE_SIZE}s'

    def __init__(self,
                 score_address: 'Address',
                 deploy_state: 'DeployState',
                 owner: 'Address',
                 current_tx_hash: bytes,
                 next_tx_hash: bytes):
        assert isinstance(current_tx_hash, bytes) and len(current_tx_hash) == 32
        assert isinstance(next_tx_hash, bytes) and len(next_tx_hash) == 32

        # key
        self._score_address = score_address

        # value
        self.deploy_state = deploy_state
        self.owner = owner
        self.current_tx_hash = current_tx_hash
        self.next_tx_hash = next_tx_hash

    def __str__(self):
        return f"score_address={self.score_address}, " \
               f"owner={self.owner}, " \
               f"state={self.deploy_state}, " \
               f"current_tx_hash={self.current_tx_hash}, " \
               f"next_tx_hash={self.next_tx_hash}"

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
        # version: int = bytes_params[0]
        deploy_state: int = bytes_params[1]
        score_address: 'Address' = Address.from_bytes(bytes_params[2])
        owner_address: 'Address' = Address.from_bytes(bytes_params[3])
        current_tx_hash: bytes = bytes_params[4]
        next_tx_hash: bytes = bytes_params[5]

        # DeployState 2 is deprecated, this code is needed for backward compatibility.
        if deploy_state == 2:
            deploy_state = DeployState.ACTIVE

        return IconScoreDeployInfo(
            score_address, DeployState(deploy_state), owner_address, current_tx_hash, next_tx_hash)

    def to_bytes(self) -> bytes:
        """Convert IconScoreDeployInfo object to bytes

        :return: data including information of IconScoreDeployInfo object
        """
        return pack(
            self._STRUCT_FMT, self._VERSION, self.deploy_state.value,
            self._score_address.to_bytes(), self.owner.to_bytes(),
            self.current_tx_hash, self.next_tx_hash)


class Storage(StorageBase):
    """Store deploy_int and tx_params on LevelDB.
    """

    _DEPLOY_STORAGE_PREFIX = b'isds|'
    _DEPLOY_STORAGE_DEPLOY_INFO_PREFIX = _DEPLOY_STORAGE_PREFIX + b'di|'
    _DEPLOY_STORAGE_DEPLOY_TX_PARAMS_PREFIX = _DEPLOY_STORAGE_PREFIX + b'dtp|'

    def put_deploy_info_and_tx_params(self,
                                      context: 'IconScoreContext',
                                      score_address: 'Address',
                                      deploy_type: 'DeployType',
                                      owner: 'Address',
                                      tx_hash: bytes,
                                      deploy_data: dict) -> None:
        prev_tx_params = self.get_deploy_tx_params(context, tx_hash)
        if prev_tx_params is not None:
            raise InvalidParamsException(f'deploy_params already exists: {tx_hash}')

        # Save DeployTXParams to stateDB
        tx_params = IconScoreDeployTXParams(tx_hash, deploy_type, score_address, deploy_data)
        self.put_deploy_tx_params(context, tx_params)

        deploy_info = self.get_deploy_info(context, score_address)
        if deploy_info is None:
            # SCORE install case
            deploy_info = IconScoreDeployInfo(
                score_address, DeployState.INACTIVE, owner, ZERO_TX_HASH, tx_hash)
        else:
            # SCORE update case
            if deploy_info.owner != owner:
                raise AccessDeniedException(f'Invalid owner: {deploy_info.owner} != {owner}')

            # If the previous DeployTXParams has exists, remove it before deploying
            if deploy_info.next_tx_hash != ZERO_TX_HASH:
                self.delete_deploy_tx_params(context, deploy_info.next_tx_hash)

            deploy_info.next_tx_hash = tx_hash

        # Save DeployInfo to stateDB
        self.put_deploy_info(context, deploy_info)

    def update_score_info(self,
                          context: 'IconScoreContext',
                          score_address: 'Address',
                          tx_hash: bytes) -> None:

        deploy_info = self.get_deploy_info(context, score_address)
        if deploy_info is None:
            raise InvalidParamsException(f'deploy_info is None: {score_address}')

        next_tx_hash = deploy_info.next_tx_hash
        # have to match next_tx_hash and tx_hash
        # tx_hash is None -> builtin install
        if tx_hash is not None and tx_hash != next_tx_hash:
            raise InvalidParamsException(
                f'Invalid update: tx_hash({tx_hash}) != next_tx_hash({next_tx_hash})')

        deploy_info.current_tx_hash = next_tx_hash
        deploy_info.next_tx_hash = ZERO_TX_HASH
        deploy_info.deploy_state = DeployState.ACTIVE
        self.put_deploy_info(context, deploy_info)

        tx_params = self.get_deploy_tx_params(context, deploy_info.current_tx_hash)
        if tx_params is None:
            raise InvalidParamsException(f'tx_params is None: {deploy_info.current_tx_hash}')

    def put_deploy_info(self, context: Optional['IconScoreContext'], deploy_info: 'IconScoreDeployInfo') -> None:
        """

        :param context:
        :param deploy_info:
        :return:
        """
        key: bytes = self._create_db_key(
            self._DEPLOY_STORAGE_DEPLOY_INFO_PREFIX, deploy_info.score_address.to_bytes())
        value: bytes = deploy_info.to_bytes()

        self._db.put(context, key, value)

    def get_deploy_info(self, context: Optional['IconScoreContext'], score_address: 'Address') \
            -> Optional['IconScoreDeployInfo']:

        key: bytes = self._create_db_key(
            self._DEPLOY_STORAGE_DEPLOY_INFO_PREFIX, score_address.to_bytes())
        data: bytes = self._db.get(context, key)
        if data is None:
            return None

        return IconScoreDeployInfo.from_bytes(data)

    def put_deploy_tx_params(self, context: 'IconScoreContext', deploy_tx_params: 'IconScoreDeployTXParams') -> None:
        """

        :param context:
        :param deploy_tx_params:
        :return:
        """
        key: bytes = self._create_db_key(self._DEPLOY_STORAGE_DEPLOY_TX_PARAMS_PREFIX, deploy_tx_params.tx_hash)
        value = deploy_tx_params.to_bytes()
        self._db.put(context, key, value)

    def get_deploy_tx_params(self, context: 'IconScoreContext', tx_hash: bytes) -> Optional['IconScoreDeployTXParams']:
        key: bytes = self._create_db_key(self._DEPLOY_STORAGE_DEPLOY_TX_PARAMS_PREFIX, tx_hash)
        value: bytes = self._db.get(context, key)

        if value is None:
            return None

        return IconScoreDeployTXParams.from_bytes(value)

    def delete_deploy_tx_params(self, context: 'IconScoreContext', tx_hash: bytes):
        """Delete DeployTXParams indicated by tx_hash from stateDB.

        :param context:
        :param tx_hash:
        :return:
        """
        if context.revision >= Revision.TWO.value:
            key: bytes = self._create_db_key(
                self._DEPLOY_STORAGE_DEPLOY_TX_PARAMS_PREFIX, tx_hash)
        else:
            key: bytes = tx_hash

        self._db.delete(context, key)

    @staticmethod
    def _create_db_key(prefix: bytes, src_key: bytes) -> bytes:
        return prefix + src_key

    def get_tx_hashes_by_score_address(self,
                                       context: 'IconScoreContext',
                                       score_address: 'Address') -> Tuple[Optional[bytes], Optional[bytes]]:
        warnings.warn("legacy function don't use.", DeprecationWarning, stacklevel=2)
        deploy_info = self.get_deploy_info(context, score_address)
        if deploy_info:
            current_tx_hash = deploy_info.current_tx_hash
            if current_tx_hash == ZERO_TX_HASH:
                # Keep compatibility for old blocks
                current_tx_hash = None

            next_tx_hash = deploy_info.next_tx_hash
            if next_tx_hash == ZERO_TX_HASH:
                # Keep compatibility for old blocks
                next_tx_hash = None

            return current_tx_hash, next_tx_hash

        return None, None

    def get_score_address_by_tx_hash(self,
                                     context: 'IconScoreContext',
                                     tx_hash: bytes) -> Optional['Address']:
        warnings.warn("legacy function don't use.", DeprecationWarning, stacklevel=2)
        tx_params = self.get_deploy_tx_params(context, tx_hash)
        if tx_params:
            return tx_params.score_address

        return None
