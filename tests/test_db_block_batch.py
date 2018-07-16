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


import unittest

from iconservice.base.address import AddressPrefix
from iconservice.base.block import Block
from iconservice.database.batch import BlockBatch, TransactionBatch
from iconservice.utils import sha3_256, int_to_bytes
from iconservice.icon_constant import DATA_BYTE_ORDER
from tests import create_block_hash, create_address


class TestBlockBatch(unittest.TestCase):
    def setUp(self):
        self.block_hash = create_block_hash(b'block')
        self.prev_hash = create_block_hash(b'prev')
        block = Block(
            block_height=0,
            block_hash=self.block_hash,
            timestamp=0,
            prev_hash=self.prev_hash)
        self.batch = BlockBatch(block)

        self.score_address = create_address(AddressPrefix.CONTRACT, b'score')
        self.addr1 = create_address(AddressPrefix.EOA, b'addr1')
        self.batch.put(self.score_address, self.addr1, int_to_bytes(1))

    def test_property(self):
        self.assertEqual(0, self.batch.block.height)
        self.assertEqual(
            self.block_hash,
            self.batch.block.hash)

    def test_len(self):
        self.assertEqual(1, len(self.batch))

    def test_get_item(self):
        self.assertEqual(
            1, int.from_bytes(self.batch[self.score_address][self.addr1], DATA_BYTE_ORDER))

    def test_put_tx_batch(self):
        tx_batch = TransactionBatch('')

        score_address = create_address(AddressPrefix.CONTRACT, b'score1')
        address = create_address(AddressPrefix.EOA, b'addr2')
        tx_batch.put(score_address, address, int_to_bytes(2))
        address = create_address(AddressPrefix.EOA, b'addr3')
        tx_batch.put(score_address, address, int_to_bytes(3))
        self.batch.put_tx_batch(tx_batch)

        self.assertEqual(2, len(self.batch))

        address = create_address(AddressPrefix.EOA, b'addr2')
        self.assertEqual(
            2, int.from_bytes(self.batch[score_address][address], DATA_BYTE_ORDER))
        address = create_address(AddressPrefix.EOA, b'addr3')
        self.assertEqual(
            3, int.from_bytes(self.batch[score_address][address], DATA_BYTE_ORDER))

        self.assertEqual(
            1, int.from_bytes(self.batch[self.score_address][self.addr1], DATA_BYTE_ORDER))

    def test_put(self):
        self.assertEqual(1, len(self.batch[self.score_address]))

        address = create_address(AddressPrefix.EOA, b'addr2')
        self.batch.put(self.score_address, address, int_to_bytes(2))
        self.assertEqual(1, len(self.batch))
        self.assertEqual(
            2, int.from_bytes(self.batch[self.score_address][address], DATA_BYTE_ORDER))
        self.assertEqual(2, len(self.batch[self.score_address]))

        score_address = create_address(AddressPrefix.CONTRACT, b'score2')
        address = create_address(AddressPrefix.EOA, b'addr2')
        self.batch.put(score_address, address, int_to_bytes(100))
        self.assertEqual(2, len(self.batch))
        self.assertEqual(
            100, int.from_bytes(self.batch[score_address][address], DATA_BYTE_ORDER))

    def test_digest(self):
        self.batch.clear()
        self.assertEqual(sha3_256(b''), self.batch.digest())

        score_address = create_address(AddressPrefix.CONTRACT, b'score1')

        data = [score_address.body]
        for i in range(3):
            value = int_to_bytes(i)
            key = create_address(AddressPrefix.EOA, value).body
            self.batch.put(score_address, key, value)

            data.append(key)
            data.append(value)

        seq1 = b'|'.join(data)
        expected1 = sha3_256(seq1)
        ret1 = self.batch.digest()
        self.assertEqual(expected1, ret1)

        data = [score_address.body]
        self.batch.clear()

        for i in range(2, -1, -1):
            value = int_to_bytes(i)
            key = create_address(AddressPrefix.EOA, value).body
            self.batch.put(score_address, key, value)

            data.append(key)
            data.append(value)

        seq2 = b'|'.join(data)
        expected2 = sha3_256(seq2)
        ret2 = self.batch.digest()
        self.assertEqual(expected2, ret2)

        self.assertTrue(expected1 != expected2)
        self.assertTrue(ret1 != ret2)

        print(seq1.hex())
        print(ret1.hex())
        print(seq2.hex())
        print(ret2.hex())
