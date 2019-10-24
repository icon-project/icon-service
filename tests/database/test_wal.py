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

import os
import random
import unittest

import pytest

from iconservice.base.block import Block
from iconservice.base.exception import IllegalFormatException
from iconservice.database.wal import (
    _MAGIC_KEY, _FILE_VERSION, _OFFSET_VERSION, _HEADER_SIZE,
    WriteAheadLogReader, WriteAheadLogWriter, WALogable, WALState
)
from iconservice.icon_constant import Revision
from tests import create_block_hash


class WALogableData(WALogable):
    def __init__(self, data):
        self._data = data

    def __iter__(self):
        for key, value in self._data.items():
            yield key, value


class TestWriteAheadLog(unittest.TestCase):

    def setUp(self) -> None:
        self.path = "./test.wal"

        self.log_data = [
            {
                b"a": b"apple",
                b"b": b"banana",
                b"c": None,
                b"d": b""
            },
            {
                b"1": None,
                b"2": b"2-hello",
                b"4": b"",
                b"3": b"3-world"
            }
        ]

        self.block = Block(
            block_height=random.randint(0, 1000),
            block_hash=os.urandom(32),
            prev_hash=os.urandom(32),
            timestamp=random.randint(0, 1_000_000),
            cumulative_fee=random.randint(0, 1_000_000)
        )

    def tearDown(self) -> None:
        try:
            os.remove(self.path)
        except:
            pass

    def test_writer_and_reader(self):
        revision = Revision.IISS.value
        log_count = 2
        instant_block_hash = create_block_hash()

        writer = WriteAheadLogWriter(revision, log_count, self.block, instant_block_hash)
        writer.open(self.path)

        writer.write_state(WALState.CALC_PERIOD_START_BLOCK.value, add=False)

        writer.write_walogable(WALogableData(self.log_data[0]))
        writer.write_state(WALState.WRITE_RC_DB.value, add=True)

        writer.write_walogable(WALogableData(self.log_data[1]))
        writer.write_state(WALState.WRITE_STATE_DB.value, add=True)

        state = (WALState.WRITE_RC_DB | WALState.WRITE_STATE_DB).value
        writer.write_state(state, add=False)
        writer.close()

        reader = WriteAheadLogReader()
        reader.open(self.path)
        assert reader.magic_key == _MAGIC_KEY
        assert reader.version == _FILE_VERSION
        assert reader.revision == revision
        assert reader.state == state
        assert reader.log_count == log_count
        assert reader.block == self.block
        assert reader.instant_block_hash == instant_block_hash

        for i in range(len(self.log_data)):
            data = {}

            for key, value in reader.get_iterator(i):
                data[key] = value

            assert data == self.log_data[i]
            assert id(data) != id(self.log_data[i])

        reader.close()

    def test_invalid_magic_key(self):
        revision = Revision.IISS.value
        log_count = 2
        instant_block_hash = create_block_hash()

        writer = WriteAheadLogWriter(revision, log_count, self.block, instant_block_hash)
        writer.open(self.path)
        writer.close()

        # Make the magic key invalid
        with open(self.path, "rb+") as f:
            ret = f.write(b"iwal")
            assert ret == 4

        reader = WriteAheadLogReader()
        with pytest.raises(IllegalFormatException):
            reader.open(self.path)

    def test_invalid_version(self):
        revision = Revision.IISS.value
        log_count = 2
        instant_block_hash = create_block_hash()

        writer = WriteAheadLogWriter(revision, log_count, self.block, instant_block_hash)
        writer.open(self.path)
        writer.close()

        # Make the version invalid
        with open(self.path, "rb+") as f:
            f.seek(_OFFSET_VERSION)
            version = 0xFFFFFFFF
            ret = f.write(version.to_bytes(4, "big"))
            assert ret == 4

        reader = WriteAheadLogReader()
        with pytest.raises(IllegalFormatException):
            reader.open(self.path)

    def test_out_of_header_size(self):
        revision = Revision.IISS.value
        log_count = 2
        instant_block_hash = create_block_hash()

        writer = WriteAheadLogWriter(
            revision=revision, max_log_count=log_count, block=self.block, instant_block_hash=instant_block_hash)
        writer.open(self.path)
        writer.close()

        f = open(self.path, "rb+")
        f.truncate(_HEADER_SIZE - 4)
        f.close()

        reader = WriteAheadLogReader()
        with pytest.raises(IllegalFormatException):
            reader.open(self.path)
