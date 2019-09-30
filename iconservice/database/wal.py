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
from typing import Optional, Tuple, Iterable
from enum import IntEnum

import msgpack

from ..base.block import Block
from ..base.exception import AccessDeniedException
from ..base.exception import InternalServiceErrorException
from ..utils import bytes_to_hex


_MAGIC_KEY = b"IWAL"
_FILE_VERSION = 0


class WALogable(metaclass=ABCMeta):
    def __iter__(self) -> Tuple[bytes, Optional[bytes]]:
        pass


class State(Flag):
    NONE = 0
    BLOCK = auto()
    STATE_DB = auto()
    RC_DB = auto()


class KeyValueItem(object):
    def __init__(self, key: bytes, value: Optional[bytes]):
        self._key = key
        self._value = value

    def to_bytes(self) -> bytes:
        return msgpack.packb([self._key, self._value])

    @staticmethod
    def from_bytes(data: bytes) -> 'KeyValueItem':
        key, value = msgpack.unpackb(data)
        return KeyValueItem(key, value)


class WALDataType(IntEnum):
    BLOCK = 0
    STATE_DB = 1
    RC_DB = 2


class WriteAheadLogWriter(object):
    """Write write-ahead-logging for block, state_db and rc_db on commit

    """
    _FORMAT = ">4sIII"

    def __init__(self, revision: int):
        self._state: 'State' = State.NONE

        self._revision: int = revision
        self._fp = None

    def open(self, path: str):
        if self._fp is not None:
            raise InternalServiceErrorException("WAL file pointer is not None")

        try:
            self._fp = open(path, "wb")
            self._write_header()
        except IOError:
            self._fp = None
            raise InternalServiceErrorException(f"Failed to open '{path}")

    def _write_header(self) -> int:
        data: bytes = struct.pack(
            self._FORMAT, _MAGIC_KEY, _FILE_VERSION, self._state.value, self._revision)
        return self._fp.write(data)

    def close(self):
        if self._fp:
            self._fp.close()
            self._fp = None

    def write_block(self, block: 'Block') -> int:
        data: bytes = block.to_bytes(self._revision)
        self._write_int32(len(data))
        return self._fp.write(data) + 4

    def write_walogable(self, it: WALogable) -> int:
        self._fp.seek(0, 2)

        size = 0
        self._write_int32(size)

        for key, value in it:
            size += self._write(key, value)

        # Return to the begin of WALogable
        self._fp.seek(-size - 4, 1)
        self._write_int32(size)

        return size

    def _write(self, key: bytes, value: bytes) -> int:
        assert isinstance(key, bytes)

        item = KeyValueItem(key, value)
        data: bytes = item.to_bytes()

        size = self._fp.write(data)
        assert size == len(data)

        return size

    def _write_int32(self, value: int) -> int:
        return self._fp.write(value.to_bytes(4, "big"))

    def _check_file_pointer(self):
        if self._fp is None:
            raise AccessDeniedException("WAL not ready")


class WriteAheadLogReader(object):

    def __init__(self):
        self._version: int = 0
        self._state: 'State' = State.NONE
        self._revision: int = 0
        self._block: Optional['Block'] = None
        self._fp = None
        self._start_wal_address: int = -1

    @property
    def version(self) -> int:
        return self._version

    @property
    def state(self) -> 'State':
        return self._state

    @property
    def block(self) -> Optional['Block']:
        return self._block

    @property
    def revision(self) -> int:
        return self._revision

    def load(self, path: str):
        try:
            self._fp = open(path, "rb")
            self._read_header()
            self._read_block()
            self._start_wal_address = self._fp.tell()
        except:
            raise InternalServiceErrorException(f"Failed to load {path}")

    def _read_header(self):
        data: bytes = self._fp.read(4)
        if data != _MAGIC_KEY:
            raise InternalServiceErrorException(f"Invalid magic key: {bytes_to_hex(data)}")

        data: bytes = self._fp.read(4)
        version = int.from_bytes(data, "big")
        if version != _FILE_VERSION:
            raise InternalServiceErrorException(f"Invalid version: {version} != {_FILE_VERSION}")
        self._version = version

        data: bytes = self._fp.read(4)
        self._state = State(int.from_bytes(data, "big"))

        data: bytes = self._fp.read(4)
        self._revision = int.from_bytes(data, "big")

    def _read_block(self):
        size: int = self._read_int32()
        data: bytes = self._fp.read(size)
        self._block = Block.from_bytes(data)

    def _read_int32(self) -> int:
        data: bytes = self._fp.read(4)
        return int.from_bytes(data, "big")

    def get_iterator(self, index: int) -> Iterable[Tuple[bytes, Optional[bytes]]]:
        self._seek_to_db_data(index)
        yield None, None

    def _seek_to_db_data(self, index: int):
        self._fp.seek(self._start_wal_address)

        for i in range(index):
            size: int = self._read_int32()
            self._fp.seek(size, 1)
