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

from ..icon_config import DEFAULT_BYTE_SIZE, ADDRESS_BYTE_SIZE
from ..base.address import Address
from ..base.exception import ServerErrorException
from . import DeployState

if TYPE_CHECKING:
    from ..iconscore.icon_score_context import IconScoreContext
    from ..database.db import ContextDatabase


class IconScoreDeployTXParams(object):
    _VERSION = 0
    _STRUCT_FMT = f'>BBI{ADDRESS_BYTE_SIZE}s{DEFAULT_BYTE_SIZE}s'
    _PIVOT_SIZE = 1 + 1 + 4 + 21 + 32

    # leveldb IconScoreDeployTXParams value structure (bigendian, 1 + 1 + 4 + 21 + 32 + ~~ bytes)
    # version(1)
    # | deploy_state(1)
    # | deploy_data_length(4)
    # | score_address(21)
    # | tx_hash(DEFAULT_BYTE_SIZE)
    # | deploy_data_value(deploy_data_lenth)

    def __init__(self,
                 tx_hash: 'bytes',
                 deploy_state: 'DeployState',
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
    def deploy_state(self) -> 'DeployState':
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
        f'>B?{ADDRESS_BYTE_SIZE}s{ADDRESS_BYTE_SIZE}s{DEFAULT_BYTE_SIZE}s{DEFAULT_BYTE_SIZE}s{DEFAULT_BYTE_SIZE}s'

    # leveldb IconScoreDeployInfo value structure (bigendian, 1 + 1 + 21 + 21 + 32 + 32 + 32 bytes)
    # version(1)
    # | service_enable(1)
    # | score_address(21)
    # | owner(21)
    # | current_tx_hash(DEFAULT_BYTE_SIZE)
    # | next_tx_hash(DEFAULT_BYTE_SIZE)
    # | audit_tx_hash(DEFAULT_BYTE_SIZE)

    def __init__(self,
                 score_address: 'Address',
                 service_enable: bool,
                 owner: 'Address',
                 current_tx_hash: Optional[bytes],
                 next_tx_hash: Optional[bytes],
                 audit_tx_hash: Optional[bytes]):
        # key
        self._score_address = score_address

        # value
        self._service_enable = service_enable
        self._owner = owner
        self._current_tx_hash = current_tx_hash
        self._next_tx_hash = next_tx_hash
        self._audit_tx_hash = audit_tx_hash

    @property
    def score_address(self) -> 'Address':
        return self._score_address

    @property
    def service_enable(self) -> bool:
        return self._service_enable

    @service_enable.setter
    def service_enable(self, value) -> None:
        self._service_enable = value

    @property
    def owner(self) -> 'Address':
        return self._owner

    @property
    def current_tx_hash(self) -> bytes:
        return self._current_tx_hash

    @current_tx_hash.setter
    def current_tx_hash(self, value) -> None:
        self._current_tx_hash = value

    @property
    def next_tx_hash(self) -> Optional[bytes]:
        return self._next_tx_hash

    @next_tx_hash.setter
    def next_tx_hash(self, value) -> None:
        self._next_tx_hash = value

    @property
    def audit_tx_hash(self) -> Optional[bytes]:
        return self._audit_tx_hash

    @audit_tx_hash.setter
    def audit_tx_hash(self, value) -> None:
        self._audit_tx_hash = value

    @staticmethod
    def from_bytes(buf: bytes) -> 'IconScoreDeployInfo':
        """Create IconScoreDeployInfo object from bytes data

        :param buf: (bytes) bytes data including IconScoreDeployInfo information
        :return: (IconScoreDeployInfo) IconScoreDeployInfo object
        """

        bytes_params = unpack(IconScoreDeployInfo._STRUCT_FMT, buf)
        # version = bytes_params[0]
        service_enable = bytes_params[1]
        score_address_bytes = bytes_params[2]
        owner_address_bytes = bytes_params[3]
        current_tx_hash = bytes_params[4]
        next_tx_hash = bytes_params[5]
        audit_tx_hash = bytes_params[6]

        score_addr = Address.from_bytes(score_address_bytes)
        owner_addr = Address.from_bytes(owner_address_bytes)

        if int(bytes.hex(current_tx_hash), 16) == 0:
            current_tx_hash = None
        converted_current_tx_hash = current_tx_hash

        if int(bytes.hex(next_tx_hash), 16) == 0:
            next_tx_hash = None
        converted_next_tx_hash = next_tx_hash

        if int(bytes.hex(audit_tx_hash), 16) == 0:
            audit_tx_hash = None
        converted_audit_tx_hash = audit_tx_hash

        info = IconScoreDeployInfo(
            score_addr, service_enable, owner_addr,
            converted_current_tx_hash, converted_next_tx_hash, converted_audit_tx_hash)
        return info

    def to_bytes(self) -> bytes:
        """Convert IconScoreDeployInfo object to bytes

        :return: data including information of IconScoreDeployInfo object
        """

        # for extendability

        current_hash = self._current_tx_hash
        if current_hash is None:
            current_hash = bytes(DEFAULT_BYTE_SIZE)
        converted_current_hash = current_hash

        next_hash = self._next_tx_hash
        if next_hash is None:
            next_hash = bytes(DEFAULT_BYTE_SIZE)
        converted_next_hash = next_hash

        audit_hash = self._audit_tx_hash
        if audit_hash is None:
            audit_hash = bytes(DEFAULT_BYTE_SIZE)
        converted_audit_hash = audit_hash

        bytes_var = pack(self._STRUCT_FMT,
                         self._VERSION, self._service_enable,
                         self.score_address.to_bytes(), self._owner.to_bytes(),
                         converted_current_hash, converted_next_hash, converted_audit_hash)
        return bytes_var


class IconScoreDeployStorage(object):
    def __init__(self, db: 'ContextDatabase') -> None:
        """Constructor

        :param db:
        """
        super().__init__()
        self._db = db

    def put_total_deploy_info(self,
                              context: 'IconScoreContext',
                              score_address: 'Address',
                              deploy_state: 'DeployState',
                              owner: 'Address',
                              tx_hash: bytes,
                              deploy_data: 'dict') -> None:
        prev_tx_params = self.get_deploy_tx_params(context, tx_hash)
        if prev_tx_params is None:
            tx_params = IconScoreDeployTXParams(tx_hash, deploy_state, score_address, deploy_data)
            self.put_deploy_tx_params(context, tx_params)
        else:
            raise ServerErrorException(f'already put deploy_params')

        service_enable = False
        deploy_info = self.get_deploy_info(context, score_address)
        if deploy_info is None:
            deploy_info = IconScoreDeployInfo(score_address, service_enable, owner, tx_hash, None, None)
            self.put_deploy_info(context, deploy_info)
        else:
            if deploy_info.next_tx_hash is not None:
                self._db.delete(context, deploy_info.next_tx_hash)
            deploy_info.next_tx_hash = tx_hash
            self.put_deploy_info(context, deploy_info)

    def put_total_deploy_info_for_prebuiltin(self, score_address: 'Address', owner: 'Address') -> None:

        deploy_info = IconScoreDeployInfo(score_address, True, owner, None, None, None)
        self.put_deploy_info(None, deploy_info)

    def update_score_info(self,
                          context: 'IconScoreContext',
                          score_address: 'Address',
                          tx_hash: bytes,
                          audit_tx_hash: bytes) -> None:

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
                deploy_info.audit_tx_hash = audit_tx_hash
                deploy_info.service_enable = True
                self.put_deploy_info(context, deploy_info)

    def put_deploy_info(self, context: Optional['IconScoreContext'], deploy_info: 'IconScoreDeployInfo') -> None:
        """

        :param context:
        :param deploy_info:
        :return:
        """

        key = deploy_info.score_address.to_bytes()
        value = deploy_info.to_bytes()
        self._db.put(context, key, value)

    def get_deploy_info(self, context: 'IconScoreContext', score_addr: 'Address') -> Optional['IconScoreDeployInfo']:
        key = score_addr.to_bytes()
        bytes_value = self._db.get(context, key)
        if bytes_value:
            return IconScoreDeployInfo.from_bytes(bytes_value)
        else:
            return None

    def put_deploy_tx_params(self, context: 'IconScoreContext', deploy_tx_params: 'IconScoreDeployTXParams') -> None:
        """

        :param context:
        :param deploy_tx_params:
        :return:
        """

        key = deploy_tx_params.tx_hash
        value = deploy_tx_params.to_bytes()
        self._db.put(context, key, value)

    def get_deploy_tx_params(self, context: 'IconScoreContext', tx_hash: bytes) -> Optional['IconScoreDeployTXParams']:
        key = tx_hash
        bytes_value = self._db.get(context, key)
        if bytes_value:
            return IconScoreDeployTXParams.from_bytes(bytes_value)
        else:
            return None

    def is_score_deployed(self,
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

        return deploy_info.service_enable

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
