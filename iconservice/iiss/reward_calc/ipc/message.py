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

import msgpack

from iconservice.base.address import Address
from iconservice.utils import bytes_to_hex
from iconservice.utils.msgpack_for_ipc import MsgPackForIpc, TypeTag

_next_msg_id: int = 1


def reset_next_msg_id(msg_id: int):
    """Only used for unittest

    :param msg_id:
    :return:
    """
    global _next_msg_id
    _next_msg_id = msg_id


def _get_next_msg_id() -> int:
    global _next_msg_id

    msg_id: int = _next_msg_id
    _next_msg_id = max(1, (msg_id + 1) % 0xffffffff)

    return msg_id


class MessageType(IntEnum):
    NONE = -1
    VERSION = 0
    CLAIM = 1
    QUERY = 2
    CALCULATE = 3
    COMMIT_BLOCK = 4
    COMMIT_CLAIM = 5
    QUERY_CALCULATE_STATUS = 6
    QUERY_CALCULATE_RESULT = 7
    ROLLBACK = 8
    INIT = 9
    READY = 100
    CALCULATE_DONE = 101


class Request(metaclass=ABCMeta):
    def __init__(self, msg_type: 'MessageType'):
        self.msg_type = msg_type
        self.msg_id = _get_next_msg_id()

    @abstractmethod
    def _to_list(self) -> tuple:
        return None,

    def to_bytes(self) -> bytes:
        items: tuple = self._to_list()
        return msgpack.dumps(items)


class Response(metaclass=ABCMeta):
    def __init__(self):
        self.msg_id = -1

    @staticmethod
    @abstractmethod
    def from_list(items: list) -> 'Response':
        pass

    def is_notification(self):
        return self.msg_id == 0


class VersionRequest(Request):
    def __init__(self):
        super().__init__(MessageType.VERSION)

    def _to_list(self) -> tuple:
        return self.msg_type, self.msg_id

    def __str__(self) -> str:
        return f"{self.msg_type.name}({self.msg_id})"


class VersionResponse(Response):
    MSG_TYPE = MessageType.VERSION

    def __init__(self, msg_id: int, version: int, block_height: int):
        super().__init__()

        self.msg_id: int = msg_id
        self.version: int = version
        self.block_height: int = block_height

    def __str__(self):
        return f"VERSION({self.msg_id}, {self.version}, {self.block_height})"

    @staticmethod
    def from_list(items: list) -> 'VersionResponse':
        msg_id: int = items[1]
        payload: list = items[2]

        version: int = payload[0]
        block_height: int = payload[1]

        return VersionResponse(msg_id, version, block_height)


class ClaimRequest(Request):
    def __init__(self, address: 'Address', block_height: int, block_hash: bytes, tx_index: int, tx_hash: bytes):
        super().__init__(MessageType.CLAIM)

        self.address = address
        self.block_height = block_height
        self.block_hash = block_hash
        self.tx_index = tx_index
        self.tx_hash = tx_hash

    def _to_list(self) -> tuple:
        return self.msg_type, self.msg_id,\
               (
                   self.address.to_bytes_including_prefix(),
                   self.block_height, self.block_hash,
                   self.tx_index, self.tx_hash
               )

    def __str__(self) -> str:
        return \
            f"{self.msg_type.name}({self.msg_id}, " \
            f"{self.address}, " \
            f"{self.block_height}, {bytes_to_hex(self.block_hash)}), " \
            f"{self.tx_index}, {bytes_to_hex(self.tx_hash)}"


class ClaimResponse(Response):
    MSG_TYPE = MessageType.CLAIM

    def __init__(self, msg_id: int, address: 'Address',
                 block_height: int, block_hash: bytes,
                 tx_index: int, tx_hash: bytes,
                 iscore: int):
        super().__init__()

        self.msg_id = msg_id
        self.address: 'Address' = address
        self.block_height: int = block_height
        self.block_hash: bytes = block_hash
        self.tx_index: int = tx_index
        self.tx_hash: bytes = tx_hash
        self.iscore: int = iscore

    def __str__(self) -> str:
        return \
            f"CLAIM({self.msg_id}, " \
            f"{self.address}, " \
            f"{self.block_height}, {bytes_to_hex(self.block_hash)}, " \
            f"{self.tx_index}, {bytes_to_hex(self.tx_hash)}, " \
            f"{self.iscore})"

    @staticmethod
    def from_list(items: list) -> 'ClaimResponse':
        msg_id: int = items[1]
        payload: list = items[2]

        address: 'Address' = MsgPackForIpc.decode(TypeTag.ADDRESS, payload[0])
        block_height: int = payload[1]
        block_hash: bytes = payload[2]
        tx_index: int = payload[3]
        tx_hash: bytes = payload[4]
        iscore: int = MsgPackForIpc.decode(TypeTag.INT, payload[5])

        return ClaimResponse(msg_id, address, block_height, block_hash, tx_index, tx_hash, iscore)


