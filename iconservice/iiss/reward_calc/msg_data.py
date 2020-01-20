# -*- coding: utf-8 -*-

# Copyright 2019 ICON Foundation
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

from abc import ABCMeta, abstractmethod
from enum import IntEnum
from typing import Any, TYPE_CHECKING, List, Optional

from ...base.exception import InvalidParamsException
from ...icon_constant import DATA_BYTE_ORDER, RC_DB_VERSION_2, RC_DB_VERSION_0
from ...utils.msgpack_for_ipc import MsgPackForIpc, TypeTag

if TYPE_CHECKING:
    from ...base.address import Address


class TxType(IntEnum):
    DELEGATION = 0
    PREP_REGISTER = 1
    PREP_UNREGISTER = 2
    INVALID = 99


class Data:
    @abstractmethod
    def make_key(self, *args, **kwargs) -> bytes:
        pass

    @abstractmethod
    def make_value(self) -> bytes:
        pass

    @staticmethod
    def from_bytes(*args, **kwargs) -> 'Data':
        pass


class Header(Data):
    PREFIX = b'HD'

    def __init__(self):
        self.version: int = 0
        self.block_height: int = 0
        self.revision: int = 0

    def make_key(self) -> bytes:
        return self.PREFIX

    def make_value(self) -> bytes:
        data = [
            self.version,
            self.block_height
        ]
        if self.version >= RC_DB_VERSION_2:
            # Added value in version 2
            data.append(self.revision)

        return MsgPackForIpc.dumps(data)

    @staticmethod
    def from_bytes(value: bytes) -> 'Header':
        data_list: list = MsgPackForIpc.loads(value)
        version: int = data_list[0]
        if version == RC_DB_VERSION_2:
            return Header._from_bytes_v2(data_list)
        elif version == RC_DB_VERSION_0:
            return Header._from_bytes_v1(data_list)

    @staticmethod
    def _from_bytes_v1(data_list: list) -> 'Header':
        obj = Header()
        obj.version: int = data_list[0]
        obj.block_height: int = data_list[1]
        return obj

    @staticmethod
    def _from_bytes_v2(data_list: list) -> 'Header':
        obj = Header()
        obj.version: int = data_list[0]
        obj.block_height: int = data_list[1]
        obj.revision: int = data_list[2]
        return obj

    def __str__(self):
        info: str = f"[{self.PREFIX}] version: {self.version}, block_height: {self.block_height} "

        if self.version >= RC_DB_VERSION_2:
            info += f"revision: {self.revision} "
        return info


class GovernanceVariable(Data):
    PREFIX = b'GV'

    def __init__(self):
        # key
        self.block_height: int = 0

        # value
        self.version: int = 0
        self.calculated_irep: int = 0
        self.reward_rep: int = 0
        self.config_main_prep_count: int = 0
        self.config_sub_prep_count: int = 0

    def make_key(self) -> bytes:
        block_height: bytes = self.block_height.to_bytes(8, byteorder=DATA_BYTE_ORDER)
        return self.PREFIX + block_height

    def make_value(self) -> bytes:
        data = [
            self.calculated_irep,
            self.reward_rep,
        ]
        if self.version >= RC_DB_VERSION_2:
            # Added value in version 2
            data.append(self.config_main_prep_count)
            data.append(self.config_sub_prep_count)

        return MsgPackForIpc.dumps(data)

    @staticmethod
    def from_bytes(key: bytes, value: bytes) -> 'GovernanceVariable':
        # Method for debugging
        data_list: list = MsgPackForIpc.loads(value)

        # need to be refactor
        if len(data_list) > 2:
            return GovernanceVariable._from_bytes_v2(key, data_list)
        else:
            return GovernanceVariable._from_bytes_v1(key, data_list)

    @staticmethod
    def _from_bytes_v1(key: bytes, data_list: list) -> 'GovernanceVariable':
        obj = GovernanceVariable()
        obj.block_height: int = int.from_bytes(key[2:], DATA_BYTE_ORDER)
        obj.version: int = RC_DB_VERSION_0
        obj.calculated_irep: int = data_list[0]
        obj.reward_rep: int = data_list[1]
        return obj

    @staticmethod
    def _from_bytes_v2(key: bytes, data_list: list) -> 'GovernanceVariable':
        obj = GovernanceVariable()
        obj.block_height: int = int.from_bytes(key[2:], DATA_BYTE_ORDER)
        obj.version: int = RC_DB_VERSION_2
        obj.calculated_irep: int = data_list[0]
        obj.reward_rep: int = data_list[1]
        obj.config_main_prep_count: int = data_list[2]
        obj.config_sub_prep_count: int = data_list[3]
        return obj

    def __str__(self):
        info: str = f"[{self.PREFIX}] key: {self.block_height}," \
                    f" calculated_irep: {self.calculated_irep}, reward_rep: {self.reward_rep}"
        if self.version >= RC_DB_VERSION_2:
            info += f"config_main_prep_count: {self.config_main_prep_count}, " \
                    f"config_sub_prep_count: {self.config_sub_prep_count}"
        return info


