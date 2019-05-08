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

from ..base.exception import InvalidParamsException
from ..icon_constant import DATA_BYTE_ORDER
from ..utils.msgpack_for_ipc import MsgPackForIpc, TypeTag

if TYPE_CHECKING:
    from ..base.address import Address


class TxType(IntEnum):
    DELEGATION = 0
    PREP_REGISTER = 1
    PREP_UNREGISTER = 2
    INVALID = 99


class Data(object):
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
    _PREFIX = b'HD'

    def __init__(self):
        self.version: int = 0
        self.block_height: int = 0

    def make_key(self) -> bytes:
        return self._PREFIX

    def make_value(self) -> bytes:
        data = [
            self.version,
            self.block_height
        ]

        return MsgPackForIpc.dumps(data)

    @staticmethod
    def from_bytes(value: bytes) -> 'Header':
        data_list: list = MsgPackForIpc.loads(value)
        obj = Header()
        obj.version: int = data_list[0]
        obj.block_height: int = data_list[1]
        return obj

    def __str__(self):
        return f"[{self._PREFIX}] " \
            f"version: {self.version}, block_height: {self.block_height}"


class GovernanceVariable(Data):
    _PREFIX = b'GV'

    def __init__(self):
        # key
        self.block_height: int = 0

        # value
        self.calculated_incentive_rep: int = 0
        self.reward_rep: int = 0

    def make_key(self) -> bytes:
        block_height: bytes = self.block_height.to_bytes(8, byteorder=DATA_BYTE_ORDER)
        return self._PREFIX + block_height

    def make_value(self) -> bytes:
        data = [
            self.calculated_incentive_rep,
            self.reward_rep
        ]
        return MsgPackForIpc.dumps(data)

    @staticmethod
    def from_bytes(key: bytes, value: bytes) -> 'GovernanceVariable':
        data_list: list = MsgPackForIpc.loads(value)
        obj = GovernanceVariable()
        obj.block_height: int = int.from_bytes(key[2:], DATA_BYTE_ORDER)
        obj.calculated_incentive_rep: int = data_list[0]
        obj.reward_rep: int = data_list[1]
        return obj

    def __str__(self):
        return f"[{self._PREFIX}] " \
            f"key: {self.block_height}, calculated_incentive_rep: {self.calculated_incentive_rep}, reward_rep: {self.reward_rep}"


class BlockProduceInfoData(Data):
    _PREFIX = b'BP'

    def __init__(self):
        # key
        self.block_height: int = 0

        # value
        self.block_generator: Optional['Address'] = None
        self.block_validator_list: Optional[List['Address']] = None

    def make_key(self) -> bytes:
        block_height: bytes = self.block_height.to_bytes(8, byteorder=DATA_BYTE_ORDER)
        return self._PREFIX + block_height

    def make_value(self) -> bytes:
        data = [
            MsgPackForIpc.encode(self.block_generator),
            [MsgPackForIpc.encode(validator_address) for validator_address in self.block_validator_list]
        ]
        return MsgPackForIpc.dumps(data)

    @staticmethod
    def from_bytes(key: bytes, value: bytes) -> 'BlockProduceInfoData':
        data_list: list = MsgPackForIpc.loads(value)
        obj = BlockProduceInfoData()
        obj.block_height: int = int.from_bytes(key[2:], DATA_BYTE_ORDER)
        obj.block_generator: 'Address' = MsgPackForIpc.decode(TypeTag.ADDRESS, data_list[0])

        obj.block_validator_list: list = [MsgPackForIpc.decode(TypeTag.ADDRESS, bytes_address)
                                          for bytes_address in data_list[1]]
        return obj

    def __str__(self):
        return f"[{self._PREFIX}] " \
            f"key: {self.block_height}, block_generator: {str(self.block_generator)}"


class PRepsData(Data):
    _PREFIX = b'PR'

    def __init__(self):
        # key
        self.block_height: int = 0

        # value
        self.total_delegation: int = 0
        self.prep_list: Optional[List['DelegationInfo']] = None

    def make_key(self) -> bytes:
        block_height: bytes = self.block_height.to_bytes(8, byteorder=DATA_BYTE_ORDER)
        return self._PREFIX + block_height

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
        return f"[{self._PREFIX}] " \
            f"key: {self.block_height}, total_delegation: {str(self.total_delegation)}"


class TxData(Data):
    _PREFIX = b'TX'

    def __init__(self):
        self.address: 'Address' = None
        self.block_height: int = 0
        self.type: 'TxType' = TxType.INVALID
        self.data: 'Tx' = None

    def make_key(self, index: int) -> bytes:
        tx_index: bytes = index.to_bytes(8, byteorder=DATA_BYTE_ORDER)
        return self._PREFIX + tx_index

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
