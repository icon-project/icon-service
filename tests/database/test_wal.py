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

from iconservice.icon_constant import Revision
from iconservice.base.block import Block
from iconservice.database.wal import (
    _FILE_VERSION, WriteAheadLogReader, WriteAheadLogWriter, WALogable, State
)


class WALogableData(WALogable):
    def __init__(self, data):
        self._data = data

    def __iter__(self):
        for key, value in self._data.items():
            yield key, value


class TestWriteAheadLog(unittest.TestCase):

    def setUp(self) -> None:
        self.path = "./test.wal"
        self.data_0 = {
            b"a": b"apple",
            b"b": b"banana",
            b"c": None
        }
        self.data_1 = {
            b"1": None,
            b"2": b"2-hello",
            b"3": b"3-world"
        }

        self.block = Block(
            block_height=random.randint(0, 1000),
            block_hash=os.urandom(32),
            prev_hash=os.urandom(32),
            timestamp=random.randint(0, 1_000_000),
            cumulative_fee=random.randint(0, 1_000_000)
        )

    def tearDown(self) -> None:
        try:
            os.unlink(self.path)
        except:
            pass

    def test_init(self):
        revision = Revision.IISS.value

        writer = WriteAheadLogWriter(revision, rc_db_revision)
        writer.open(self.path)
        writer.write_block(self.block)
        writer.write_walogable(WALogableData(self.data_0))
        writer.write_walogable(WALogableData(self.data_1))
        writer.close()

        reader = WriteAheadLogReader()
        reader.open(self.path)
        assert reader.version == _FILE_VERSION
        assert reader.state == State.NONE
        assert reader.revision == revision
        assert reader.block == self.block

        data_0 = {}
        it_data_0 = reader.get_iterator(0)
        for key, value in it_data_0:
            data_0[key] = value
        assert data_0 == self.data_0
        assert id(data_0) != id(self.data_0)

        data_1 = {}
        it_data_1 = reader.get_iterator(1)
        for key, value in it_data_1:
            data_1[key] = value
        assert data_1 == self.data_1
        assert id(data_1) != id(self.data_1)

        reader.close()
