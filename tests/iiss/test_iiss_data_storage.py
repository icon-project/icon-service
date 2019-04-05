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
from shutil import rmtree
from unittest.mock import Mock

import plyvel

from iconservice.iiss.database.iiss_batch import IissBatch
from iconservice.iiss.database.iiss_db import IissDatabase
from iconservice.iiss.iiss_data_creator import *
from iconservice.iiss.iiss_data_storage import IissDataStorage
from iconservice.iiss.iiss_msg_data import IissTxType
from tests import create_address


class TestIissDataStorage(unittest.TestCase):
    test_db_path: str = os.path.join(os.getcwd(), ".storage_test_db")

    def setUp(self):
        os.mkdir(self.test_db_path)
        self.iiss_data_storage = IissDataStorage()
        self.iiss_data_storage.open(self.test_db_path)

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
        self.dummy_tx.index = 0
        self.dummy_tx.address = create_address()
        self.dummy_tx.block_height =  dummy_block_height
        self.dummy_tx.type = IissTxType.PREP_REGISTER
        self.dummy_tx.data = PRepRegisterTx()

    def tearDown(self):
        rmtree(self.test_db_path, ignore_errors=True)

    def test_open(self):
        # close and remove leveldb(current_db) which is set on setUp method (for test open method)
        self.iiss_data_storage.close()
        rmtree(self.iiss_data_storage._current_db_path)

        # failure case: when input non-existing path, should raise error
        iiss_data_storage = IissDataStorage()
        non_exist_path = os.path.join(self.test_db_path, "non_exist_path")
        self.assertRaises(Exception, iiss_data_storage.open, non_exist_path)

        # success case: when input existing path, make path of current_db and iiss_rc_db
        # and generate current level db(if not exist)
        iiss_data_storage.open(self.test_db_path)
        expected_current_db_path = os.path.join(self.test_db_path, IissDataStorage._CURRENT_IISS_DB_NAME)
        expected_iiss_rc_db_path = os.path.join(self.test_db_path, IissDataStorage._IISS_RC_DB_NAME_WITHOUT_BLOCK_HEIGHT)
        actual_current_db_path = iiss_data_storage._current_db_path
        actual_iiss_rc_db_path = iiss_data_storage._iiss_rc_db_path

        self.assertEqual(expected_current_db_path, actual_current_db_path)
        self.assertEqual(expected_iiss_rc_db_path, actual_iiss_rc_db_path)
        assert os.path.exists(actual_current_db_path)
        assert not os.path.exists(actual_iiss_rc_db_path)

    def test_put(self):
        # success case: when input IissTxData, iiss_data's index variable is assigned as batch's index
        # and batch's increase_iiss_tx_index should be called
        self.iiss_data_storage = IissDataStorage()
        self.iiss_data_storage.open(self.test_db_path)

        expected_index = 5
        expected_key = b"key"
        expected_value = b"value"

        batch = IissBatch(expected_index)
        mock_iiss_tx_data = Mock(spec=IissTxData)
        mock_iiss_tx_data.attach_mock(Mock(return_value=expected_key), "make_key")
        mock_iiss_tx_data.attach_mock(Mock(return_value=expected_value), "make_value")
        self.iiss_data_storage.put(batch, mock_iiss_tx_data)
        self.assertEqual(expected_index, mock_iiss_tx_data.index)
        self.assertEqual(expected_value, batch[expected_key])
        self.assertEqual(expected_index + 1, batch.batch_iiss_tx_index)

        # success case: when input other IissData, just encoded key value is updated to batch
        mocked_iiss_data_list = [Mock(spec=PrepsData),
                                 Mock(spec=IissGovernanceVariable),
                                 Mock(spec=IissHeader)]

        for index, mocked_iiss_data in enumerate(mocked_iiss_data_list):
            expected_index = index
            expected_key = b"key" + index.to_bytes(1, 'big')
            expected_value = b"value" + index.to_bytes(1, 'big')

            batch = IissBatch(expected_index)
            mocked_iiss_data.attach_mock(Mock(return_value=expected_key), "make_key")
            mocked_iiss_data.attach_mock(Mock(return_value=expected_value), "make_value")

            self.iiss_data_storage.put(batch, mocked_iiss_data)
            self.assertEqual(expected_value, batch[expected_key])
            self.assertEqual(expected_index, batch.batch_iiss_tx_index)

    def test_load_last_tx_index(self):
        # success case: when inquiring tx index while current_db has no data recorded should return -1
        expected_tx_index = -1
        actual_tx_index = self.iiss_data_storage.load_last_transaction_index()
        self.assertEqual(expected_tx_index, actual_tx_index)

        # success case: when inquiring tx index while current_db has no tx data recorded but
        # has other iiss data, also should return -1
        dummy_iiss_data_list = [self.dummy_header, self.dummy_gv, self.dummy_prep]
        current_db = self.iiss_data_storage.db
        for iiss_data in dummy_iiss_data_list:
            current_db.put(iiss_data.make_key(), iiss_data.make_value())

        expected_tx_index = -1
        actual_tx_index = self.iiss_data_storage.load_last_transaction_index()
        self.assertEqual(expected_tx_index, actual_tx_index)

        # success case: when inquiring tx index while current_db has tx data recorded, should return
        # correct index (i.e. last index number)
        for index in range(0, 200):
            self.dummy_tx.index = index
            current_db.put(self.dummy_tx.make_key(), self.dummy_tx.make_value())

            expected_tx_index = index
            actual_tx_index = self.iiss_data_storage.load_last_transaction_index()
            self.assertEqual(expected_tx_index, actual_tx_index)

    def test_create_db_for_calc_invalid_block_height(self):
        # failure case: when input block height less than or equal to 0, raise exception
        for block_height in range(-2, 1):
            self.assertRaises(Exception, self.iiss_data_storage.create_db_for_calc, block_height)

    def test_create_db_for_calc_current_db_exists(self):
        valid_block_height = 1
        # failure case: call this method when current db is not exists
        self.iiss_data_storage.close()
        # remove current path
        rmtree(self.iiss_data_storage._current_db_path, ignore_errors=True)

        self.assertRaises(Exception, self.iiss_data_storage.create_db_for_calc, valid_block_height)

    def test_create_db_for_calc_iiss_db_exists(self):
        valid_block_height = 1
        # failure case: call this method when same block height iiss db is exists
        dummy_iiss_db_dir = self.iiss_data_storage._iiss_rc_db_path + f"{valid_block_height}"
        os.mkdir(dummy_iiss_db_dir)
        self.assertRaises(Exception, self.iiss_data_storage.create_db_for_calc, valid_block_height)

    def test_create_db_for_calc_valid_block_height(self):
        # success case: when input valid block height, should create iiss_db and return path
        valid_block_height = 1
        current_db_path = self.iiss_data_storage._current_db_path
        expected_iiss_db_path = os.path.join(self.test_db_path,
                                             IissDataStorage._IISS_RC_DB_NAME_WITHOUT_BLOCK_HEIGHT + f"{valid_block_height}")
        actual_path = self.iiss_data_storage.create_db_for_calc(valid_block_height)
        self.assertEqual(expected_iiss_db_path, actual_path)
        assert os.path.exists(current_db_path)
        assert os.path.exists(expected_iiss_db_path)

        self.assertRaises(Exception, plyvel.DB, current_db_path, error_if_exists=True)
        self.assertRaises(Exception, plyvel.DB, expected_iiss_db_path, error_if_exists=True)

    def test_remove_db_for_calc_invalid_block_height(self):
        # failure case: when input block height less than or equal to 0, raise exception
        for block_height in range(-2, 1):
            self.assertRaises(Exception, self.iiss_data_storage.remove_db_for_calc, block_height)

    def test_remove_db_for_calc_no_db_corresponding_to_block_height(self):
        # failure case: when there is no db corresponding to block height, raise exception
        invalid_block_height = 1_000_000
        self.assertRaises(Exception, self.iiss_data_storage.remove_db_for_calc, invalid_block_height)
        pass

    def test_remove_db_for_calc_db_occupied_by_another_process(self):
        # failure case: when the iiss_db corresponding to block height is occupied by another process,
        # should raise exception

        # create dummy iiss_db
        valid_block_height = 1
        iiss_db_path = self.iiss_data_storage._iiss_rc_db_path + f"{valid_block_height}"

        # '_' for garbage collector
        _ = IissDatabase.from_path(iiss_db_path)
        assert os.path.exists(iiss_db_path)

        self.assertRaises(Exception, self.iiss_data_storage.remove_db_for_calc, valid_block_height)

    def test_remove_db_for_calc_valid_block_height(self):
        # success case: when there is no db corresponding to block height, remove db
        valid_block_height = 1
        iiss_db_path = self.iiss_data_storage._iiss_rc_db_path + f"{valid_block_height}"
        dummy_iiss_db = IissDatabase.from_path(iiss_db_path)
        assert os.path.exists(iiss_db_path)
        # close db
        dummy_iiss_db.close()
        self.iiss_data_storage.remove_db_for_calc(valid_block_height)

        assert not os.path.exists(iiss_db_path)
