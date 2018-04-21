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


import logging
import os
import shutil
import unittest

from iconservice.base.address import Address, AddressPrefix
from iconservice.database.factory import DatabaseFactory
from iconservice.database.context_db import ContextDatabase
from iconservice.iconscore.icon_score_info_mapper import IconScoreInfo
from iconservice.iconscore.icon_score_info_mapper import IconScoreInfoMapper
from . import create_address, rmtree, create_tx_hash, create_block_hash


class TestContextDatabase(unittest.TestCase):
    def setUp(self):
        """This method is called before calling every test methods 
        """
        state_db_root_path = 'state_db'
        self.state_db_root_path = state_db_root_path
        rmtree(state_db_root_path)
        os.mkdir(state_db_root_path)

        address = create_address(AddressPrefix.CONTRACT, b'0')
        db_factory = DatabaseFactory(state_db_root_path=state_db_root_path)

        IconScoreInfo.set_db_factory(db_factory)
        info = IconScoreInfo(
            icon_score=None,
            owner=None,
            icon_score_address=address)

        mapper = IconScoreInfoMapper()
        mapper[address] = info

        self.mapper = mapper
        self.context_db = ContextDatabase(mapper)
        self.context_db.icon_score_address = address

    def tearDown(self):
        for address in self.mapper:
            self.mapper[address].db.close()

        rmtree(self.state_db_root_path)

    def test_get_and_put(self):
        value = self.context_db.get(b'hello')
        self.assertIsNone(value)

        input = 100
        self.context_db.put(b'hello', input.to_bytes(32, 'big'))

        output = self.context_db.get(b'hello')
        self.assertEqual(input, int.from_bytes(output, 'big'))

    def test_transaction(self):
        context_db = self.context_db

        tx_hash = create_tx_hash()
        address0 = b'address0'
        address1 = b'address1'

        context_db.start_transaction(tx_hash)

        balance0 = 100
        context_db.put(address0, balance0.to_bytes(32, 'big'))
        value = context_db.get(address0)
        self.assertEqual(balance0, int.from_bytes(value, 'big'))

        balance0 = int.from_bytes(value, 'big')
        balance1 = 20
        balance0 -= balance1

        context_db.put(address0, balance0.to_bytes(32, 'big'))
        context_db.put(address1, balance1.to_bytes(32, 'big'))

        value = context_db.get(address0)
        self.assertEqual(balance0, int.from_bytes(value, 'big'))

        value = context_db.get(address1)
        self.assertEqual(balance1, int.from_bytes(value, 'big'))

        context_db.end_transaction()

        value = context_db.get(address0)
        self.assertTrue(isinstance(value, bytes))
        self.assertEqual(balance0, int.from_bytes(value, 'big'))

        value = context_db.get(address1)
        self.assertEqual(balance1, int.from_bytes(value, 'big'))

    def test_rollback_transaction(self):
        context_db = self.context_db
        tx_hash = create_tx_hash()
        data = {b'key0': 10, b'key1': 20}

        context_db.start_transaction(tx_hash)

        for key in data:
            value = data[key].to_bytes(32, 'big')
            context_db.put(key, value)

            saved_value = context_db.get(key)
            self.assertEqual(value, saved_value)

        context_db.rollback_transaction()

        for key in data:
            value = context_db.get(key)
            self.assertIsNone(value)

    def test_commit(self):
        context_db = self.context_db
        icon_score_address = context_db.icon_score_address
        tx_hash = create_tx_hash()
        block_hash = create_block_hash()
        data = {b'key0': 10, b'key1': 20}

        context_db.start_block(0, block_hash)
        context_db.start_transaction(tx_hash)

        for key in data:
            value = data[key].to_bytes(32, 'big')
            context_db.put(key, value)

            saved_value = context_db.get(key)
            self.assertEqual(value, saved_value)

        context_db.end_transaction()
        context_db.end_block()

        context_db.commit()

        self.assertIsNone(context_db._tx_batch[icon_score_address])
        self.assertIsNone(context_db._block_batch[icon_score_address])

        for key in data:
            value = data[key].to_bytes(32, 'big')

            saved_value = context_db._score_db.get(key)
            self.assertEqual(value, saved_value)

    def test_rollback(self):
        context_db = self.context_db
        icon_score_address = context_db.icon_score_address
        tx_hash = create_tx_hash()
        block_hash = create_block_hash()
        data = {b'key0': 10, b'key1': 20}

        context_db.start_block(0, block_hash)
        context_db.start_transaction(tx_hash)

        for key in data:
            value = data[key].to_bytes(32, 'big')
            context_db.put(key, value)

            saved_value = context_db.get(key)
            self.assertEqual(value, saved_value)

        context_db.end_transaction()
        context_db.end_block()

        context_db.rollback()

        self.assertIsNone(context_db._tx_batch[icon_score_address])
        self.assertIsNone(context_db._block_batch[icon_score_address])

        for key in data:
            value = context_db._score_db.get(key)
            self.assertIsNone(value)