class CommitClaimRequest(Request):
    """Send the result of claimIScore tx to reward calculator
        No response for CommitClaimRequest
    """
    def __init__(self, success: bool, address: 'Address',
                 block_height: int, block_hash: bytes,
                 tx_index: int, tx_hash: bytes):
        super().__init__(MessageType.COMMIT_CLAIM)

        self.success = success
        self.address = address
        self.block_height = block_height
        self.block_hash = block_hash
        self.tx_index = tx_index
        self.tx_hash = tx_hash

    def _to_list(self) -> tuple:
        return self.msg_type, self.msg_id, \
               (
                   self.success,
                   self.address.to_bytes_including_prefix(),
                   self.block_height,
                   self.block_hash,
                   self.tx_index,
                   self.tx_hash
               )

    def __str__(self) -> str:
        return \
            f"{self.msg_type.name}(" \
            f"{self.msg_id}, " \
            f"{self.success}, " \
            f"{self.address}, " \
            f"{self.block_height}, " \
            f"{bytes_to_hex(self.block_hash)}, " \
            f"{self.tx_index}, " \
            f"{bytes_to_hex(self.tx_hash)}" \
            f")"


class CommitClaimResponse(Response):
    MSG_TYPE = MessageType.COMMIT_CLAIM

    def __init__(self, msg_id: int):
        super().__init__()

        self.msg_id = msg_id

    def __str__(self) -> str:
        return f"COMMIT_CLAIM({self.msg_id})"

    @staticmethod
    def from_list(items: list) -> 'CommitClaimResponse':
        msg_id: int = items[1]

        return CommitClaimResponse(msg_id)


class QueryCalculateStatusRequest(Request):
    def __init__(self):
        super().__init__(MessageType.QUERY_CALCULATE_STATUS)

    def _to_list(self) -> tuple:
        return self.msg_type, self.msg_id

    def __str__(self) -> str:
        return f"{self.msg_type.name}({self.msg_id})"


class QueryCalculateStatusResponse(Response):
    MSG_TYPE = MessageType.QUERY_CALCULATE_STATUS

    def __init__(self, msg_id: int, status: int, block_height: int):
        super().__init__()

        self.msg_id: int = msg_id
        self.status: int = status
        self.block_height: int = block_height

    def __str__(self) -> str:
        return f"QUERY_CALCULATE_STATUS_RESPONSE({self.msg_id}, {self.status}, {self.block_height})"

    @staticmethod
    def from_list(items: list) -> 'QueryCalculateStatusResponse':
        msg_id: int = items[1]
        payload: list = items[2]

        status: int = payload[0]
        block_height: int = payload[1]

        return QueryCalculateStatusResponse(msg_id, status, block_height)


class QueryCalculateResultRequest(Request):

    def __init__(self, block_height):
        super().__init__(MessageType.QUERY_CALCULATE_RESULT)

        self.block_height = block_height

    def _to_list(self) -> tuple:
        return self.msg_type, self.msg_id, self.block_height

    def __str__(self) -> str:
        return f"{self.msg_type.name}({self.msg_id},{self.block_height})"


class QueryCalculateResultResponse(Response):
    MSG_TYPE = MessageType.QUERY_CALCULATE_RESULT

    def __init__(self, msg_id: int, status: int, block_height: int, iscore: int, state_hash: bytes):
        super().__init__()

        self.msg_id = msg_id
        self.status = status
        self.block_height = block_height
        self.iscore = iscore
        self.state_hash = state_hash

    def __str__(self):
        return f"QUERY_CALCULATE_RESULT_RESPONSE({self.msg_id}, " \
            f"{self.status}, {self.block_height}, {self.iscore}, {bytes_to_hex(self.state_hash)})"

    @staticmethod
    def from_list(items: list) -> 'QueryCalculateResultResponse':
        msg_id: int = items[1]
        payload: list = items[2]

        status: int = payload[0]
        block_hegiht: int = payload[1]
        iscore: int = MsgPackForIpc.decode(TypeTag.INT, payload[2])
        state_hash: bytes = payload[3]

        return QueryCalculateResultResponse(msg_id, status, block_hegiht, iscore, state_hash)


