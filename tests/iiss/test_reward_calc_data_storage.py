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
from unittest.mock import patch

from iconservice.iiss.data_creator import *
from iconservice.iiss.msg_data import TxType
from iconservice.iiss.reward_calc_data_storage import RewardCalcDataStorage
from tests import create_address
from tests.iiss.mock_rc_db import MockIissDataBase
from tests.mock_db import MockPlyvelDB


class TestRcDataStorage(unittest.TestCase):
    @patch('iconservice.iiss.database.iiss_db.IissDatabase.from_path')
    @patch('os.path.exists')
    def setUp(self, _, mocked_iiss_db_from_path) -> None:
        self.path = ""
        mocked_iiss_db_from_path.side_effect = MockIissDataBase.from_path
        self.rc_data_storage = RewardCalcDataStorage()
        self.rc_data_storage.open(self.path)

        dummy_block_height = 1

        self.dummy_header = Header()
        self.dummy_header.block_height = dummy_block_height
        self.dummy_header.version = 1

        self.dummy_gv = GovernanceVariable()
        self.dummy_gv.block_height = dummy_block_height
        self.dummy_gv.icx_price = 1
        self.dummy_gv.incentive_rep = 10

        self.dummy_prep = PRepsData()
        self.dummy_prep.block_height = dummy_block_height
        self.dummy_prep.block_generator = create_address()
        self.dummy_prep.block_validator_list = [create_address()]

        self.dummy_tx = TxData()
        self.dummy_tx.address = create_address()
        self.dummy_tx.block_height = dummy_block_height
        self.dummy_tx.type = TxType.PREP_REGISTER
        self.dummy_tx.data = PRepRegisterTx()

    def tearDown(self):
        pass

    @patch('iconservice.iiss.database.iiss_db.IissDatabase.from_path')
    @patch('os.path.exists')
    def test_open(self, mocked_path_exists, mocked_iiss_db_from_path):
        # success case: when input existing path, make path of current_db and iiss_rc_db
        # and generate current level db(if not exist)
        rc_data_storage = RewardCalcDataStorage()
        test_db_path: str = os.path.join(os.getcwd(), ".storage_test_db")

        expected_current_db_path = os.path.join(test_db_path, RewardCalcDataStorage._CURRENT_IISS_DB_NAME)

        def from_path(path: str,
                      create_if_missing: bool = True) -> 'MockIissDataBase':
            """
            :param path: db path
            :param create_if_missing:
            :return: KeyValueDatabase instance
            """
            assert expected_current_db_path, path
            assert True, create_if_missing
            db = MockPlyvelDB(MockPlyvelDB.make_db())
            return MockIissDataBase(db)
        mocked_iiss_db_from_path.side_effect = from_path
        rc_data_storage.open(test_db_path)
        mocked_path_exists.assert_called()

        expected_tx_index = -1
        actual_tx_index = rc_data_storage._db_iiss_tx_index
        self.assertEqual(expected_tx_index, actual_tx_index)

    def test_load_last_tx_index(self):
        current_db = self.rc_data_storage.db
        # success case: when inquiring tx index while current_db has non data recorded should return -1
        current_db.delete(b'last_transaction_index')
        expected_tx_index = -1
        actual_tx_index = self.rc_data_storage._load_last_transaction_index()
        self.assertEqual(expected_tx_index, actual_tx_index)

        # success case: when inquiring tx index while current_db has tx data recorded, should return
        # correct index (i.e. last index number)

        for index in range(0, 200):
            dummy_last_tx_index_info = index.to_bytes(8, 'big')
            current_db.put(b'last_transaction_index', dummy_last_tx_index_info)

            expected_tx_index = index
            actual_tx_index = self.rc_data_storage._load_last_transaction_index()
            self.assertEqual(expected_tx_index, actual_tx_index)

    def test_create_db_for_calc_invalid_block_height(self):
        # failure case: when input block height less than or equal to 0, raise exception
        for block_height in range(-2, 1):
            self.assertRaises(AssertionError, self.rc_data_storage.create_db_for_calc, block_height)

    @patch('iconservice.iiss.database.iiss_db.IissDatabase.from_path')
    @patch('os.rename')
    @patch('os.path.exists')
    def test_create_db_for_calc_valid_block_height(self, mocked_path_exists, mocked_rename, mocked_iiss_db_from_path):
        # success case: when input valid block height, should create iiss_db and return path
        mocked_iiss_db_from_path.side_effect = MockIissDataBase.from_path
        current_db_path = os.path.join(self.path, RewardCalcDataStorage._CURRENT_IISS_DB_NAME)

        # todo: to be refactored
        def path_exists(path):
            if path == current_db_path:
                return True
            else:
                return False
        mocked_path_exists.side_effect = path_exists

        valid_block_height = 1
        expected_iiss_db_path = os.path.join(self.path,
                                             RewardCalcDataStorage._IISS_RC_DB_NAME_PREFIX + f"{valid_block_height}")
        actual_ret_path = self.rc_data_storage.create_db_for_calc(valid_block_height)
        self.assertEqual(expected_iiss_db_path, actual_ret_path)

        mocked_rename.assert_called_with(current_db_path, expected_iiss_db_path)
        mocked_iiss_db_from_path.assert_called_with(current_db_path)

        expected_last_tx_index = -1
        self.assertEqual(expected_last_tx_index, self.rc_data_storage._db_iiss_tx_index)

    def test_commit_invalid_batch_format(self):
        # failure case: when input invalid format of batch, should raise error
        invalid_batch = [self.dummy_header, [self.dummy_gv, self.dummy_prep]]
        self.assertRaises(AttributeError, self.rc_data_storage.commit, invalid_batch)

    def test_commit_without_iiss_tx(self):
        # todo: should supplement this unit tests
        # success case: when there is no iiss_tx data, index should not be increased
        dummy_iiss_data_list_without_iiss_tx = [self.dummy_header, self.dummy_gv, self.dummy_prep]
        self.rc_data_storage.commit(dummy_iiss_data_list_without_iiss_tx)
        expected_index = -1
        self.assertEqual(expected_index, self.rc_data_storage._db_iiss_tx_index)
        self.assertEqual(None,
                         self.rc_data_storage.db.get(self.rc_data_storage._KEY_FOR_GETTING_LAST_TRANSACTION_INDEX))

    def test_commit_with_iiss_tx(self):
        # todo: should supplement this unit tests
        # success case: when there is iiss_tx data, index should be increased
        for expected_index in range(0, 10):
            dummy_iiss_data_list = [self.dummy_header, self.dummy_gv, self.dummy_prep, self.dummy_tx]
            self.rc_data_storage.commit(dummy_iiss_data_list)
            self.assertEqual(expected_index, self.rc_data_storage._db_iiss_tx_index)

            recorded_index = \
                int.from_bytes(
                    self.rc_data_storage.db.get(self.rc_data_storage._KEY_FOR_GETTING_LAST_TRANSACTION_INDEX), 'big')
            self.assertEqual(expected_index, recorded_index)

            last_tx_index = -1
            for key in self.rc_data_storage.db.iterator():
                if key[:2] == b'TX':
                    temp_tx_index = int.from_bytes(key[2:], 'big')
                    if last_tx_index < temp_tx_index:
                        last_tx_index = temp_tx_index
            self.assertEqual(expected_index, last_tx_index)
