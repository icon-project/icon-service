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

from iconservice.icon_constant import REV_DECENTRALIZATION, RC_DB_VERSION_0, RC_DB_VERSION_2
from iconservice.iconscore.icon_score_context import IconScoreContext
from iconservice.iiss.reward_calc import RewardCalcStorage
from iconservice.iiss.reward_calc.data_creator import *
from iconservice.iiss.reward_calc.msg_data import TxType
from iconservice.iiss.reward_calc.storage import get_rc_version
from iconservice.utils.msgpack_for_db import MsgPackForDB
from tests import create_address
from tests.iiss.mock_rc_db import MockIissDataBase
from tests.mock_db import MockPlyvelDB
from tests.mock_generator import KEY_VALUE_DB_PATH


class TestRcDataStorage(unittest.TestCase):
    @patch('iconservice.iiss.reward_calc.storage.Storage._supplement_db')
    @patch(f'{KEY_VALUE_DB_PATH}.from_path')
    @patch('os.path.exists')
    def setUp(self, _, mocked_rc_db_from_path, mocked_supplement_db) -> None:
        context: 'IconScoreContext' = IconScoreContext()
        context.revision = REV_DECENTRALIZATION
        self.path = ""
        mocked_rc_db_from_path.side_effect = MockIissDataBase.from_path
        self.rc_data_storage = RewardCalcStorage()
        self.rc_data_storage.open(context, self.path)

        dummy_block_height = 1

        self.dummy_header = Header()
        self.dummy_header.block_height = dummy_block_height
        self.dummy_header.version = RC_DB_VERSION_0

        self.dummy_gv = GovernanceVariable()
        self.dummy_gv.block_height = dummy_block_height
        self.dummy_gv.config_main_prep_count = 22
        self.dummy_gv.config_sub_prep_count = 78
        self.dummy_gv.calculated_irep = 1
        self.dummy_gv.reward_rep = 1000

        self.dummy_prep = PRepsData()
        self.dummy_prep.block_height = dummy_block_height
        self.dummy_prep.total_delegation = 10
        self.dummy_prep.prep_list = []

        self.dummy_tx = TxData()
        self.dummy_tx.address = create_address()
        self.dummy_tx.block_height = dummy_block_height
        self.dummy_tx.type = TxType.PREP_REGISTER
        self.dummy_tx.data = PRepRegisterTx()

    def tearDown(self):
        pass

    @patch('iconservice.iiss.reward_calc.storage.Storage._supplement_db')
    @patch(f'{KEY_VALUE_DB_PATH}.from_path')
    @patch('os.path.exists')
    def test_rc_storage_check_data_format_by_revision(self, _, mocked_rc_db_from_path, mocked_supplement_db):
        mocked_rc_db_from_path.side_effect = MockIissDataBase.from_path
        context: 'IconScoreContext' = IconScoreContext()
        for revision in range(REV_DECENTRALIZATION):
            context.revision = revision
            current_version = get_rc_version(revision)
            rc_data_storage = RewardCalcStorage()
            rc_data_storage.open(context, self.path)
            self.dummy_header.version = current_version
            self.dummy_header.revision = revision
            self.dummy_gv.version = current_version
            iiss_data = [self.dummy_header, self.dummy_gv]
            rc_data_storage.commit(iiss_data)

            header: bytes = rc_data_storage._db.get(self.dummy_header.make_key())
            header: 'Header' = Header.from_bytes(header)
            self.assertEqual(RC_DB_VERSION_0, header.version)
            self.assertEqual(0, header.revision)

            gv_key: bytes = self.dummy_gv.make_key()
            gv: bytes = rc_data_storage._db.get(self.dummy_gv.make_key())
            gv: 'GovernanceVariable' = GovernanceVariable.from_bytes(gv_key, gv)
            self.assertEqual(RC_DB_VERSION_0, gv.version)
            self.assertEqual(0, gv.config_main_prep_count)
            self.assertEqual(0, gv.config_sub_prep_count)

        revision = REV_DECENTRALIZATION
        current_version = get_rc_version(revision)
        rc_data_storage = RewardCalcStorage()
        rc_data_storage.open(context, self.path)
        self.dummy_header.version = current_version
        self.dummy_header.revision = revision
        self.dummy_gv.version = current_version
        iiss_data = [self.dummy_header, self.dummy_gv]
        rc_data_storage.commit(iiss_data)

        header: bytes = rc_data_storage._db.get(self.dummy_header.make_key())
        header: 'Header' = Header.from_bytes(header)
        self.assertEqual(RC_DB_VERSION_2, header.version)
        self.assertEqual(REV_DECENTRALIZATION, header.revision)

        gv_key: bytes = self.dummy_gv.make_key()
        gv: bytes = rc_data_storage._db.get(self.dummy_gv.make_key())
        gv: 'GovernanceVariable' = GovernanceVariable.from_bytes(gv_key, gv)
        self.assertEqual(RC_DB_VERSION_2, gv.version)
        self.assertEqual(self.dummy_gv.config_main_prep_count, gv.config_main_prep_count)
        self.assertEqual(self.dummy_gv.config_sub_prep_count, gv.config_sub_prep_count)

    @patch('iconservice.iiss.reward_calc.storage.Storage._supplement_db')
    @patch(f'{KEY_VALUE_DB_PATH}.from_path')
    @patch('os.path.exists')
    def test_open(self, mocked_path_exists, mocked_rc_db_from_path, mocked_supplement_db):
        # success case: when input existing path, make path of current_db and iiss_rc_db
        # and generate current level db(if not exist)
        context: 'IconScoreContext' = IconScoreContext()
        context.revision = REV_DECENTRALIZATION
        rc_data_storage = RewardCalcStorage()
        test_db_path: str = os.path.join(os.getcwd(), ".storage_test_db")

        expected_current_db_path = os.path.join(test_db_path, RewardCalcStorage._CURRENT_IISS_DB_NAME)

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
        mocked_rc_db_from_path.side_effect = from_path
        rc_data_storage.open(context, test_db_path)
        mocked_path_exists.assert_called()

        expected_tx_index = -1
        actual_tx_index = rc_data_storage._db_iiss_tx_index
        self.assertEqual(expected_tx_index, actual_tx_index)

    def test_load_last_tx_index(self):
        current_db = self.rc_data_storage._db
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

    @patch(f'{KEY_VALUE_DB_PATH}.from_path')
    @patch('os.rename')
    @patch('os.path.exists')
    def test_create_db_for_calc_valid_block_height(self, mocked_path_exists, mocked_rename, mocked_rc_db_from_path):

        mocked_rc_db_from_path.side_effect = MockIissDataBase.from_path
        current_db_path = os.path.join(self.path, RewardCalcStorage._CURRENT_IISS_DB_NAME)

        # todo: to be refactored
        def path_exists(path):
            if path == current_db_path:
                return True
            else:
                return False
        mocked_path_exists.side_effect = path_exists

        valid_block_height = 1
        expected_iiss_db_path = os.path.join(self.path,
                                             RewardCalcStorage._IISS_RC_DB_NAME_PREFIX + f"{valid_block_height}")
        # failure case: When input valid block height and HD is not exists, should return None
        actual_ret_path = self.rc_data_storage.create_db_for_calc(valid_block_height)
        self.assertEqual(None, actual_ret_path)

        # success case: When input valid block height and HD is exists, should create iiss_db and return path
        self.rc_data_storage._db.put(self.dummy_header.make_key(), self.dummy_header.make_value())
        actual_ret_path = self.rc_data_storage.create_db_for_calc(valid_block_height)
        self.assertEqual(expected_iiss_db_path, actual_ret_path)

        mocked_rename.assert_called_with(current_db_path, expected_iiss_db_path)
        mocked_rc_db_from_path.assert_called_with(current_db_path)

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
                         self.rc_data_storage._db.get(self.rc_data_storage._KEY_FOR_GETTING_LAST_TRANSACTION_INDEX))

    def test_commit_with_iiss_tx(self):
        # todo: should supplement this unit tests
        # success case: when there is iiss_tx data, index should be increased
        for expected_index in range(0, 10):
            dummy_iiss_data_list = [self.dummy_header, self.dummy_gv, self.dummy_prep, self.dummy_tx]
            self.rc_data_storage.commit(dummy_iiss_data_list)
            self.assertEqual(expected_index, self.rc_data_storage._db_iiss_tx_index)

            recorded_index = \
                int.from_bytes(
                    self.rc_data_storage._db.get(self.rc_data_storage._KEY_FOR_GETTING_LAST_TRANSACTION_INDEX), 'big')
            self.assertEqual(expected_index, recorded_index)

            last_tx_index = -1
            for key in self.rc_data_storage._db.iterator():
                if key[:2] == b'TX':
                    temp_tx_index = int.from_bytes(key[2:], 'big')
                    if last_tx_index < temp_tx_index:
                        last_tx_index = temp_tx_index
            self.assertEqual(expected_index, last_tx_index)

    def test_putting_i_score_data_on_current_db(self):
        # success case: If there is no prev_calc_period_issued_i_score, should return None
        actual_i_score, _ = self.rc_data_storage.get_calc_response_from_rc()
        assert actual_i_score == -1

        # success case: put i score and get i score from the db
        expected_i_score = 10_000
        expected_version = 0
        expected_block_height = 0
        self.rc_data_storage.put_calc_response_from_rc(expected_i_score, expected_block_height)
        i_score_db_data = MsgPackForDB.loads(self.rc_data_storage._db.get(self.rc_data_storage._KEY_FOR_CALC_RESPONSE_FROM_RC))
        assert i_score_db_data[0] == expected_version
        assert i_score_db_data[1] == expected_i_score
        assert i_score_db_data[2] == expected_block_height

        actual_i_score, _ = self.rc_data_storage.get_calc_response_from_rc()
        assert actual_i_score == expected_i_score

