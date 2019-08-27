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
from iconservice.utils.msgpack_for_ipc import MsgPackForIpc, TypeTag

_next_msg_id: int = 1


def _get_next_id() -> int:
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


class Request(metaclass=ABCMeta):
    def __init__(self, msg_type: 'MessageType'):
        self.msg_type = msg_type
        self.msg_id = _get_next_id()

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
    def __init__(self, address: 'Address', block_height: int, block_hash):
        super().__init__(MessageType.CLAIM)

        self.address = address
        self.block_height = block_height
        self.block_hash = block_hash

    def _to_list(self) -> tuple:
        return self.msg_type, self.msg_id,\
               (self.address.to_bytes_including_prefix(), self.block_height, self.block_hash)

    def __str__(self) -> str:
        return f"{self.msg_type.name}({self.msg_id}, {self.address}, {self.block_height}, {self.block_hash.hex()})"


class ClaimResponse(Response):
    MSG_TYPE = MessageType.CLAIM

    def __init__(self, msg_id: int, address: 'Address',
                 block_height: int, block_hash: bytes, iscore: int):
        super().__init__()

        self.msg_id = msg_id
        self.address: 'Address' = address
        self.block_height: int = block_height
        self.block_hash: bytes = block_hash
        self.iscore: int = iscore

    def __str__(self) -> str:
        return f"CLAIM({self.msg_id}, {self.address}, {self.block_height}, {self.block_hash.hex()}, {self.iscore})"

    @staticmethod
    def from_list(items: list) -> 'ClaimResponse':
        msg_id: int = items[1]
        payload: list = items[2]

        address: 'Address' = MsgPackForIpc.decode(TypeTag.ADDRESS, payload[0])
        block_height: int = payload[1]
        block_hash: bytes = payload[2]
        iscore: int = MsgPackForIpc.decode(TypeTag.INT, payload[3])

        return ClaimResponse(msg_id, address, block_height, block_hash, iscore)


class CommitClaimRequest(Request):
    """Send the result of claimIScore tx to reward calculator
        No response for CommitClaimRequest
    """
    def __init__(self, success: bool, address: 'Address', block_height: int, block_hash: bytes):
        super().__init__(MessageType.COMMIT_CLAIM)

        self.success = success
        self.address = address
        self.block_height = block_height
        self.block_hash = block_hash

    def _to_list(self) -> tuple:
        return self.msg_type, self.msg_id,\
               (self.success, self.address.to_bytes_including_prefix(), self.block_height, self.block_hash)

    def __str__(self) -> str:
        return f"{self.msg_type.name}" \
                f"({self.msg_id}, {self.success}, {self.address}, {self.block_height}, {self.block_hash.hex()})"


class QueryRequest(Request):
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

    def __init__(self, msg_id: int, success: bool, block_height: int, iscore: int, state_hash: bytes):
        super().__init__()

        self.msg_id: int = msg_id
        self.success: bool = success
        self.block_height: int = block_height
        self.iscore: int = iscore
        self.state_hash: bytes = state_hash

    def __str__(self) -> str:
        return f"CALCULATE({self.msg_id}, {self.success}, {self.block_height}, {self.iscore}, {self.state_hash})"

    @staticmethod
    def from_list(items: list) -> 'CalculateResponse':
        msg_id: int = items[1]
        payload: list = items[2]

        success: bool = payload[0]
        block_height: int = payload[1]
        iscore: int = MsgPackForIpc.decode(TypeTag.INT, payload[2])
        state_hash: bytes = payload[3]

        return CalculateResponse(msg_id, success, block_height, iscore, state_hash)


class CommitBlockRequest(Request):
    def __init__(self, success: bool, block_height: int, block_hash: bytes):
        super().__init__(MessageType.COMMIT_BLOCK)

        self.success = success
        self.block_height = block_height
        self.block_hash = block_hash

    def __str__(self):
        return f"{self.msg_type.name}({self.msg_id}, {self.success}, {self.block_height}, {self.block_hash})"

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
        return f"COMMIT_BLOCK({self.msg_id}, {self.success}, {self.block_height}, {self.block_hash})"

    @staticmethod
    def from_list(items: list) -> 'CommitBlockResponse':
        msg_id: int = items[1]
        payload: list = items[2]

        success: bool = payload[0]
        block_height: int = payload[1]
        block_hash: bytes = payload[2]

        return CommitBlockResponse(msg_id, success, block_height, block_hash)


class NoneRequest(Request):
    def __init__(self):
        super().__init__(MessageType.NONE)

    def _to_list(self) -> tuple:
        return self.msg_type, self.msg_id


class NoneResponse(Response):
    MSG_TYPE = MessageType.NONE

    def __init__(self, msg_id: int):
        super().__init__()
        self.msg_id = msg_id

    @staticmethod
    def from_list(items: list) -> 'NoneResponse':
        msg_id: int = items[1]
        return NoneResponse(msg_id)
