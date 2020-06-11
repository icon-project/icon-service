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
from enum import Flag, auto

from .batch import BlockBatchValue
from ..icon_constant import DATA_BYTE_ORDER
from ..iiss.reward_calc.msg_data import TxData
from ..iiss.reward_calc.storage import Storage, get_rc_version
from ..utils.msgpack_for_db import MsgPackForDB

__all__ = (
    "WriteAheadLogWriter", "WriteAheadLogReader", "WALogable", "StateWAL", "IissWAL", "WALState", "WALDBType"
)

import struct
from abc import ABCMeta
from typing import Optional, Tuple, Iterable, List
import os
from enum import Enum

import msgpack
from iconcommons.logger import Logger

from ..base.block import Block
from ..base.exception import AccessDeniedException, InvalidParamsException
from ..base.exception import InternalServiceErrorException, IllegalFormatException
from ..utils import bytes_to_hex
from ..database.batch import BlockBatch, TransactionBatchValue


TAG = "WAL"
_MAGIC_KEY = b"IWAL"
_FILE_VERSION = 1
_HEADER_SIZE = 52
_HEADER_STRUCT_FORMAT = ">4sIII32sI"

# FILE OFFSET
_OFFSET_MAGIC_KEY = 0
_OFFSET_VERSION = _OFFSET_MAGIC_KEY + 4
_OFFSET_REVISION = _OFFSET_VERSION + 4
_OFFSET_STATE = _OFFSET_REVISION + 4
_OFFSET_INSTANT_BLOCK_HASH = _OFFSET_STATE + 4
_OFFSET_LOG_COUNT = _OFFSET_INSTANT_BLOCK_HASH + 32
_OFFSET_LOG_START_OFFSETS = _OFFSET_LOG_COUNT + 4


class WALDBType(Enum):
    RC = 0
    STATE = 1


class WALState(Flag):
    CALC_PERIOD_START_BLOCK = auto()
    # Write WAL to rc_db
    WRITE_RC_DB = auto()
    # Write WAL to state_db
    WRITE_STATE_DB = auto()
    # Send COMMIT_BLOCK message to rc
    SEND_COMMIT_BLOCK = auto()
    # Send CALCULATE message to rc
    SEND_CALCULATE = auto()

    # Means All flags are on
    ALL = 0xFFFFFFFF


def block_batch_value_to_bytes(block_batch_value: 'BlockBatchValue') -> Optional[bytes]:
    if not isinstance(block_batch_value, BlockBatchValue):
        raise InvalidParamsException(f"Invalid value type: {type(block_batch_value)}")
    return block_batch_value.value


class WALogable(metaclass=ABCMeta):
    def __iter__(self) -> Tuple[bytes, Optional[bytes]]:
        pass


class StateWAL(WALogable):
    def __init__(self, block_batch: 'BlockBatch', converter: Optional[callable] = block_batch_value_to_bytes):
        self.block_batch: 'BlockBatch' = block_batch
        self.converter: callable = converter

    def __iter__(self) -> Tuple[bytes, Optional[bytes]]:
        for key, value in self.block_batch.items():
            if self.converter:
                value = self.converter(value)
            yield key, value


class IissWAL(WALogable):
    def __init__(self, rc_batch: list, tx_index: int, revision: int = -1):
        self._rc_batch: list = rc_batch
        self._tx_index: int = tx_index
        # If revision is not -1, should put revision and version to rc db
        self._revision: int = revision
        self._version: int = self._get_version()

        self._final_tx_index: Optional[int] = None

    @property
    def final_tx_index(self) -> Optional[int]:
        # If None, means there were any data to put
        return self._final_tx_index

    def _get_version(self):
        version: int = -1
        if self._revision == -1:
            return version
        else:
            version: int = get_rc_version(self._revision)
            return version

    def __iter__(self) -> Tuple[bytes, Optional[bytes]]:
        tx_index = self._tx_index

        # In case of the start block of calc period, put version, revision
        if self._revision != -1:
            # todo: refactoring (same logic exists in reward_calc storage
            key: bytes = Storage.KEY_FOR_VERSION_AND_REVISION
            value: bytes = MsgPackForDB.dumps([self._version, self._revision])
            yield key, value

        for iiss_data in self._rc_batch:
            if isinstance(iiss_data, TxData):
                tx_index += 1
                key: bytes = iiss_data.make_key(tx_index)
            else:
                key: bytes = iiss_data.make_key()
            value: bytes = iiss_data.make_value()
            yield key, value

        if tx_index > self._tx_index:
            key: bytes = Storage.KEY_FOR_GETTING_LAST_TRANSACTION_INDEX
            value: bytes = tx_index.to_bytes(8, DATA_BYTE_ORDER)
            yield key, value

        self._final_tx_index = tx_index


