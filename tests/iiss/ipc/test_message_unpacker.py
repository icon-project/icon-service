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

import hashlib
import unittest

from iconservice.base.address import AddressPrefix
from iconservice.iiss.reward_calc.ipc.message import *
from iconservice.iiss.reward_calc.ipc.message_unpacker import MessageUnpacker
from iconservice.utils import int_to_bytes


class TestMessageUnpacker(unittest.TestCase):
    def setUp(self):
        self.unpacker = MessageUnpacker()

    def test_iterator(self):
        version: int = 7
        msg_id: int = 1234
        block_height: int = 100
        state_hash: bytes = hashlib.sha3_256(b'').digest()
        block_hash: bytes = hashlib.sha3_256(b'block_hash').digest()
        address = Address.from_data(AddressPrefix.EOA, b'')
        iscore: int = 5000
        success: bool = True

        messages = [
            (
                MessageType.VERSION,
                msg_id,
                (
                    version,
                    block_height
                )
            ),
            (
                MessageType.CALCULATE,
                msg_id,
                (
                    success,
                    block_height,
                    MsgPackForIpc.encode(iscore),
                    state_hash
                )
            ),
            (
                MessageType.QUERY,
                msg_id,
                (
                    address.to_bytes_including_prefix(),
                    int_to_bytes(iscore),
                    block_height
                )
            ),
            (
                MessageType.CLAIM,
                msg_id,
                (
                    address.to_bytes_including_prefix(),
                    block_height,
                    block_hash,
                    int_to_bytes(iscore)
                )
            ),
            (
                MessageType.COMMIT_BLOCK,
                msg_id,
                (
                    success,
                    block_height,
                    block_hash
                )
            )
        ]

        for message in messages:
            data: bytes = msgpack.packb(message)
            self.unpacker.feed(data)

        it = iter(self.unpacker)
        version_response = next(it)
        self.assertIsInstance(version_response, VersionResponse)
        self.assertEqual(version, version_response.version)

        calculate_response = next(it)
        self.assertIsInstance(calculate_response, CalculateResponse)
        self.assertTrue(calculate_response.success)
        self.assertEqual(block_height, calculate_response.block_height)
        self.assertEqual(state_hash, calculate_response.state_hash)

        query_response = next(it)
        self.assertIsInstance(query_response, QueryResponse)
        self.assertEqual(iscore, query_response.iscore)
        self.assertEqual(block_height, query_response.block_height)

        claim_response = next(it)
        self.assertIsInstance(claim_response, ClaimResponse)
        self.assertEqual(iscore, claim_response.iscore)
        self.assertEqual(block_height, claim_response.block_height)

        commit_block_response = next(it)
        self.assertIsInstance(commit_block_response, CommitBlockResponse)
        self.assertEqual(block_height, commit_block_response.block_height)
        self.assertEqual(block_hash, commit_block_response.block_hash)

        with self.assertRaises(StopIteration):
            next(it)

        for message in messages:
            data: bytes = msgpack.packb(message)
            self.unpacker.feed(data)

        expected = [
            version_response, calculate_response, query_response,
            claim_response, commit_block_response
        ]
        for expected_response, response in zip(expected, self.unpacker):
            self.assertEqual(expected_response.MSG_TYPE, response.MSG_TYPE)
            self.assertEqual(msg_id, response.msg_id)
