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
import unittest
from collections import OrderedDict

from iconservice.base.block import Block
from iconservice.database.wal import WriteAheadLogger, WALogable, State


class WALogableData(WALogable):
    def __init__(self, data):
        self._data = data
        self._tx_index

    def __iter__(self):
        for key, value in self._data.items():
            yield key, value


class TestWriteAheadLogger(unittest.TestCase):

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

    def tearDown(self) -> None:
        try:
            # os.unlink(self.path)
            pass
        except:
            pass

    def test_init(self):
        wal = WriteAheadLogger()
        assert wal.block is None

        wal.open(self.path, create=True)
        wal.record_walogable(WALogableData(self.data_0))
        wal.record_walogable(WALogableData(self.data_1))
        wal.close()

        wal.open(self.path, create=False)
        assert wal.version == WriteAheadLogger._VERSION
        assert wal.state == State.NONE
        assert wal.revision == 0
        wal.close()

    def test_load(self):
        pass
