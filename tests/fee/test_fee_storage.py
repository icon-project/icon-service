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

from shutil import rmtree
from unittest import TestCase, main

from iconservice.base.address import AddressPrefix
from iconservice.database.batch import BlockBatch, TransactionBatch
from iconservice.database.db import ContextDatabase
from iconservice.fee.deposit import Deposit
from iconservice.fee.fee_storage import FeeStorage
from iconservice.fee.score_deposit_info import ScoreDepositInfo
from iconservice.iconscore.icon_score_context import IconScoreContextType, IconScoreContext
from tests import create_address, create_tx_hash


class TestFeeStorage(TestCase):

    def setUp(self):
        self.db_name = 'fee.db'
        self.address = create_address(AddressPrefix.EOA)
        db = ContextDatabase.from_path(self.db_name)
        self.assertIsNotNone(db)

        self.storage = FeeStorage(db)

        context = IconScoreContext(IconScoreContextType.DIRECT)
        context.tx_batch = TransactionBatch()
        context.block_batch = BlockBatch()
        self.context = context

    def tearDown(self):
        context = self.context
        self.storage.close(context)
        rmtree(self.db_name)

    def test_get_put_delete_score_fee(self):
        context = self.context
        score_address = create_address(AddressPrefix.CONTRACT)

        score_deposit_info = ScoreDepositInfo()
        score_deposit_info.head_id = create_tx_hash()
        score_deposit_info.tail_id = create_tx_hash()
        score_deposit_info.available_head_id_of_deposit = create_tx_hash()
        score_deposit_info.available_head_id_of_virtual_step = create_tx_hash()
        self.storage.put_score_deposit_info(context, score_address, score_deposit_info)

        score_deposit_info_2 = self.storage.get_score_deposit_info(context, score_address)
        self.assertEqual(score_deposit_info, score_deposit_info_2)

        self.storage.delete_score_deposit_info(context, score_address)
        score_deposit_info_2 = self.storage.get_score_deposit_info(context, score_address)
        self.assertIsNone(score_deposit_info_2)

    def test_get_put_delete_score_fee_with_none_type(self):
        context = self.context
        score_address = create_address(AddressPrefix.CONTRACT)

        score_deposit_info = ScoreDepositInfo()
        self.storage.put_score_deposit_info(context, score_address, score_deposit_info)

        score_deposit_info_2 = self.storage.get_score_deposit_info(context, score_address)
        self.assertEqual(score_deposit_info, score_deposit_info_2)

        self.storage.delete_score_deposit_info(context, score_address)
        score_deposit_info_2 = self.storage.get_score_deposit_info(context, score_address)
        self.assertIsNone(score_deposit_info_2)

    def test_get_put_delete_deposit(self):
        context = self.context

        deposit = Deposit()
        deposit.id = create_tx_hash()
        deposit.score_address = create_address(AddressPrefix.CONTRACT)
        deposit.sender = create_address(AddressPrefix.EOA)
        deposit.deposit_amount = 10000
        deposit.deposit_used = 10000
        deposit.created = 10
        deposit.expires = 1000000
        deposit.virtual_step_issued = 100000000000
        deposit.virtual_step_used = 200000000000
        deposit.prev_id = create_tx_hash()
        deposit.next_id = create_tx_hash()
        deposit.version = 2
        self.storage.put_deposit(context, deposit.id, deposit)

        deposit2 = self.storage.get_deposit(context, deposit.id)
        self.assertEqual(deposit, deposit2)
        self.assertEqual(deposit.id, deposit2.id)

        self.storage.delete_deposit(context, deposit.id)
        deposit2 = self.storage.get_deposit(context, deposit.id)
        self.assertIsNone(deposit2)

    def test_get_put_delete_deposit_with_none_type(self):
        context = self.context

        deposit = Deposit()
        deposit.id = create_tx_hash()
        deposit.score_address = create_address(AddressPrefix.CONTRACT)
        deposit.sender = create_address(AddressPrefix.EOA)
        deposit.deposit_amount = 10000
        deposit.deposit_used = 10000
        deposit.created = 10
        deposit.expires = 1000000
        deposit.virtual_step_issued = 100000000000
        deposit.virtual_step_used = 200000000000
        deposit.version = 1
        self.storage.put_deposit(context, deposit.id, deposit)

        deposit2 = self.storage.get_deposit(context, deposit.id)
        self.assertEqual(deposit, deposit2)
        self.assertEqual(deposit.id, deposit2.id)

        self.storage.delete_deposit(context, deposit.id)
        deposit2 = self.storage.get_deposit(context, deposit.id)
        self.assertIsNone(deposit2)


if __name__ == '__main__':
    main()