def _uint32_to_bytes(value: int):
    return value.to_bytes(4, "big", signed=False)


def _bytes_to_uint32(data: bytes):
    return int.from_bytes(data, "big", signed=False)


class WriteAheadLogWriter(object):
    """Write write-ahead-logging for block, state_db and rc_db on commit

    | magic_key(4) | version(4) | revision(4) | state(4) | instant_block_hash(32) |
    | data count(4) | log start address_0 (4) | log start address_1 (4) | ...
    | block data size(4) | block data | size(4) | data | size(4) | data | ...

    Every number is written in big endian format
    """

    def __init__(self, revision: int, max_log_count: int, block: 'Block', instant_block_hash: bytes):
        Logger.debug(tag=TAG,
                     msg=f"__init__(revision={revision}, "
                         f"max_log_out={max_log_count}, "
                         f"block={block} start")

        self._magic_key = _MAGIC_KEY
        self._version = _FILE_VERSION
        self._revision: int = revision
        self._state: int = 0
        self._max_log_count: int = max_log_count
        self._log_count: int = 0

        self._instant_block_hash = instant_block_hash
        self._block = block
        self._fp = None

        Logger.debug(tag=TAG, msg="__init__() end")

    def open(self, path: str):
        if self._fp is not None:
            raise InternalServiceErrorException("WAL file pointer is not None")

        try:
            self._fp = open(path, "wb")
            self._write_header()
            self._write_block()
        except:
            self._fp = None
            raise

    def _write_header(self) -> int:
        values = [
            self._magic_key,
            self._version,
            self._revision,
            self._state,
            self._instant_block_hash,
            self._log_count
        ]

        for _ in range(self._max_log_count):
            values.append(0)

        struct_format = _HEADER_STRUCT_FORMAT + "I" * self._max_log_count
        data: bytes = struct.pack(struct_format, *values)
        return self._fp.write(data)

    def flush(self):
        fp = self._fp

        if fp:
            fp.flush()
            os.fsync(fp.fileno())

    def close(self):
        if self._fp:
            self._fp.close()
            self._fp = None

    def _write_block(self) -> int:
        block = self._block

        data: bytes = block.to_bytes(self._revision)
        self._write_uint32(len(data))
        ret = self._fp.write(data) + 4

        return ret

    def write_walogable(self, it: Iterable[Tuple[bytes, Optional[bytes]]]) -> int:
        self._fp.seek(0, 2)
        start_offset: int = self._fp.tell()

        size = 0
        self._write_uint32(size)

        for key, value in it:
            size += self._write_key_value(key, value)

        # Return to the WALogable start offset, writing its data size
        self._fp.seek(-size - 4, 1)
        self._write_uint32(size)

        self._write_log_start_offset(self._log_count, start_offset)
        self._write_log_count()

        return size

    def _write_key_value(self, key: bytes, value: bytes) -> int:
        assert isinstance(key, bytes)

        data: bytes = msgpack.packb([key, value])
        size = self._fp.write(data)
        assert size == len(data)

        return size

    def write_state(self, state: int, add: bool = False):
        offset = _OFFSET_STATE

        if add:
            state |= self._state

        self._fp.seek(offset, 0)
        self._write_uint32(state)
        self._state = state

    def _write_log_count(self) -> int:
        offset = _OFFSET_LOG_COUNT
        self._log_count += 1

        self._fp.seek(offset, 0)
        data: bytes = _uint32_to_bytes(self._log_count)
        return self._fp.write(data)

    def _write_log_start_offset(self, index: int, start_offset: int) -> int:
        offset = _OFFSET_LOG_START_OFFSETS + index * 4
        self._fp.seek(offset, 0)

        return self._write_uint32(start_offset)

    def _write_uint32(self, value: int) -> int:
        return self._fp.write(_uint32_to_bytes(value))

    def _check_file_pointer(self):
        if self._fp is None:
            raise AccessDeniedException("WAL not ready")