def make_block_produce_info_key(block_height: int) -> bytes:
    return BlockProduceInfoData.PREFIX + block_height.to_bytes(8, byteorder=DATA_BYTE_ORDER)


class BlockProduceInfoData(Data):
    PREFIX = b'BP'

    def __init__(self):
        # key
        self.block_height: int = 0

        # value
        self.block_generator: Optional['Address'] = None
        self.block_validator_list: Optional[List['Address']] = None

    def make_key(self) -> bytes:
        return make_block_produce_info_key(self.block_height)

    def make_value(self) -> bytes:
        data = [
            MsgPackForIpc.encode(self.block_generator),
            [MsgPackForIpc.encode(validator_address) for validator_address in self.block_validator_list]
        ]
        return MsgPackForIpc.dumps(data)

    @staticmethod
    def from_bytes(key: bytes, value: bytes) -> 'BlockProduceInfoData':
        # Method for debugging
        data_list: list = MsgPackForIpc.loads(value)
        obj = BlockProduceInfoData()
        obj.block_height: int = int.from_bytes(key[2:], DATA_BYTE_ORDER)
        obj.block_generator: 'Address' = MsgPackForIpc.decode(TypeTag.ADDRESS, data_list[0])

        obj.block_validator_list: list = [MsgPackForIpc.decode(TypeTag.ADDRESS, bytes_address)
                                          for bytes_address in data_list[1]]
        return obj

    def __str__(self):
        return f"[{self.PREFIX}] " \
               f"key: {self.block_height}, " \
               f"block_generator: {str(self.block_generator)}, " \
               f"block_validators: {[str(addr) for addr in self.block_validator_list]}"


class PRepsData(Data):
    PREFIX = b'PR'

    def __init__(self):
        # key
        self.block_height: int = 0

        # value
        self.total_delegation: int = 0
        self.prep_list: Optional[List['DelegationInfo']] = None

    def make_key(self) -> bytes:
        block_height: bytes = self.block_height.to_bytes(8, byteorder=DATA_BYTE_ORDER)
        return self.PREFIX + block_height

    def make_value(self) -> bytes:
        encoded_prep_list = [[MsgPackForIpc.encode(delegation_info.address),
                              MsgPackForIpc.encode(delegation_info.value)] for delegation_info in self.prep_list]
        data = [
            MsgPackForIpc.encode(self.total_delegation),
            encoded_prep_list
        ]
        return MsgPackForIpc.dumps(data)

    @staticmethod
    def from_bytes(key: bytes, value: bytes) -> 'PRepsData':
        # Method for debugging
        data_list: list = MsgPackForIpc.loads(value)
        obj = PRepsData()
        obj.prep_list = []
        obj.block_height: int = int.from_bytes(key[2:], DATA_BYTE_ORDER)
        obj.total_delegation = MsgPackForIpc.decode(TypeTag.INT, data_list[0])
        prep_list: list = [
            [MsgPackForIpc.decode(TypeTag.ADDRESS, delegation_info[0]),
             MsgPackForIpc.decode(TypeTag.INT, delegation_info[1])]
            for delegation_info in data_list[1]
        ]
        for prep in prep_list:
            del_info = DelegationInfo()
            del_info.address = prep[0]
            del_info.value = prep[1]
            obj.prep_list.append(del_info)
        return obj

    def __str__(self):
        return f"[{self.PREFIX}] " \
               f"key: {self.block_height}, total_delegation: {str(self.total_delegation)}"


