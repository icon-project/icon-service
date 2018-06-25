# -*- coding: utf-8 -*-

# Copyright 2017-2018 theloop Inc.
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
from struct import Struct
from ..icon_config import DATA_BYTE_ORDER, BALANCE_BYTE_SIZE


class Block(object):
    """Block Information included in IconScoreContext
    """

    _VERSION = 0
    # leveldb account value structure (bigendian, 1 + 32 + 32 + 32  bytes)
    # version(1) | height(BALANCE_BYTE_SIZE) | hash(BALANCE_BYTE_SIZE) | timestamp(BALANCE_BYTE_SIZE)
    _struct = Struct(f'>c{BALANCE_BYTE_SIZE}s{BALANCE_BYTE_SIZE}s{BALANCE_BYTE_SIZE}s')

    def __init__(self, block_height: int, block_hash: str, timestamp: int) -> None:
        """Constructor

        :param block_height: block height
        :param block_hash: block hash
        """
        self._height = block_height
        self._hash = block_hash
        # unit: microsecond
        self._timestamp = timestamp

    @property
    def height(self) -> int:
        return self._height

    @property
    def hash(self) -> str:
        return self._hash

    @property
    def timestamp(self) -> int:
        return self._timestamp

    @staticmethod
    def from_dict(params: dict):
        block_height = params.get('blockHeight')
        block_hash = params.get('blockHash')
        timestamp = params.get('timestamp')
        return Block(block_height, block_hash, timestamp)

    @staticmethod
    def from_block(block: 'Block'):
        block_height = block.height
        block_hash = block.hash
        timestamp = block.timestamp
        return Block(block_height, block_hash, timestamp)

    @staticmethod
    def from_bytes(buf: bytes) -> 'Block':
        """Create Account object from bytes data

        :param buf: (bytes) bytes data including Account information
        :return: (Account) account object
        """
        byteorder = DATA_BYTE_ORDER

        version_bytes, block_height_bytes, block_hash_bytes, timestamp_bytes = \
            Block._struct.unpack(buf)

        # version = int.from_bytes(version_bytes, byteorder)
        block_height = int.from_bytes(block_height_bytes, byteorder)
        block_hash = bytes.hex(block_hash_bytes)
        timestamp = int.from_bytes(timestamp_bytes, byteorder)

        block = Block(block_height, block_hash, timestamp)
        return block

    def to_bytes(self) -> bytes:
        """Convert block object to bytes

        :return: data including information of block object
        """

        byteorder = DATA_BYTE_ORDER
        # for extendability
        version_bytes = self._VERSION.to_bytes(1, byteorder)
        block_height_bytes = self._height.to_bytes(BALANCE_BYTE_SIZE, byteorder)
        block_hash_bytes = bytes.fromhex(self._hash[2:])
        timestamp_bytes = self._timestamp.to_bytes(BALANCE_BYTE_SIZE, byteorder)

        return Block._struct.pack(
            version_bytes,
            block_height_bytes,
            block_hash_bytes,
            timestamp_bytes)

    def __bytes__(self) -> bytes:
        """operator bytes() overriding

        :return: binary data including information of account object
        """
        return self.to_bytes()
