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
from enum import unique, IntEnum
from struct import Struct
from typing import Optional

from .exception import InvalidParamsException
from ..icon_constant import DATA_BYTE_ORDER, DEFAULT_BYTE_SIZE
from ..utils.msgpack_for_db import MsgPackForDB


@unique
class BlockVersion(IntEnum):
    STRUCT = 0
    # change to msg pack and add 'step_used' field
    MSG_PACK = 1


class Block(object):
    """Block Information included in IconScoreContext
    """
    _VERSION = BlockVersion.MSG_PACK
    _STRUCT_PACKED_BYTES_SIZE = 129
    # leveldb account value structure (bigendian, 1 + 32 + 32 + 32 + 32 bytes)
    # version(1)
    # | height(DEFAULT_BYTE_SIZE)
    # | hash(DEFAULT_BYTE_SIZE)
    # | timestamp(DEFAULT_BYTE_SIZE)
    # | prev_hash(DEFAULT_BYTE_SIZE)

    _struct = Struct(f'>B{DEFAULT_BYTE_SIZE}s{DEFAULT_BYTE_SIZE}s{DEFAULT_BYTE_SIZE}s{DEFAULT_BYTE_SIZE}s')

    def __init__(self,
                 block_height: int,
                 block_hash: bytes,
                 timestamp: int,
                 prev_hash: Optional[bytes],
                 step_used: Optional[int]) -> None:
        """Constructor

        :param block_height: block height
        :param block_hash: block hash
        :param timestamp: block timestamp
        :param prev_hash: prev block hash
        """
        self._height = block_height
        self._hash = block_hash
        # unit: microsecond
        self._timestamp = timestamp
        self._prev_hash = prev_hash
        self._step_used = step_used

    @property
    def height(self) -> int:
        return self._height

    @property
    def hash(self) -> bytes:
        return self._hash

    @property
    def timestamp(self) -> int:
        return self._timestamp

    @property
    def prev_hash(self) -> bytes:
        return self._prev_hash

    @property
    def step_used(self) -> Optional[int]:
        return self._step_used

    @staticmethod
    def from_dict(params: dict):
        block_height = params.get('blockHeight')
        block_hash = params.get('blockHash')
        timestamp = params.get('timestamp', 0)
        prev_hash = params.get('prevBlockHash', b'\x00' * 32)

        return Block(block_height=block_height,
                     block_hash=block_hash,
                     timestamp=timestamp,
                     prev_hash=prev_hash,
                     step_used=0)

    @staticmethod
    def from_block(block: 'Block'):
        block_height = block.height
        block_hash = block.hash
        timestamp = block.timestamp
        prev_hash = block.prev_hash
        step_used = block.step_used
        return Block(block_height, block_hash, timestamp, prev_hash, step_used)

    @staticmethod
    def from_bytes(buf: bytes) -> 'Block':
        if len(buf) == Block._STRUCT_PACKED_BYTES_SIZE and buf[0] == BlockVersion.STRUCT:
            return Block._from_struct_packed_bytes(buf)
        else:
            return Block._from_msg_packed_bytes(buf)

    @staticmethod
    def _from_struct_packed_bytes(buf: bytes) -> 'Block':
        """Create Account object from bytes data

        :param buf: (bytes) bytes data including Account information
        :return: (Account) account object
        """
        byteorder = DATA_BYTE_ORDER

        version, block_height_bytes, block_hash_bytes,\
        timestamp_bytes, block_prev_hash_bytes = \
            Block._struct.unpack(buf)

        block_height = int.from_bytes(block_height_bytes, byteorder)
        block_hash = block_hash_bytes
        timestamp = int.from_bytes(timestamp_bytes, byteorder)
        byte_prev_hash = block_prev_hash_bytes

        if int(bytes.hex(byte_prev_hash), 16) == 0:
            byte_prev_hash = None
        prev_block_hash = byte_prev_hash

        # todo: consider using 0 as a step_used (not None)
        block = Block(block_height, block_hash, timestamp, prev_block_hash, None)
        return block

    @staticmethod
    def _from_msg_packed_bytes(buf: bytes) -> 'Block':
        data: list = MsgPackForDB.loads(buf)
        version: int = data[0]

        assert version <= Block._VERSION

        if version != BlockVersion.MSG_PACK:
            raise InvalidParamsException(f"Invalid block version: {version}")

        return Block(block_height=data[1],
                     block_hash=data[2],
                     timestamp=data[3],
                     prev_hash=data[4],
                     step_used=data[5])

    def to_bytes(self) -> bytes:
        data = [
            BlockVersion.MSG_PACK,
            self._height,
            self._hash,
            self._timestamp,
            self._prev_hash,
            self._step_used
        ]
        return MsgPackForDB.dumps(data)

    def __bytes__(self) -> bytes:
        """operator bytes() overriding

        :return: binary data including information of account object
        """
        return self.to_bytes()

    def __str__(self) -> str:
        hash_hex = 'None' if self._hash is None else f'0x{self._hash.hex()}'
        prev_hash_hex = \
            'None' if self._prev_hash is None else f'0x{self._prev_hash.hex()}'
        step_used = 'None' if self._step_used is None else self._step_used

        return f'height({self._height}) ' \
            f'hash({hash_hex}) ' \
            f'timestamp({self._timestamp}) ' \
            f'prev_hash({prev_hash_hex})' \
            f'step_used({step_used})' \
