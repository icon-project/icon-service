#!/usr/bin/env python3
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
from iconservice.base.block import Block
from iconservice.icon_constant import DEFAULT_BYTE_SIZE
from tests import create_block_hash


class TestBlock(unittest.TestCase):
    def test_Block_from_bytes_to_bytes(self):
        block_hash = create_block_hash()
        prev_block_hash = create_block_hash()
        block1 = Block(1, block_hash, 100, prev_block_hash)
        data = Block.to_bytes(block1)
        self.assertEqual(bytes(block1), data)
        self.assertTrue(isinstance(data, bytes))
        self.assertEqual(1+DEFAULT_BYTE_SIZE+DEFAULT_BYTE_SIZE+DEFAULT_BYTE_SIZE+DEFAULT_BYTE_SIZE, len(data))

        block2 = Block.from_bytes(data)
        self.assertEqual(block2.height, 1)
        self.assertEqual(block2.hash, block_hash)
        self.assertEqual(block2.timestamp, 100)
        self.assertEqual(block2.prev_hash, prev_block_hash)

    def test_Block_from_bytes_to_bytes(self):
        block_hash = create_block_hash()
        prev_block_hash = None
        block1 = Block(1, block_hash, 100, prev_block_hash)
        data = Block.to_bytes(block1)
        self.assertEqual(bytes(block1), data)
        self.assertTrue(isinstance(data, bytes))
        self.assertEqual(1+DEFAULT_BYTE_SIZE+DEFAULT_BYTE_SIZE+DEFAULT_BYTE_SIZE+DEFAULT_BYTE_SIZE, len(data))

        block2 = Block.from_bytes(data)
        self.assertEqual(block2.height, 1)
        self.assertEqual(block2.hash, block_hash)
        self.assertEqual(block2.timestamp, 100)
        self.assertEqual(block2.prev_hash, prev_block_hash)

    def test_str(self):

        block = Block(1,
                      create_block_hash(),
                      100,
                      create_block_hash())

        text = str(block)
        print(text)


if __name__ == '__main__':
    unittest.main()
