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

import unittest

from iconservice.iiss.database.iiss_batch import IissBatchManager


class TestIissBatchManager(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_init(self):
        # failure case: when input index under -1, should raise exception
        self.assertRaises(Exception, IissBatchManager, -2)

        # success case: when input index -1 or more, should create new instance successfully
        # and recorded index should be + 1
        for i in range(-1, 5):
            batch_manager = IissBatchManager(i)
            expected_index = i + 1
            actual_index = batch_manager._db_iiss_tx_index
            self.assertEqual(expected_index, actual_index)

    def test_get_batch(self):
        batch_manager = IissBatchManager(-1)
        # set batch to batch manager
        for i in range(0, 10):
            batch = batch_manager.get_batch(i.to_bytes(1, "big"))
            batch._batch_iiss_tx_index = i
            for j in range(0, i):
                batch[f"{j}"] = i

        # success case: when input non-existing block hash, should return new instance of IissBatch
        batch = batch_manager.get_batch(b'non_exist_block_hash')
        expected_index = batch_manager._db_iiss_tx_index
        actual_index = batch.batch_iiss_tx_index
        self.assertEqual(expected_index, actual_index)
        self.assertEqual(0, len(batch))

        # success case: when input existing block hash, should return correct instance of batch
        for i in range(0, 10):
            batch = batch_manager.get_batch(i.to_bytes(1, "big"))
            actual_batch_tx_index = batch.batch_iiss_tx_index
            self.assertEqual(i, actual_batch_tx_index)
            for j in range(0, i):
                self.assertEqual(i, batch[f"{j}"])

    def test_update_index_and_clear_mapper(self):
        batch_manager = IissBatchManager(-1)
        arbitrary_block_hash = b"block_hash"
        expected_tx_index = 5
        batch = batch_manager.get_batch(arbitrary_block_hash)
        batch._batch_iiss_tx_index = expected_tx_index

        # failure case: when input non-existing block hash as a param, should raise an error
        self.assertRaises(Exception,
                          batch_manager.update_index_and_clear_mapper,
                          b'non_exist_block_hash')

        # success case: when input existing block hash as a param, db_transaction_index variable
        # should be updated to the batch's transaction index which is mapped with block hash
        batch_manager.update_index_and_clear_mapper(arbitrary_block_hash)
        actual_tx_index = batch_manager._db_iiss_tx_index
        self.assertEqual(expected_tx_index, actual_tx_index)
