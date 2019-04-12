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

from iconservice.iiss.iiss_data_creator import *
from iconservice.iiss.iiss_msg_data import IissTxType
from iconservice.iiss.rc_data_storage import RcDataStorage
from tests import create_address
from tests.iiss.mock_rc_db import MockIissDataBase
from tests.mock_db import MockPlyvelDB


class TestRcDataStorage(unittest.TestCase):
    test_db_path: str = os.path.join(os.getcwd(), ".storage_test_db")

    @patch('iconservice.iiss.database.iiss_db.IissDatabase.from_path')
    @patch('os.path.exists')
    def setUp(self, _, mocked_iiss_db_from_path) -> None:
        self.path = ""
        mocked_iiss_db_from_path.side_effect = MockIissDataBase.from_path
        self.rc_data_storage = RcDataStorage()
        self.rc_data_storage.open(self.path)
        # os.mkdir(self.test_db_path)
        # self.rc_data_storage = RcDataStorage()
        # self.rc_data_storage.open(self.test_db_path)
        # self.current_db_path = os.path.join(self.test_db_path, self.rc_data_storage._CURRENT_IISS_DB_NAME)

        dummy_block_height = 1

        self.dummy_header = IissHeader()
        self.dummy_header.block_height = dummy_block_height
        self.dummy_header.version = 1

        self.dummy_gv = IissGovernanceVariable()
        self.dummy_gv.block_height = dummy_block_height
        self.dummy_gv.icx_price = 1
        self.dummy_gv.incentive_rep = 10

        self.dummy_prep = PrepsData()
        self.dummy_prep.block_height = dummy_block_height
        self.dummy_prep.block_generator = create_address()
        self.dummy_prep.block_validator_list = [create_address()]

        self.dummy_tx = IissTxData()
        self.dummy_tx.address = create_address()
        self.dummy_tx.block_height = dummy_block_height
        self.dummy_tx.type = IissTxType.PREP_REGISTER
        self.dummy_tx.data = PRepRegisterTx()

    def tearDown(self):
        pass

    @patch('iconservice.iiss.database.iiss_db.IissDatabase.from_path')
    @patch('os.path.exists')
    def test_open(self, mocked_path_exists, mocked_iiss_db_from_path):
        # close and remove leveldb(current_db) which is set on setUp method (for test open method)
        # self.rc_data_storage.close()
        # rmtree(self.current_db_path)

        # failure case: when input non-existing path, should raise error
        # rc_data_storage = RcDataStorage()
        # non_exist_path = os.path.join(self.test_db_path, "non_exist_path")
        # self.assertRaises(DatabaseException, rc_data_storage.open, non_exist_path)

        # success case: when input existing path, make path of current_db and iiss_rc_db
        # and generate current level db(if not exist)

        rc_data_storage = RcDataStorage()
        expected_current_db_path = os.path.join(self.test_db_path, RcDataStorage._CURRENT_IISS_DB_NAME)

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

        rc_data_storage.open(self.test_db_path)
        mocked_path_exists.assert_called()

        expected_tx_index = -1
        actual_tx_index = rc_data_storage._db_iiss_tx_index
        self.assertEqual(expected_tx_index, actual_tx_index)

    def test_load_last_tx_index(self):
        # success case: when inquiring tx index while current_db has nozdata recorded should return -1
        expected_tx_index = -1
        actual_tx_index = self.rc_data_storage._load_last_transaction_index()
        self.assertEqual(expected_tx_index, actual_tx_index)

        # success case: when inquiring tx index while current_db has no tx data recorded but
        # has other iiss data, also should return -1
        dummy_iiss_data_list = [self.dummy_header, self.dummy_gv, self.dummy_prep]
        current_db = self.rc_data_storage.db
        for iiss_data in dummy_iiss_data_list:
            current_db.put(iiss_data.make_key(), iiss_data.make_value())

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
        current_db_path = os.path.join(self.path, RcDataStorage._CURRENT_IISS_DB_NAME)

        def path_exists(path):
            if path == current_db_path:
                return True
            else:
                return False
        mocked_path_exists.side_effect = path_exists

        valid_block_height = 1
        expected_iiss_db_path = os.path.join(self.path,
                                             RcDataStorage._IISS_RC_DB_NAME_PREFIX + f"{valid_block_height}")
        actual_path = self.rc_data_storage.create_db_for_calc(valid_block_height)
        self.assertEqual(expected_iiss_db_path, actual_path)

        mocked_rename.assert_called_with(current_db_path, expected_iiss_db_path)
        mocked_iiss_db_from_path.assert_called_with(current_db_path)

        expected_last_tx_index = -1
        self.assertEqual(expected_last_tx_index, self.rc_data_storage._db_iiss_tx_index)

    def test_commit_without_iiss_tx(self):
        # todo: should supplement this unit tests
        # success case: when there is no iiss_tx data, index should not be increased
        dummy_iiss_data_list_without_iiss_tx = [self.dummy_header, [self.dummy_gv, self.dummy_prep]]
        self.rc_data_storage.commit(dummy_iiss_data_list_without_iiss_tx)
        expected_index = -1
        self.assertEqual(expected_index, self.rc_data_storage._db_iiss_tx_index)
        self.assertEqual(None,
                         self.rc_data_storage.db.get(self.rc_data_storage._KEY_FOR_GETTING_LAST_TRANSACTION_INDEX))

    def test_commit_with_iiss_tx(self):
        # todo: should supplement this unit tests
        # success case: when there is iiss_tx data, index should be increased
        for expected_index in range(0, 10):
            dummy_iiss_data_list = [self.dummy_header, [self.dummy_gv, self.dummy_prep, self.dummy_tx]]
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

    # below is for integrate tests

    # def test_create_db_for_calc_current_db_exists(self):
    #     valid_block_height = 1
    #     # failure case: call this method when current db is not exists
    #     self.rc_data_storage._db.close()
    #     # remove current path
    #     rmtree(self.current_db_path, ignore_errors=True)
    #
    #     self.assertRaises(DatabaseException, self.rc_data_storage.create_db_for_calc, valid_block_height)
    #
    # def test_create_db_for_calc_iiss_db_exists(self):
    #     valid_block_height = 1
    #     # failure case: call this method when same block height iiss db is exists
    #     iiss_db_name = self.rc_data_storage._IISS_RC_DB_NAME_PREFIX + f"{valid_block_height}"
    #     dummy_iiss_db_path = os.path.join(self.current_db_path, f"../{iiss_db_name}")
    #     os.mkdir(dummy_iiss_db_path)
    #     self.assertRaises(DatabaseException, self.rc_data_storage.create_db_for_calc, valid_block_height)
    #
    # def test_create_db_for_calc_valid_block_height(self):
    #     # success case: when input valid block height, should create iiss_db and return path
    #     valid_block_height = 1
    #     expected_iiss_db_path = os.path.join(self.test_db_path,
    #                                          RcDataStorage._IISS_RC_DB_NAME_PREFIX + f"{valid_block_height}")
    #     actual_path = self.rc_data_storage.create_db_for_calc(valid_block_height)
    #     self.assertEqual(expected_iiss_db_path, actual_path)
    #     assert os.path.exists(self.current_db_path)
    #     assert os.path.exists(expected_iiss_db_path)
    #
    #     self.assertRaises(Exception, plyvel.DB, self.current_db_path, error_if_exists=True)
    #     self.assertRaises(Exception, plyvel.DB, expected_iiss_db_path, error_if_exists=True)
    #     expected_last_tx_index = -1
    #     self.assertEqual(expected_last_tx_index, self.rc_data_storage._db_iiss_tx_index)
    #
    # def test_commit_without_iiss_tx(self):
    #     # success case: when there is no iiss_tx data, index should not be increased
    #     dummy_iiss_data_list_without_iiss_tx = [self.dummy_header, [self.dummy_gv, self.dummy_prep]]
    #     self.rc_data_storage.commit(dummy_iiss_data_list_without_iiss_tx)
    #     expected_index = -1
    #     self.assertEqual(expected_index, self.rc_data_storage._db_iiss_tx_index)
    #     self.assertEqual(None,
    #                      self.rc_data_storage.db.get(self.rc_data_storage._KEY_FOR_GETTING_LAST_TRANSACTION_INDEX))
    #
    # def test_commit_with_iiss_tx(self):
    #     # success case: when there is iiss_tx data, index should be increased
    #     for expected_index in range(0, 10):
    #         dummy_iiss_data_list = [self.dummy_header, [self.dummy_gv, self.dummy_prep, self.dummy_tx]]
    #         self.rc_data_storage.commit(dummy_iiss_data_list)
    #         self.assertEqual(expected_index, self.rc_data_storage._db_iiss_tx_index)
    #
    #         recorded_index = \
    #             int.from_bytes(
    #                 self.rc_data_storage.db.get(self.rc_data_storage._KEY_FOR_GETTING_LAST_TRANSACTION_INDEX), 'big')
    #         self.assertEqual(expected_index, recorded_index)
    #
    #         iiss_tx_db = self.rc_data_storage.db.get_sub_db(prefix=b'TX')._db
    #         key, _ = next(iiss_tx_db.iterator(reverse=True))
    #         actual_last_tx_index = int.from_bytes(key[2:], 'big')
    #         self.assertEqual(expected_index, actual_last_tx_index)
