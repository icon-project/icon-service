#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright 2018 ICON Foundation
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


from typing import Optional

from iconservice.base.block import Block
from iconservice.icon_constant import DEFAULT_BYTE_SIZE, Revision
from tests import create_block_hash


def test_Block_from_bytes_to_bytes():
    # success case: struct
    block_hash = create_block_hash()
    prev_block_hash = create_block_hash()
    _test_block_from_bytes_to_bytes_struct(block_hash, prev_block_hash)

    # success case: msg pack
    _test_block_from_bytes_to_bytes_msg_pack(block_hash, prev_block_hash)


def test_Block_from_bytes_to_bytes_None_hash():
    # success case: struct
    block_hash = create_block_hash()
    prev_block_hash = None
    _test_block_from_bytes_to_bytes_struct(block_hash, prev_block_hash)

    # success case: msg pack
    _test_block_from_bytes_to_bytes_msg_pack(block_hash, prev_block_hash)


def _test_block_from_bytes_to_bytes_struct(block_hash: bytes, prev_block_hash: Optional[bytes]):
    revision = 0
    cumulative_fee = 10
    block1 = Block(1, block_hash, 100, prev_block_hash, cumulative_fee)
    data = Block.to_bytes(block1, revision)
    assert isinstance(data, bytes)
    assert 1 + DEFAULT_BYTE_SIZE + DEFAULT_BYTE_SIZE + DEFAULT_BYTE_SIZE + DEFAULT_BYTE_SIZE == len(data)

    block2 = Block.from_bytes(data)
    assert block2.height == 1
    assert block2.hash == block_hash
    assert block2.timestamp == 100
    assert block2.prev_hash == prev_block_hash
    # as cumulative fee is not recorded, result should be zero (not 10)
    assert block2.cumulative_fee == 0


def _test_block_from_bytes_to_bytes_msg_pack(block_hash: bytes, prev_block_hash: Optional[bytes]):
    revision = Revision.IISS.value
    cumulative_fee = 10
    block1 = Block(1, block_hash, 100, prev_block_hash, cumulative_fee)
    data = Block.to_bytes(block1, revision)
    assert isinstance(data, bytes)

    block2 = Block.from_bytes(data)
    assert block2.height == 1
    assert block2.hash == block_hash
    assert block2.timestamp == 100
    assert block2.prev_hash == prev_block_hash
    assert block2.cumulative_fee == cumulative_fee