class WriteAheadLogReader(object):
    """Read data from a write ahead log file

    """

    def __init__(self):
        self._magic_key: Optional[bytes] = None
        self._version: int = 0
        self._revision: int = 0
        self._state: int = 0
        self._log_count: int = 0
        self._log_start_offsets: Optional[List[int]] = None
        self._instant_block_hash: bytes = b""
        self._block: Optional['Block'] = None

        self._fp = None

    @property
    def magic_key(self) -> Optional[bytes]:
        return self._magic_key

    @property
    def version(self) -> int:
        return self._version

    @property
    def revision(self) -> int:
        return self._revision

    @property
    def state(self) -> int:
        return self._state

    @property
    def instant_block_hash(self) -> bytes:
        return self._instant_block_hash

    @property
    def block(self) -> Optional['Block']:
        return self._block

    @property
    def log_count(self) -> int:
        return self._log_count

    def __str__(self):
        return f"version={self._version}, " \
               f"state={self._state}, " \
               f"instant_block_hash={bytes_to_hex(self._instant_block_hash)}, " \
               f"log_count={self._log_count}, " \
               f"block={self._block}"

    def open(self, path: str):
        self._fp = open(path, "rb")
        self._read_header()
        self._read_block()

    def close(self):
        if self._fp:
            self._fp.close()
            self._fp = None

    def _read_header(self):
        data: bytes = self._fp.read(_HEADER_SIZE)
        self._check_bytes_data(data, _HEADER_SIZE)

        magic_key, version, revision, state, instant_block_hash, log_count = \
            struct.unpack_from(_HEADER_STRUCT_FORMAT, data)

        if magic_key != _MAGIC_KEY:
            raise IllegalFormatException(f"Invalid magic key: {bytes_to_hex(data)}")

        if version != _FILE_VERSION:
            raise IllegalFormatException(
                f"Invalid version: Actual({version}) != Expected({_FILE_VERSION})")

        self._magic_key = magic_key
        self._version = version
        self._revision = revision
        self._state = state
        self._log_count = log_count
        self._instant_block_hash = instant_block_hash
        self._log_start_offsets = []

        for _ in range(self._log_count):
            offset = self._read_uint32()
            self._log_start_offsets.append(offset)

    def _read_block(self):
        size: int = self._read_uint32()
        data: bytes = self._fp.read(size)
        self._check_bytes_data(data, size)

        self._block = Block.from_bytes(data)

    def _read_uint32(self) -> int:
        size = 4
        data: bytes = self._fp.read(size)
        self._check_bytes_data(data, size)

        return _bytes_to_uint32(data)

    def get_iterator(self, index: int) -> Iterable[Tuple[bytes, Optional[bytes]]]:
        self._seek_to_log_start_offset(index)
        size: int = self._read_uint32()

        unpacker = msgpack.Unpacker(use_list=False, raw=True)

        while size > 0:
            size_to_read = min(size, 16384)
            data: bytes = self._fp.read(size_to_read)
            self._check_bytes_data(data, size_to_read)

            size -= size_to_read

            unpacker.feed(data)
            for key, value in unpacker:
                yield key, value

    def _seek_to_log_start_offset(self, index: int):
        offset = self._log_start_offsets[index]
        self._fp.seek(offset, 0)

    @classmethod
    def _check_bytes_data(cls, data: bytes, size: int):
        if not isinstance(data, bytes):
            raise IllegalFormatException("Data is not bytes")

        if len(data) != size:
            raise IllegalFormatException(f"Out of data: data_size({len(data)}) != size_to_read({size})")
