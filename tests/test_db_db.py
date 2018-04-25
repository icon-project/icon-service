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


import os
import shutil
import unittest

from iconservice.base.address import Address, AddressPrefix
from iconservice.base.exception import DatabaseException
from iconservice.database.db import PlyvelDatabase
from iconservice.database.db import ReadOnlyDatabase
from iconservice.database.db import WritableDatabase
from iconservice.database.factory import DatabaseFactory
from iconservice.database.batch import BlockBatch, TransactionBatch
from . import create_address, rmtree


class TestPlyvelDatabase(unittest.TestCase):
    def setUp(self):
        state_db_root_path = 'state_db'
        self.state_db_root_path = state_db_root_path
        rmtree(state_db_root_path)
        os.mkdir(state_db_root_path)

        address = create_address(AddressPrefix.CONTRACT, b'0')
        factory = DatabaseFactory(state_db_root_path)
        self.db = factory.create_by_address(address)

    def tearDown(self):
        self.db.close()
        rmtree(self.state_db_root_path)

    def test_write_batch(self):
        data = {
            b'key0': b'value0',
            b'key1': b'value1'
        }
        db = self.db

        db.write_batch(data)

        self.assertEqual(b'value1', db.get(b'key1'))
        self.assertEqual(b'value0', db.get(b'key0'))


class TestReadOnlyDatabase(unittest.TestCase):
    def setUp(self):
        state_db_root_path = 'state_db'
        self.state_db_root_path = state_db_root_path
        rmtree(state_db_root_path)
        os.mkdir(state_db_root_path)

        address = create_address(AddressPrefix.CONTRACT, b'0')
        factory = DatabaseFactory(state_db_root_path)
        _db = factory.create_by_address(address)

        value = 100
        _db.put(address.body, value.to_bytes(32, 'big'))

        block_batch = BlockBatch(),
        tx_batch = TransactionBatch()

        self.db = ReadOnlyDatabase(_db)

        self.block_batch = block_batch
        self.tx_batch = tx_batch

    def tearDown(self):
        self.db._ReadOnlyDatabase__db.close()
        rmtree(self.state_db_root_path)

    def test_get(self):
        """
        """
        address = create_address(AddressPrefix.CONTRACT, b'0')
        value = self.db.get(address.body)
        self.assertEqual(100, int.from_bytes(value, 'big'))

    def test_put(self):
        """put is not allowed in ReadOnlyDatabase
        """
        with self.assertRaises(DatabaseException):
            self.db.put(b'key0', b'value0')


class TestWritableDatabase(unittest.TestCase):
    def setUp(self):
        state_db_root_path = 'state_db'
        self.state_db_root_path = state_db_root_path
        rmtree(state_db_root_path)
        os.mkdir(state_db_root_path)

        address = create_address(AddressPrefix.CONTRACT, b'0')
        factory = DatabaseFactory(state_db_root_path)
        _db = factory.create_by_address(address)

        value = 100
        _db.put(address.body, value.to_bytes(32, 'big'))

        block_batch = BlockBatch()
        tx_batch = TransactionBatch()

        self.db = WritableDatabase(address=address,
                                   db=_db,
                                   block_batch=block_batch,
                                   tx_batch=tx_batch)

        self.block_batch = block_batch
        self.tx_batch = tx_batch

    def tearDown(self):
        self.db._WritableDatabase__db.close()
        rmtree(self.state_db_root_path)

    def test_get(self):
        """
        """
        address = create_address(AddressPrefix.CONTRACT, b'0')
        value = self.db.get(address.body)
        self.assertEqual(100, int.from_bytes(value, 'big'))

    def test_put(self):
        """WritableDatabase supports put()
        """
        self.db.put(b'key0', b'value0')
        value = self.db.get(b'key0')
        self.assertEqual(b'value0', value)
