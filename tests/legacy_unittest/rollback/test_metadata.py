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
import random
import time
import unittest
from typing import Optional

from iconservice.base.block import Block
from iconservice.rollback.metadata import Metadata


class TestMetadata(unittest.TestCase):
    def setUp(self) -> None:
        block_height: int = random.randint(1000, 10000)
        block_hash: bytes = os.urandom(32)
        prev_block_hash: bytes = os.urandom(32)
        timestamp_us: int = int(time.time() * 1000_000)
        cumulative_fee = random.randint(0, 10000)

        last_block = Block(
            block_height=block_height,
            block_hash=block_hash,
            timestamp=timestamp_us,
            prev_hash=prev_block_hash,
            cumulative_fee=cumulative_fee
        )

        block_height = last_block.height - 10
        block_hash: bytes = os.urandom(32)
        term_start_block_height = block_height = block_height - 20
        last_block: 'Block' = last_block

        metadata = Metadata(block_height, block_hash, term_start_block_height, last_block)
        assert metadata.block_height == block_height
        assert metadata.block_hash == block_hash
        assert metadata.term_start_block_height == term_start_block_height
        assert metadata.last_block == last_block

        self.metadata = metadata
        self.block_height = block_height
        self.block_hash = block_hash
        self.term_start_block_height = term_start_block_height
        self.last_block = last_block

    def test_from_bytes(self):
        metadata = self.metadata

        buf: bytes = metadata.to_bytes()
        assert isinstance(buf, bytes)

        metadata2 = Metadata.from_bytes(buf)
        assert metadata2 == metadata
        assert id(metadata2) != id(metadata)
        assert metadata2.block_height == self.block_height
        assert metadata2.block_hash == self.block_hash
        assert metadata2.term_start_block_height == self.term_start_block_height
        assert metadata2.last_block == self.last_block

    def test_load(self):
        path = "./ROLLBACK_METADATA"
        metadata: Optional['Metadata'] = Metadata.load(path)
        assert metadata is None

        self.metadata.save(path)

        metadata = Metadata.load(path)
        assert metadata == self.metadata
        assert id(metadata) != id(self.metadata)

        os.remove(path)
