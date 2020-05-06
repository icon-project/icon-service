#!/usr/bin/env python
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

import unittest

from iconservice.base.exception import ExceptionCode
from iconservice.base.address import AddressPrefix
from iconservice.base.block import Block
from iconservice.base.transaction import Transaction
from iconservice.iconscore.icon_score_result import TransactionResult
from tests import create_block_hash, create_tx_hash, create_address


class TestTransactionResult(unittest.TestCase):
    def setUp(self):
        block_hash = create_block_hash()
        tx_hash = create_tx_hash()
        tx_index = 0
        to = create_address(AddressPrefix.EOA)

        tx = Transaction(tx_hash, tx_index)

        block = Block(
            block_height=0,
            block_hash=block_hash,
            timestamp=0x1234567890,
            prev_hash=None,
            cumulative_fee=0,
        )

        tx_result = TransactionResult(tx=tx, block=block, to=to)

        tx_result.event_logs = []

        tx_result.failure = TransactionResult.Failure(
            code=ExceptionCode.SYSTEM_ERROR, message=str("Server error")
        )

        self.tx_result = tx_result

    def tearDown(self):
        pass

    def test_to_dict(self):
        tx_result = self.tx_result
        d = tx_result.to_dict()
        self.assertTrue(isinstance(d, dict))
        self.assertTrue(isinstance(tx_result.failure, TransactionResult.Failure))

        # If status is SUCCESS,
        # dict created by tx_result.to_dict() should not contain failure.
        tx_result.status = TransactionResult.SUCCESS
        tx_result.failure = TransactionResult.Failure(
            code=ExceptionCode.INVALID_PARAMETER, message="Invalid params"
        )

        d = tx_result.to_dict()
        self.assertFalse("failure" in d)

        tx_result.status = TransactionResult.FAILURE
        d = tx_result.to_dict()
        self.assertTrue("failure" in d)

        print(d)
        print(hex(tx_result.failure.code))
