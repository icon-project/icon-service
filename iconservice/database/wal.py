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

__all__ = ("WriteAheadLogWriter", "WriteAheadLogReader", "WALogable")

import struct
from abc import ABCMeta
from enum import Flag, auto
from typing import Optional, Tuple, Iterable, List

import msgpack

from ..base.block import Block
from ..base.exception import AccessDeniedException
from ..base.exception import InternalServiceErrorException, IllegalFormatException
from ..utils import bytes_to_hex

_MAGIC_KEY = b"IWAL"
_FILE_VERSION = 0
_HEADER_SIZE = 20
_HEADER_STRUCT_FORMAT = ">4sIIII"

# FILE OFFSET
_OFFSET_MAGIC_KEY = 0
_OFFSET_VERSION = _OFFSET_MAGIC_KEY + 4
_OFFSET_REVISION = _OFFSET_VERSION + 4
_OFFSET_STATE = _OFFSET_REVISION + 4
_OFFSET_LOG_COUNT = _OFFSET_STATE + 4
_OFFSET_LOG_START = _OFFSET_LOG_COUNT + 4


class WALogable(metaclass=ABCMeta):
    def __iter__(self) -> Tuple[bytes, Optional[bytes]]:
        pass


def _uint32_to_bytes(value: int):
    return value.to_bytes(4, "big", signed=False)


def _bytes_to_uint32(data: bytes):
    return int.from_bytes(data, "big", signed=False)


class WriteAheadLogWriter(object):
    """Write write-ahead-logging for block, state_db and rc_db on commit

    | magic_key(4) | version(4) | revision(4) | state(4) | data count(4) |
    | log start address_0 (4) | log start address_1 (4) | ...
    | block data size(4) | block data | size(4) | data | size(4) | data | ...

    Every number is written in big endian format
    """

    def __init__(self, revision: int, max_log_count: int, block: 'Block'):
        self._magic_key = _MAGIC_KEY
        self._version = _FILE_VERSION
        self._revision: int = revision
        self._state: int = 0
        self._max_log_count: int = max_log_count
        self._log_count: int = 0

        self._header_size: _OFFSET_LOG_START + max_log_count * 4

        self._block = block
        self._fp = None

    def open(self, path: str):
        if self._fp is not None:
            raise InternalServiceErrorException("WAL file pointer is not None")

        try:
            self._fp = open(path, "wb")
            self._write_header()
            self._write_block()
        except IOError:
            self._fp = None
            raise InternalServiceErrorException(f"Failed to open '{path}")

    def _write_header(self) -> int:
        values = [
            self._magic_key,
            self._version,
            self._revision,
            self._state,
            self._log_count
        ]

        for _ in range(self._max_log_count):
            values.append(0)

        struct_format = _HEADER_STRUCT_FORMAT + "I" * self._max_log_count
        data: bytes = struct.pack(struct_format, *values)
        return self._fp.write(data)

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

    def write_walogable(self, it: WALogable) -> int:
        self._fp.seek(0, 2)
        start_offset: int = self._fp.tell()

        size = 0
        self._write_uint32(size)

        for key, value in it:
            size += self._write_key_value(key, value)

        # Return to the begin of WALogable
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

    def write_state(self, state: int):
        offset = _OFFSET_STATE

        self._fp.seek(offset, 0)
        self._write_uint32(state)

    def _write_log_count(self) -> int:
        offset = _OFFSET_LOG_COUNT
        self._log_count += 1

        self._fp.seek(offset, 0)
        data: bytes = _uint32_to_bytes(self._log_count)
        return self._fp.write(data)

    def _write_log_start_offset(self, index: int, start_offset: int) -> int:
        offset = _OFFSET_LOG_START + index * 4
        self._fp.seek(offset, 0)

        return self._write_uint32(start_offset)

    def _write_uint32(self, value: int) -> int:
        return self._fp.write(_uint32_to_bytes(value))

    def _check_file_pointer(self):
        if self._fp is None:
            raise AccessDeniedException("WAL not ready")


class WriteAheadLogReader(object):

    def __init__(self):
        self._magic_key: Optional[bytes] = None
        self._version: int = 0
        self._revision: int = 0
        self._state: int = 0
        self._log_count: int = 0
        self._log_start_offsets = []
        self._block: Optional['Block'] = None

        self._fp = None
        self._start_wal_address: int = -1

    @property
    def magic_key(self) -> Optional[bytes]:
        return self._magic_key

    @property
    def version(self) -> int:
        return self._version

    @property
    def state(self) -> int:
        return self._state

    @property
    def block(self) -> Optional['Block']:
        return self._block

    @property
    def revision(self) -> int:
        return self._revision

    @property
    def log_count(self) -> int:
        return self._log_count

    def open(self, path: str):
        try:
            self._fp = open(path, "rb")
            self._read_header()
            self._read_block()
            self._start_wal_address = self._fp.tell()
        except:
            raise InternalServiceErrorException(f"Failed to load {path}")

    def close(self):
        if self._fp:
            self._fp.close()
            self._fp = None

    def _read_header(self):
        data: bytes = self._fp.read(_HEADER_SIZE)
        if len(data) < _HEADER_SIZE:
            raise IllegalFormatException("WAL header size not enough")

        magic_key, version, revision, state, log_count = \
            struct.unpack_from(_HEADER_STRUCT_FORMAT, data)

        if magic_key != _MAGIC_KEY:
            raise InternalServiceErrorException(f"Invalid magic key: {bytes_to_hex(data)}")

        if version != _FILE_VERSION:
            raise InternalServiceErrorException(f"Invalid version: {version} != {_FILE_VERSION}")

        self._magic_key = magic_key
        self._version = version
        self._revision = revision
        self._state = state
        self._log_count = log_count

        for _ in range(self._log_count):
            offset = self._read_uint32()
            self._log_start_offsets.append(offset)

    def _read_block(self):
        size: int = self._read_uint32()
        data: bytes = self._fp.read(size)
        self._block = Block.from_bytes(data)

    def _read_uint32(self) -> int:
        data: bytes = self._fp.read(4)
        return _bytes_to_uint32(data)

    def get_iterator(self, index: int) -> Iterable[Tuple[bytes, Optional[bytes]]]:
        self._seek_to_log_start_offset(index)
        size: int = self._read_uint32()

        unpacker = msgpack.Unpacker(use_list=False, raw=True)

        size_to_read = 16 * 1024
        while size > 0:
            size_to_read = min(size, size_to_read)
            data: bytes = self._fp.read(size_to_read)
            assert len(data) == size_to_read
            size -= size_to_read

            unpacker.feed(data)
            for key, value in unpacker:
                yield key, value

    def _seek_to_log_start_offset(self, index: int):
        offset = self._log_start_offsets[index]
        self._fp.seek(offset, 0)
