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
from ..icon_constant import DATA_BYTE_ORDER, DEFAULT_BYTE_SIZE, Revision
from ..utils import bytes_to_hex
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
                 block_hash: Optional[bytes],
                 timestamp: int,
                 prev_hash: Optional[bytes],
                 cumulative_fee: int = 0) -> None:
        """Constructor

        :param block_height: block height
        :param block_hash: block hash
        :param timestamp: block timestamp
        :param prev_hash: prev block hash
        :param cumulative_fee: cumulative_fee
        """
        self._height = block_height
        self._hash = block_hash
        # unit: microsecond
        self._timestamp = timestamp
        self._prev_hash = prev_hash
        # set default value for compatibility with t-bears
        self.cumulative_fee = cumulative_fee

    def to_dict(self, casing: Optional[callable] = None) -> dict:
        """
        Returns properties as `dict`
        :return: a dict
        """
        new_dict = {}
        for key, value in self.__dict__.items():
            if key.startswith("_"):
                key = key[1:]
            new_dict[casing(key) if casing else key] = value

        return new_dict

    def __str__(self) -> str:
        return f"Block(height={self._height}, " \
               f"hash={bytes_to_hex(self._hash)}, " \
               f"prev_hash={bytes_to_hex(self._prev_hash)}, " \
               f"timestamp={self._timestamp}, " \
               f"cumulative_fee={self.cumulative_fee})"

    def __repr__(self) -> str:
        return self.__str__()

    def __eq__(self, other):
        return isinstance(other, Block) \
               and self._height == other._height \
               and self._timestamp == other._timestamp \
               and self._prev_hash == other._prev_hash \
               and self.cumulative_fee == other.cumulative_fee

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
                     cumulative_fee=0)

    @staticmethod
    def from_block(block: 'Block'):
        block_height = block.height
        block_hash = block.hash
        timestamp = block.timestamp
        prev_hash = block.prev_hash
        cumulative_fee = block.cumulative_fee
        return Block(block_height, block_hash, timestamp, prev_hash, cumulative_fee)

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

        version, block_height_bytes, block_hash_bytes, \
            timestamp_bytes, block_prev_hash_bytes = Block._struct.unpack(buf)

        block_height = int.from_bytes(block_height_bytes, byteorder)
        block_hash = block_hash_bytes
        timestamp = int.from_bytes(timestamp_bytes, byteorder)
        byte_prev_hash = block_prev_hash_bytes

        if int(bytes.hex(byte_prev_hash), 16) == 0:
            byte_prev_hash = None
        prev_block_hash = byte_prev_hash

        block = Block(block_height, block_hash, timestamp, prev_block_hash, 0)
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
                     cumulative_fee=data[5])

    def to_bytes(self, revision: int) -> bytes:
        if revision >= Revision.IISS.value:
            return self._to_msg_packed_bytes()
        else:
            return self._to_struct_packed_bytes()

    def _to_msg_packed_bytes(self) -> bytes:
        data = [
            BlockVersion.MSG_PACK.value,
            self._height,
            self._hash,
            self._timestamp,
            self._prev_hash,
            self.cumulative_fee
        ]
        return MsgPackForDB.dumps(data)

    def _to_struct_packed_bytes(self) -> bytes:
        """Convert block object to bytes

        :return: data including information of block object
        """
        byteorder = DATA_BYTE_ORDER
        # for extendability
        block_height_bytes = self._height.to_bytes(DEFAULT_BYTE_SIZE, byteorder)
        block_hash_bytes = self._hash
        timestamp_bytes = self._timestamp.to_bytes(DEFAULT_BYTE_SIZE, byteorder)

        tmp_prev_hash = self._prev_hash
        if tmp_prev_hash is None:
            tmp_prev_hash = bytes(DEFAULT_BYTE_SIZE)
        prev_block_hash_bytes = tmp_prev_hash

        return Block._struct.pack(
            BlockVersion.STRUCT,
            block_height_bytes,
            block_hash_bytes,
            timestamp_bytes,
            prev_block_hash_bytes)


# This predefined block is used to fix context.block.height access error before genesis block is synchronized.
NULL_BLOCK = Block(block_height=-1, block_hash=None, timestamp=0, prev_hash=None)
