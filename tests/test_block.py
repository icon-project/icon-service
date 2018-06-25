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
from tests import create_block_hash


class TestBlock(unittest.TestCase):
    def test_Block_from_bytes_to_bytes(self):
        block_hash = create_block_hash(b'block1')
        block_hash_str = f"0x{block_hash}"
        block1 = Block(1, block_hash_str, 100)
        data = Block.to_bytes(block1)
        self.assertEqual(bytes(block1), data)
        self.assertTrue(isinstance(data, bytes))
        self.assertEqual(1+32+32+32, len(data))

        block2 = Block.from_bytes(data)
        self.assertEqual(block2.height, 1)
        self.assertEqual(block2.hash, block_hash)
        self.assertEqual(block2.timestamp, 100)


if __name__ == '__main__':
    unittest.main()