class QueryRequest(Request):
    """queryIScore
    """

    def __init__(self, address: 'Address'):
        super().__init__(MessageType.QUERY)

        self.address = address

    def __str__(self) -> str:
        return f"{self.msg_type.name}({self.msg_id}, {self.address})"

    def _to_list(self) -> tuple:
        return self.msg_type, \
               self.msg_id, \
               self.address.to_bytes_including_prefix()


class QueryResponse(Response):
    MSG_TYPE = MessageType.QUERY

    def __init__(self, msg_id: int,
                 address: 'Address', block_height: int, iscore: int):
        super().__init__()

        self.msg_id: int = msg_id
        self.address: 'Address' = address
        self.block_height: int = block_height
        self.iscore: int = iscore

    def __str__(self) -> str:
        return f"QUERY({self.msg_id}, {self.address}, {self.block_height}, {self.iscore})"

    @staticmethod
    def from_list(items: list) -> 'QueryResponse':
        msg_id: int = items[1]
        payload: list = items[2]

        address: 'Address' = MsgPackForIpc.decode(TypeTag.ADDRESS, payload[0])
        iscore: int = MsgPackForIpc.decode(TypeTag.INT, payload[1])
        block_height: int = payload[2]

        return QueryResponse(msg_id, address, block_height, iscore)


class CalculateRequest(Request):
    def __init__(self, db_path: str, block_height: int):
        super().__init__(MessageType.CALCULATE)

        self.db_path = db_path
        self.block_height = block_height

    def __str__(self) -> str:
        return f"{self.msg_type.name}({self.msg_id}, {self.db_path}, {self.block_height})"

    def _to_list(self) -> tuple:
        return self.msg_type, self.msg_id, (self.db_path, self.block_height)


class CalculateResponse(Response):
    MSG_TYPE = MessageType.CALCULATE

    def __init__(self, msg_id: int, status: int, block_height: int):
        super().__init__()

        self.msg_id: int = msg_id
        self.status: int = status
        self.block_height: int = block_height

    def __str__(self) -> str:
        return f"CALCULATE({self.msg_id}, {self.status}, {self.block_height})"

    @staticmethod
    def from_list(items: list) -> 'CalculateResponse':
        msg_id: int = items[1]
        payload: list = items[2]

        status: int = payload[0]
        block_height: int = payload[1]

        return CalculateResponse(msg_id, status, block_height)


class CommitBlockRequest(Request):
    def __init__(self, success: bool, block_height: int, block_hash: bytes):
        super().__init__(MessageType.COMMIT_BLOCK)

        self.success = success
        self.block_height = block_height
        self.block_hash = block_hash

    def __str__(self):
        return f"{self.msg_type.name}({self.msg_id}, " \
            f"{self.success}, {self.block_height}, {bytes_to_hex(self.block_hash)})"

    def _to_list(self) -> tuple:
        return self.msg_type, self.msg_id, (self.success, self.block_height, self.block_hash)


class CommitBlockResponse(Response):
    MSG_TYPE = MessageType.COMMIT_BLOCK

    def __init__(self, msg_id: int, success: bool, block_height: int, block_hash: bytes):
        super().__init__()

        self.msg_id: int = msg_id
        self.success: bool = success
        self.block_height: int = block_height
        self.block_hash: bytes = block_hash

    def __str__(self):
        return f"COMMIT_BLOCK({self.msg_id}, {self.success}, {self.block_height}, {bytes_to_hex(self.block_hash)})"

    @staticmethod
    def from_list(items: list) -> 'CommitBlockResponse':
        msg_id: int = items[1]
        payload: list = items[2]

        success: bool = payload[0]
        block_height: int = payload[1]
        block_hash: bytes = payload[2]

        return CommitBlockResponse(msg_id, success, block_height, block_hash)


class InitRequest(Request):
    def __init__(self, block_height: int):
        super().__init__(MessageType.INIT)

        self.block_height = block_height

    def __str__(self):
        return f"{self.msg_type.name}({self.msg_id}, {self.block_height})"

    def _to_list(self) -> tuple:
        return self.msg_type, self.msg_id, self.block_height


