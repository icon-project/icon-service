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
from typing import Any, TYPE_CHECKING

from ..icon_constant import DATA_BYTE_ORDER
from .iiss_data_converter import IissDataConverter, TypeTag
from ..base.exception import InvalidParamsException

if TYPE_CHECKING:
    from ..base.address import Address


class IissTxType(IntEnum):
    DELEGATION = 0
    PREP_REGISTER = 1
    PREP_UNREGISTER = 2
    INVALID = 99


class IissData(object):
    @abstractmethod
    def make_key(self) -> bytes:
        pass

    @abstractmethod
    def make_value(self) -> bytes:
        pass

    @staticmethod
    def get_value(**kwargs) -> 'IissData':
        pass


class IissHeader(IissData):
    _prefix = 'HD'

    def __init__(self):
        self.version: int = 0
        self.block_height: int = 0

    def make_key(self) -> bytes:
        return IissDataConverter.encode(self._prefix)

    def make_value(self) -> bytes:
        data = [
            self.version,
            self.block_height
        ]

        return IissDataConverter.dumps(data)

    @staticmethod
    def get_value(data: bytes) -> 'IissHeader':
        data_list: list = IissDataConverter.loads(data)
        obj = IissHeader()
        obj.version: int = data_list[0]
        obj.block_height: int = data_list[1]
        return obj


class IissGovernanceVariable(IissData):
    _prefix = 'gv'

    def __init__(self):
        # key
        self.block_height: int = 0

        # value
        self.icx_price: int = 0
        self.incentive_rep: int = 0
        self.reward_rep: int = 0

    def make_key(self) -> bytes:
        prefix: bytes = IissDataConverter.encode(self._prefix)
        block_height: bytes = self.block_height.to_bytes(8, byteorder=DATA_BYTE_ORDER)
        return prefix + block_height

    def make_value(self) -> bytes:
        data = [
            self.icx_price,
            self.incentive_rep,
            self.reward_rep
        ]
        return IissDataConverter.dumps(data)

    @staticmethod
    def get_value(key: bytes, data: bytes) -> 'IissGovernanceVariable':
        data_list: list = IissDataConverter.loads(data)
        obj = IissGovernanceVariable()
        obj.block_height: int = int.from_bytes(key[2:], DATA_BYTE_ORDER)
        obj.icx_price: int = data_list[0]
        obj.incentive_rep: int = data_list[1]
        obj.reward_rep: int = data_list[2]
        return obj


class PrepsData(IissData):
    _prefix = 'prep'

    def __init__(self):
        # key
        self.block_height: int = 0

        # value
        self.block_generator: 'Address' = None
        # todo: need to change type check
        self.block_validator_list: list = None

    def make_key(self) -> bytes:
        prefix: bytes = IissDataConverter.encode(self._prefix)
        block_height: bytes = self.block_height.to_bytes(8, byteorder=DATA_BYTE_ORDER)
        return prefix + block_height

    def make_value(self) -> bytes:

        data = [
            IissDataConverter.encode(self.block_generator),
            [IissDataConverter.encode(validator_address) for validator_address in self.block_validator_list]
        ]
        return IissDataConverter.dumps(data)

    @staticmethod
    def get_value(key: bytes, data: bytes) -> 'PrepsData':
        data_list: list = IissDataConverter.loads(data)
        obj = PrepsData()
        obj.block_height: int = int.from_bytes(key[4:], DATA_BYTE_ORDER)
        obj.block_generator: 'Address' = IissDataConverter.decode(TypeTag.ADDRESS, data_list[0])

        obj.block_validator_list: list = [IissDataConverter.decode(TypeTag.ADDRESS, bytes_address)
                                          for bytes_address in data_list[1]]
        return obj


class IissTxData(IissData):
    _prefix = 'TX'

    def __init__(self):
        # key
        self.index: int = 0

        # value
        self.address: 'Address' = None
        self.block_height: int = 0
        self.type: 'IissTxType' = IissTxType.INVALID
        self.data: 'IissTx' = None

    def make_key(self) -> bytes:
        prefix: bytes = IissDataConverter.encode(self._prefix)
        tx_index: bytes = self.index.to_bytes(8, byteorder=DATA_BYTE_ORDER)
        return prefix + tx_index

    def make_value(self) -> bytes:
        tx_type: 'IissTxType' = self.type
        tx_data: 'IissTx' = self.data

        if isinstance(tx_data, IissTx):
            tx_data_type = tx_data.get_type()
            if tx_type == IissTxType.INVALID:
                tx_type = tx_data_type
            elif tx_type != tx_data_type:
                raise InvalidParamsException(f"Mismatch TxType: {tx_type}")
        else:
            raise InvalidParamsException(f"Invalid TxData: {tx_data}")

        data = [
            IissDataConverter.encode(self.address),
            self.block_height,
            tx_type,
            tx_data.encode()
        ]

        return IissDataConverter.dumps(data)

    @staticmethod
    def get_value(tx_index: int, data: bytes) -> 'IissTxData':
        data_list: list = IissDataConverter.loads(data)
        obj = IissTxData()
        obj.index: int = tx_index
        obj.address: 'Address' = IissDataConverter.decode(TypeTag.ADDRESS, data_list[0])
        obj.block_height: int = data_list[1]
        obj.type: 'IissTxType' = IissTxType(data_list[2])
        obj.data: 'IissTx' = IissTxData._covert_tx_data(obj.type, data_list[3])
        return obj

    @staticmethod
    def _covert_tx_data(tx_type: 'IissTxType', data: tuple) -> Any:
        if tx_type == IissTxType.DELEGATION:
            return DelegationTx.decode(data)
        elif tx_type == IissTxType.PREP_REGISTER:
            return PRepRegisterTx.decode(data)
        elif tx_type == IissTxType.PREP_UNREGISTER:
            return PRepUnregisterTx.decode(data)
        else:
            raise InvalidParamsException(f"InvalidParams TxType: {tx_type}")


class IissTx(object, metaclass=ABCMeta):
    @abstractmethod
    def get_type(self) -> 'IissTxType':
        pass

    @abstractmethod
    def encode(self) -> list:
        pass

    @staticmethod
    @abstractmethod
    def decode(data: list) -> Any:
        pass


class DelegationTx(IissTx):
    def __init__(self):
        self.delegation_info: list = []

    def get_type(self) -> 'IissTxType':
        return IissTxType.DELEGATION

    def encode(self) -> tuple:
        data = [x.encode() for x in self.delegation_info]
        return IissDataConverter.encode_any(data)

    @staticmethod
    def decode(data: tuple) -> 'DelegationTx':
        data_list: list = IissDataConverter.decode_any(data)
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


class PRepRegisterTx(IissTx):
    def __init__(self):
        pass

    def get_type(self) -> 'IissTxType':
        return IissTxType.PREP_REGISTER

    def encode(self) -> tuple:
        return IissDataConverter.encode_any(None)

    @staticmethod
    def decode(data: tuple) -> 'PRepRegisterTx':
        obj = PRepRegisterTx()
        return obj


class PRepUnregisterTx(IissTx):
    def __init__(self):
        pass

    def get_type(self) -> 'IissTxType':
        return IissTxType.PREP_UNREGISTER

    def encode(self) -> tuple:
        return IissDataConverter.encode_any(None)

    @staticmethod
    def decode(data: tuple) -> 'PRepUnregisterTx':
        obj = PRepUnregisterTx()
        return obj
