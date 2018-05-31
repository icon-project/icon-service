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

"""IconScoreEngine testcase
"""

import unittest
from unittest.mock import Mock

from iconservice.iconscore.icon_score_result import TransactionResult
from iconservice.iconscore.icon_score_result import IconBlockResult
from iconservice.iconscore.icon_score_result import Serializer
from iconservice.iconscore.icon_score_result import JsonSerializer
from iconservice.base.block import Block


class TestIconBlockResult(unittest.TestCase):
    def setUp(self):
        self._mock_serializer = Mock(spec=Serializer)
        self._block_result = IconBlockResult(self._mock_serializer)

    def tearDown(self):
        self._block_result = None
        self._mock_serializer = None

    def test_append(self):
        self._block_result.append(Mock(spec=TransactionResult))
        assert len(self._block_result) == 1

    def test_serialize(self):
        self._block_result.serialize()
        self._mock_serializer.serialize.assert_called_once()


class TestJsonSerializer(unittest.TestCase):
    SAMPLE_SERIALIZED_RESULT = b'[{"tx_hash": "0x0000000000000000000000000000000000000000000000000000000000000000", "block_height": 0, "to": "hx0000000000000000000000000000000000000000", "score_address": null, "step_used": 0, "status": 1}, {"tx_hash": "0x1111111111111111111111111111111111111111111111111111111111111111", "block_height": 0, "to": null, "score_address": "cx1111111111111111111111111111111111111111", "step_used": 0, "status": 1}, {"tx_hash": "0x2222222222222222222222222222222222222222222222222222222222222222", "block_height": 0, "to": "cx1111111111111111111111111111111111111111", "score_address": null, "step_used": 0, "status": 0}]'

    def setUp(self):
        self._json_serializer = JsonSerializer()

    def tearDown(self):
        self._json_serializer = None

    def test_serialize(self):
        eoa_address = f'hx{"0" * 40}'
        ca_address = f'cx{"1" * 40}'
        zero_block = Block(0, f'0x{"0" * 64}', 1)

        transaction_results = []

        # EOA to EOA
        # {
        #     "txHash": "0x0000000000000000000000000000000000000000000000000000000000000000",
        #     "blockHeight": 0,
        #     "to": "hx0000000000000000000000000000000000000000",
        #     "contractAddress": null,
        #     "stepUsed": 0,
        #     "status": 1
        # }
        transaction_results.append(TransactionResult(
            f'0x{"0" * 64}', zero_block, eoa_address, TransactionResult.SUCCESS,
            None, 0))

        # Install Score
        # {
        #     "txHash": "0x1111111111111111111111111111111111111111111111111111111111111111",
        #     "blockHeight": 0,
        #     "to": null,
        #     "contractAddress": "cx1111111111111111111111111111111111111111",
        #     "stepUsed": 0,
        #     "status": 1
        # }
        transaction_results.append(TransactionResult(
            f'0x{"1" * 64}', zero_block, None, TransactionResult.SUCCESS,
            ca_address, 0))

        # EOA to CA
        # {
        #     "txHash": "0x2222222222222222222222222222222222222222222222222222222222222222",
        #     "blockHeight": 0,
        #     "to": "cx1111111111111111111111111111111111111111",
        #     "contractAddress": null,
        #     "stepUsed": 0,
        #     "status": 0
        # }
        transaction_results.append(TransactionResult(
            f'0x{"2" * 64}', zero_block, ca_address, TransactionResult.FAILURE,
            None, 0))

        serialized = self._json_serializer.serialize(transaction_results)

        # The result string should be
        # [{"tx_hash": "0x0000000000000000000000000000000000000000000000000000000000000000", "block_height": 0, "to": "hx0000000000000000000000000000000000000000", "score_address": null, "step_used": 0, "status": 1}, {"tx_hash": "0x1111111111111111111111111111111111111111111111111111111111111111", "block_height": 0, "to": null, "score_address": "cx1111111111111111111111111111111111111111", "step_used": 0, "status": 1}, {"tx_hash": "0x2222222222222222222222222222222222222222222222222222222222222222", "block_height": 0, "to": "cx1111111111111111111111111111111111111111", "score_address": null, "step_used": 0, "status": 0}]
        assert serialized == TestJsonSerializer.SAMPLE_SERIALIZED_RESULT
