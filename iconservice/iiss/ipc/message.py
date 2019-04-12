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

__all__ = (
    'MessageType',
    'VersionRequest', 'VersionResponse',
    'ClaimRequest', 'ClaimResponse',
    'QueryRequest', 'QueryResponse',
    'CalculateRequest', 'CalculateResponse',
    'CommitBlockRequest', 'CommitBlockResponse'
)

from abc import ABCMeta, abstractmethod
from enum import IntEnum
from threading import Lock

import msgpack

from ...base.address import Address
from ...utils.msgpack_for_ipc import MsgPackForIpc, TypeTag


class MessageType(IntEnum):
    NONE = -1
    VERSION = 0
    CLAIM = 1
    QUERY = 2
    CALCULATE = 3
    COMMIT_BLOCK = 4


class Request(metaclass=ABCMeta):
    _next_msg_id = 0
    _msg_id_lock = Lock()

    def __init__(self, msg_type: 'MessageType'):
        self.msg_type = msg_type
        self.msg_id = self._get_next_id()

    @classmethod
    def _get_next_id(cls) -> int:
        with cls._msg_id_lock:
            msg_id: int = cls._next_msg_id
            cls._next_msg_id = (msg_id + 1) % 0xffffffff

            return msg_id

    @abstractmethod
    def _get_payload(self) -> tuple:
        return None,

    def to_bytes(self) -> bytes:
        payload = self._get_payload()
        return msgpack.dumps(payload)


class Response(metaclass=ABCMeta):
    def __init__(self):
        pass

    @staticmethod
    @abstractmethod
    def from_list(items: list) -> 'Response':
        pass


class VersionRequest(Request):
    def __init__(self):
        super().__init__(MessageType.VERSION)

    def _get_payload(self) -> tuple:
        return self.msg_type, self.msg_id


class VersionResponse(Response):
    MSG_TYPE = MessageType.VERSION

    def __init__(self, msg_id: int, version: int):
        super().__init__()

        self.msg_id = msg_id
        self.version: int = version

    @staticmethod
    def from_list(items: list) -> 'VersionResponse':
        msg_id: int = items[1]
        version: int = items[2]

        return VersionResponse(msg_id, version)


class ClaimRequest(Request):
    def __init__(self, address: 'Address', block_height: int, block_hash):
        super().__init__(MessageType.CLAIM)

        self.address = address
        self.block_height = block_height
        self.block_hash = block_hash

    def _get_payload(self) -> tuple:
        return self.msg_type, \
               self.msg_id, \
               self.address.to_bytes_including_prefix(), \
               self.block_height, \
               self.block_hash


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

    @staticmethod
    def from_list(items: list) -> 'ClaimResponse':
        msg_id: int = items[1]
        address: 'Address' = MsgPackForIpc.decode(TypeTag.ADDRESS, items[2])
        block_height: int = items[3]
        block_hash: bytes = items[4]
        iscore: int = MsgPackForIpc.decode(TypeTag.INT, items[5])

        return ClaimResponse(msg_id, address, block_height, block_hash, iscore)


class QueryRequest(Request):
    def __init__(self, address: 'Address'):
        super().__init__(MessageType.QUERY)

        self.address = address

    def _get_payload(self) -> tuple:
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

    @staticmethod
    def from_list(items: list) -> 'QueryResponse':
        msg_id: int = items[1]
        address: 'Address' = MsgPackForIpc.decode(TypeTag.ADDRESS, items[2])
        iscore: int = MsgPackForIpc.decode(TypeTag.INT, items[3])
        block_height: int = items[4]

        return QueryResponse(msg_id, address, block_height, iscore)


class CalculateRequest(Request):
    def __init__(self, db_path: str, block_height: int):
        super().__init__(MessageType.CALCULATE)

        self.db_path = db_path
        self.block_height = block_height

    def _get_payload(self) -> tuple:
        return self.msg_type, self.msg_id, self.db_path, self.block_height


class CalculateResponse(Response):
    MSG_TYPE = MessageType.CALCULATE

    def __init__(self, msg_id: int, success: bool, block_height: int, state_hash: bytes):
        super().__init__()

        self.msg_id: int = msg_id
        self.success: bool = success
        self.block_height: int = block_height
        self.state_hash: bytes = state_hash

    @staticmethod
    def from_list(items: list) -> 'CalculateResponse':
        msg_id: int = items[1]
        success: bool = items[2]
        block_height: int = items[3]
        state_hash: bytes = items[4]

        return CalculateResponse(msg_id, success, block_height, state_hash)


class CommitBlockRequest(Request):
    def __init__(self, success: bool, block_height: int, block_hash: bytes):
        super().__init__(MessageType.COMMIT_BLOCK)

        self.success = success
        self.block_height = block_height
        self.block_hash = block_hash

    def _get_payload(self) -> tuple:
        return self.msg_type, self.msg_id, self.success, self.block_height, self.block_hash


class CommitBlockResponse(Response):
    MSG_TYPE = MessageType.COMMIT_BLOCK

    def __init__(self, msg_id: int, success: bool, block_height: int, block_hash: bytes):
        super().__init__()

        self.msg_id: int = msg_id
        self.success: bool = success
        self.block_height: int = block_height
        self.block_hash: bytes = block_hash

    @staticmethod
    def from_list(items: list) -> 'CommitBlockResponse':
        msg_id: int = items[1]
        success: bool = items[2]
        block_height: int = items[3]
        block_hash: bytes = items[4]

        return CommitBlockResponse(msg_id, success, block_height, block_hash)