class TxData(Data):
    PREFIX = b'TX'

    def __init__(self):
        self.address: 'Address' = None
        self.block_height: int = 0
        self.type: 'TxType' = TxType.INVALID
        self.data: 'Tx' = None

    def make_key(self, index: int) -> bytes:
        tx_index: bytes = index.to_bytes(8, byteorder=DATA_BYTE_ORDER)
        return self.PREFIX + tx_index

    def make_value(self) -> bytes:
        tx_type: 'TxType' = self.type
        tx_data: 'Tx' = self.data

        if isinstance(tx_data, Tx):
            tx_data_type = tx_data.get_type()
            if tx_type == TxType.INVALID:
                tx_type = tx_data_type
            elif tx_type != tx_data_type:
                raise InvalidParamsException(f"Mismatch TxType: {tx_type}")
        else:
            raise InvalidParamsException(f"Invalid TxData: {tx_data}")

        data = [
            MsgPackForIpc.encode(self.address),
            self.block_height,
            tx_type,
            tx_data.encode()
        ]

        return MsgPackForIpc.dumps(data)

    @staticmethod
    def from_bytes(value: bytes) -> 'TxData':
        # Method for debugging
        data_list: list = MsgPackForIpc.loads(value)
        obj = TxData()
        obj.address: 'Address' = MsgPackForIpc.decode(TypeTag.ADDRESS, data_list[0])
        obj.block_height: int = data_list[1]
        obj.type: 'TxType' = TxType(data_list[2])
        obj.data: 'Tx' = TxData._covert_tx_data(obj.type, data_list[3])
        return obj

    @staticmethod
    def _covert_tx_data(tx_type: 'TxType', data: tuple) -> Any:
        if tx_type == TxType.DELEGATION:
            return DelegationTx.decode(data)
        elif tx_type == TxType.PREP_REGISTER:
            return PRepRegisterTx.decode(data)
        elif tx_type == TxType.PREP_UNREGISTER:
            return PRepUnregisterTx.decode(data)
        else:
            raise InvalidParamsException(f"InvalidParams TxType: {tx_type}")


class Tx(object, metaclass=ABCMeta):
    @abstractmethod
    def get_type(self) -> 'TxType':
        pass

    @abstractmethod
    def encode(self) -> list:
        pass

    @staticmethod
    @abstractmethod
    def decode(data: list) -> Any:
        pass


class DelegationTx(Tx):
    def __init__(self):
        self.delegation_info: List['DelegationInfo'] = []

    def get_type(self) -> 'TxType':
        return TxType.DELEGATION

    def encode(self) -> tuple:
        data = [x.encode() for x in self.delegation_info]
        return MsgPackForIpc.encode_any(data)

    @staticmethod
    def decode(data: tuple) -> 'DelegationTx':
        data_list: list = MsgPackForIpc.decode_any(data)
        obj = DelegationTx()
        obj.delegation_info: list = [DelegationInfo.decode(x) for x in data_list]
        return obj


class DelegationInfo(object):
    def __init__(self):
        self.address: 'Address' = None
        self.value: int = None

    def encode(self) -> list:
        return [self.address, self.value]

    @staticmethod
    def decode(data: list) -> 'DelegationInfo':
        obj = DelegationInfo()
        obj.address: 'Address' = data[0]
        obj.value: int = data[1]
        return obj


class PRepRegisterTx(Tx):
    def __init__(self):
        pass

    def get_type(self) -> 'TxType':
        return TxType.PREP_REGISTER

    def encode(self) -> tuple:
        return MsgPackForIpc.encode_any(None)

    @staticmethod
    def decode(data: tuple) -> 'PRepRegisterTx':
        obj = PRepRegisterTx()
        return obj


class PRepUnregisterTx(Tx):
    def __init__(self):
        pass

    def get_type(self) -> 'TxType':
        return TxType.PREP_UNREGISTER

    def encode(self) -> tuple:
        return MsgPackForIpc.encode_any(None)

    @staticmethod
    def decode(data: tuple) -> 'PRepUnregisterTx':
        obj = PRepUnregisterTx()
        return obj
