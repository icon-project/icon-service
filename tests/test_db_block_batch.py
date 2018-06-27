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

from iconservice.base.address import Address, AddressPrefix
from iconservice.base.block import Block
from iconservice.database.batch import BlockBatch, TransactionBatch
from iconservice.utils import sha3_256, int_to_bytes


class TestBlockBatch(unittest.TestCase):
    def setUp(self):
        block_hash =\
            'd1e7281723bfa4c9e358080bfe57a6c36c67eba94a974d8a2ea4c3cdb0229399'
        block = Block(
            block_height=0,
            block_hash=block_hash,
            timestamp=0,
            prev_hash='')
        self.batch = BlockBatch(block)

        score_address = Address.from_string(f'cx{"0" * 40}')
        address = Address.from_string(f'hx{"1" * 40}')
        self.batch.put(score_address, address, int_to_bytes(1))

    def test_property(self):
        self.assertEqual(0, self.batch.block.height)
        self.assertEqual(
            'd1e7281723bfa4c9e358080bfe57a6c36c67eba94a974d8a2ea4c3cdb0229399',
            self.batch.block.hash)

    def test_len(self):
        self.assertEqual(1, len(self.batch))

    def test_get_item(self):
        score_address = Address.from_string(f'cx{"0" * 40}')
        address = Address.from_string(f'hx{"1" * 40}')
        self.assertEqual(
            1, int.from_bytes(self.batch[score_address][address], 'big'))

    def test_put_tx_batch(self):
        tx_batch = TransactionBatch('')

        score_address = Address.from_string(f'cx{"f" * 40}')
        address = Address.from_string(f'hx{"2" * 40}')
        tx_batch.put(score_address, address, int_to_bytes(2))
        address = Address.from_string(f'hx{"3" * 40}')
        tx_batch.put(score_address, address, int_to_bytes(3))
        self.batch.put_tx_batch(tx_batch)

        self.assertEqual(2, len(self.batch))

        address = Address.from_string(f'hx{"2" * 40}')
        self.assertEqual(
            2, int.from_bytes(self.batch[score_address][address], 'big'))
        address = Address.from_string(f'hx{"3" * 40}')
        self.assertEqual(
            3, int.from_bytes(self.batch[score_address][address], 'big'))

        score_address = Address.from_string(f'cx{"0" * 40}')
        address = Address.from_string(f'hx{"1" * 40}')
        self.assertEqual(
            1, int.from_bytes(self.batch[score_address][address], 'big'))

    def test_put(self):
        score_address = Address.from_string(f'cx{"0" * 40}')
        self.assertEqual(1, len(self.batch[score_address]))

        address = Address.from_string(f'hx{"2" * 40}')
        self.batch.put(score_address, address, int_to_bytes(2))
        self.assertEqual(1, len(self.batch))
        self.assertEqual(
            2, int.from_bytes(self.batch[score_address][address], 'big'))
        self.assertEqual(2, len(self.batch[score_address]))

        score_address = Address.from_string(f'cx{"b" * 40}')
        address = Address.from_string(f'hx{"2" * 40}')
        self.batch.put(score_address, address, int_to_bytes(100))
        self.assertEqual(2, len(self.batch))
        self.assertEqual(
            100, int.from_bytes(self.batch[score_address][address], 'big'))

    def test_digest(self):
        self.batch.clear()
        self.assertEqual(sha3_256(b''), self.batch.digest())

        score_address1 = Address.from_data(
            AddressPrefix.CONTRACT, b'score_address1')

        data = [score_address1.body]
        for i in range(3):
            value = int_to_bytes(i)
            key = Address.from_data(AddressPrefix.EOA, value).body
            self.batch.put(score_address1, key, value)

            data.append(key)
            data.append(value)

        seq1 = b'|'.join(data)
        expected1 = sha3_256(seq1)
        ret1 = self.batch.digest()
        self.assertEqual(expected1, ret1)

        data = [score_address1.body]
        self.batch.clear()

        for i in range(2, -1, -1):
            value = int_to_bytes(i)
            key = Address.from_data(AddressPrefix.EOA, value).body
            self.batch.put(score_address1, key, value)

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