class InitResponse(Response):
    MSG_TYPE = MessageType.INIT

    def __init__(self, msg_id: int, success: bool, block_height: int):
        super().__init__()

        self.msg_id: int = msg_id
        self.success: bool = success
        self.block_height: int = block_height

    def __str__(self):
        return f"INIT({self.msg_id}, {self.success}, {self.block_height})"

    @staticmethod
    def from_list(items: list) -> 'InitResponse':
        msg_id: int = items[1]
        payload: list = items[2]

        success: bool = payload[0]
        block_height: int = payload[1]

        return InitResponse(msg_id, success, block_height)


class RollbackRequest(Request):
    def __init__(self, block_height: int, block_hash: bytes):
        super().__init__(MessageType.ROLLBACK)

        self.block_height = block_height
        self.block_hash = block_hash

    def __str__(self):
        return f"{self.msg_type.name}({self.msg_id}, " \
               f"{self.block_height}, {bytes_to_hex(self.block_hash)})"

    def _to_list(self) -> tuple:
        return self.msg_type, self.msg_id, (self.block_height, self.block_hash)


class RollbackResponse(Response):
    MSG_TYPE = MessageType.ROLLBACK

    def __init__(self, msg_id: int, success: bool, block_height: int, block_hash: bytes):
        super().__init__()

        self.msg_id: int = msg_id
        self.success: bool = success
        self.block_height: int = block_height
        self.block_hash: bytes = block_hash

    def __str__(self):
        return f"ROLLBACK({self.msg_id}, {self.success}, {self.block_height}, {bytes_to_hex(self.block_hash)})"

    @staticmethod
    def from_list(items: list) -> 'RollbackResponse':
        msg_id: int = items[1]
        payload: list = items[2]

        success: bool = payload[0]
        block_height: int = payload[1]
        block_hash: bytes = payload[2]

        return RollbackResponse(msg_id, success, block_height, block_hash)


class ReadyNotification(Response):
    MSG_TYPE = MessageType.READY

    def __init__(self, msg_id: int, version: int, block_height: int, block_hash: bytes):
        super().__init__()

        self.msg_id = msg_id
        self.version = version
        self.block_height = block_height
        self.block_hash = block_hash

    def __str__(self):
        return f"READY({self.msg_id}, {self.version}, {self.block_height}, {bytes_to_hex(self.block_hash)})"

    @staticmethod
    def from_list(items: list) -> 'ReadyNotification':
        msg_id: int = items[1]
        payload: list = items[2]

        version: int = payload[0]
        block_height: int = payload[1]
        block_hash: bytes = payload[2]

        return ReadyNotification(msg_id, version, block_height, block_hash)


class CalculateDoneNotification(Response):
    MSG_TYPE = MessageType.CALCULATE_DONE

    def __init__(self, msg_id: int, success: bool, block_height: int, iscore: int, state_hash: bytes):
        super().__init__()

        self.msg_id = msg_id
        self.success = success
        self.block_height = block_height
        self.iscore = iscore
        self.state_hash = state_hash

    def __str__(self):
        return f"CALCULATE_DONE({self.msg_id}, " \
            f"{self.success}, {self.block_height}, {self.iscore}, {bytes_to_hex(self.state_hash)})"

    @staticmethod
    def from_list(items: list) -> 'CalculateDoneNotification':
        msg_id: int = items[1]
        payload: list = items[2]

        success: bool = payload[0]
        block_hegiht: int = payload[1]
        iscore: int = MsgPackForIpc.decode(TypeTag.INT, payload[2])
        state_hash: bytes = payload[3]

        return CalculateDoneNotification(msg_id, success, block_hegiht, iscore, state_hash)


class NoneRequest(Request):
    """This request is used to stop ipc channel on iconservice stopping
    """
    def __init__(self):
        super().__init__(MessageType.NONE)

    def __str__(self):
        return f"NONE_REQUEST({self.msg_id})"

    def _to_list(self) -> tuple:
        return self.msg_type, self.msg_id


class NoneResponse(Response):
    MSG_TYPE = MessageType.NONE

    def __init__(self, msg_id: int):
        super().__init__()
        self.msg_id = msg_id

    def __str__(self):
        return f"NONE_RESPONSE({self.msg_id})"

    @staticmethod
    def from_list(items: list) -> 'NoneResponse':
        msg_id: int = items[1]
        return NoneResponse(msg_id)
