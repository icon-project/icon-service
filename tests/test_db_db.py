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
from iconservice.database.factory import DatabaseFactory
from iconservice.database.db import ContextDatabase, PlyvelDatabase
from iconservice.database.batch import BlockBatch, TransactionBatch
from iconservice.iconscore.icon_score_context import IconScoreContextType
from iconservice.iconscore.icon_score_context import IconScoreContextFactory
from . import create_address, rmtree


class TestPlyvelDatabase(unittest.TestCase):
    def setUp(self):
        state_db_root_path = 'state_db'
        self.state_db_root_path = state_db_root_path
        rmtree(state_db_root_path)
        os.mkdir(state_db_root_path)

        self.db = PlyvelDatabase(
            PlyvelDatabase.make_db(state_db_root_path, True))

    def tearDown(self):
        self.db.close()
        rmtree(self.state_db_root_path)

    def test_get_and_put(self):
        db = self.db

        db.put(b'key0', b'value0')
        value = db.get(b'key0')
        self.assertEqual(b'value0', value)

        value = db.get(b'key1')
        self.assertIsNone(value)

    def test_write_batch(self):
        data = {
            b'key0': b'value0',
            b'key1': b'value1'
        }
        db = self.db

        db.write_batch(data)

        self.assertEqual(b'value1', db.get(b'key1'))
        self.assertEqual(b'value0', db.get(b'key0'))


class TestContextDatabaseOnWriteMode(unittest.TestCase):
    def setUp(self):
        state_db_root_path = 'state_db'
        self.state_db_root_path = state_db_root_path
        rmtree(state_db_root_path)
        os.mkdir(state_db_root_path)

        address = create_address(AddressPrefix.CONTRACT, b'0')
        factory = DatabaseFactory(state_db_root_path)
        context_factory = IconScoreContextFactory(max_size=2)

        context = context_factory.create(IconScoreContextType.INVOKE)
        context.block_batch = BlockBatch()
        context.tx_batch = TransactionBatch()

        value = 100
        score_db = factory.create_by_address(address)
        score_db._db.put(address.body, value.to_bytes(32, 'big'))

        self.db = score_db
        self.address = address
        self.context = context

    def tearDown(self):
        self.db.close()
        rmtree(self.state_db_root_path)

    def test_get(self):
        """
        """
        context = self.context
        address = create_address(AddressPrefix.CONTRACT, b'0')
        value = self.db.get(context, address.body)
        self.assertEqual(100, int.from_bytes(value, 'big'))

    def test_put(self):
        """WritableDatabase supports put()
        """
        context = self.context
        self.db.put(context, b'key0', b'value0')
        value = self.db.get(context, b'key0')
        self.assertEqual(b'value0', value)

        batch = self.context.tx_batch[self.address]
        self.assertEqual(b'value0', batch.get(b'key0'))

    def test_write_batch(self):
        context = self.context
        data = {
            b'key0': b'value0',
            b'key1': b'value1'
        }
        db = self.db
        db.write_batch(context, data)

        self.assertEqual(b'value1', db.get(context, b'key1'))
        self.assertEqual(b'value0', db.get(context, b'key0'))
