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

"""IconScoreEngine testcase
"""
from typing import TYPE_CHECKING, List
from unittest.mock import patch

from iconservice import ZERO_SCORE_ADDRESS, Address
from iconservice.icon_constant import ICX_IN_LOOP, PREP_MAIN_PREPS, IISS_INITIAL_IREP, ConfigKey, \
    PREP_PENALTY_SIGNATURE, BASE_TRANSACTION_INDEX, PREP_MAIN_AND_SUB_PREPS
from iconservice.icon_constant import PRepStatus, PRepGrade
from iconservice.iconscore.icon_score_event_log import EventLog
from tests.integrate_test.iiss.test_iiss_base import TestIISSBase
from tests.integrate_test.test_integrate_base import EOAAccount

if TYPE_CHECKING:
    from iconservice.iconscore.icon_score_result import TransactionResult


class TestPreps(TestIISSBase):
    def _make_init_config(self) -> dict:
        config: dict = super()._make_init_config()
        return config

    def setUp(self):
        super().setUp()
        self.init_decentralized()

    @patch('iconservice.prep.data.prep.PENALTY_GRACE_PERIOD', 40)
    @patch('iconservice.prep.data.prep.VALIDATION_PENALTY', 5)
    def test_prep_replace_in_term1(self):
        accounts: List['EOAAccount'] = self.create_eoa_accounts(PREP_MAIN_AND_SUB_PREPS)
        self.distribute_icx(accounts=accounts,
                            init_balance=3000 * ICX_IN_LOOP)

        # replace new PREPS
        tx_list = []
        for i in range(PREP_MAIN_PREPS):
            tx = self.create_register_prep_tx(from_=accounts[i])
            tx_list.append(tx)
            tx = self.create_set_stake_tx(from_=accounts[i + PREP_MAIN_PREPS],
                                          value=1)
            tx_list.append(tx)
            tx = self.create_set_delegation_tx(from_=accounts[i + PREP_MAIN_PREPS],
                                               origin_delegations=[
                                                   (
                                                       accounts[i],
                                                       1
                                                   )
                                               ])
            tx_list.append(tx)
        self.process_confirm_block_tx(tx_list)
        self.make_blocks_to_end_calculation()

        # check new PREPS to MAIN_PREPS
        response: dict = self.get_main_prep_list()
        expected_preps: list = []
        expected_total_delegated: int = 0
        for account in accounts[:PREP_MAIN_PREPS]:
            expected_preps.append({
                'address': account.address,
                'delegated': 1
            })
            expected_total_delegated += 1
        expected_response: dict = {
            "preps": expected_preps,
            "totalDelegated": expected_total_delegated
        }
        self.assertEqual(expected_response, response)

        # maintain
        block_count = 100
        for i in range(block_count):
            prev_block, hash_list = self.make_and_req_block(
                [],
                prev_block_generator=accounts[0].address,
                prev_block_validators=[account.address
                                       for account in accounts[1:PREP_MAIN_PREPS]])
            self._write_precommit_state(prev_block)
            tx_results: List['TransactionResult'] = self.get_tx_results(hash_list)
            for tx_result in tx_results:
                self.assertEqual(True, tx_result.status)

        # check new PREPS to MAIN_PREPS
        response: dict = self.get_main_prep_list()
        expected_preps: list = []
        expected_total_delegated: int = 0
        for account in accounts[:PREP_MAIN_PREPS]:
            expected_preps.append({
                'address': account.address,
                'delegated': 1
            })
            expected_total_delegated += 1
        expected_response: dict = {
            "preps": expected_preps,
            "totalDelegated": expected_total_delegated
        }
        self.assertEqual(expected_response, response)

        response: dict = self.get_prep(accounts[0])
        self.assertEqual(block_count, response["totalBlocks"])
        self.assertEqual(block_count, response["validatedBlocks"])

    @patch('iconservice.prep.data.prep.PENALTY_GRACE_PERIOD', 5)
    def test_prep_replace_in_term2(self):
        accounts: List['EOAAccount'] = self.create_eoa_accounts(PREP_MAIN_AND_SUB_PREPS)
        self.distribute_icx(accounts=accounts,
                            init_balance=3000 * ICX_IN_LOOP)

        # replace new PREPS
        tx_list = []
        for i in range(PREP_MAIN_PREPS):
            tx = self.create_register_prep_tx(from_=accounts[i])
            tx_list.append(tx)
            tx = self.create_register_prep_tx(from_=accounts[i + PREP_MAIN_PREPS])
            tx_list.append(tx)

            tx = self.create_set_stake_tx(from_=accounts[i],
                                          value=1)
            tx_list.append(tx)
            tx = self.create_set_stake_tx(from_=accounts[i + PREP_MAIN_PREPS],
                                          value=1)
            tx_list.append(tx)
            tx = self.create_set_delegation_tx(from_=accounts[i + PREP_MAIN_PREPS],
                                               origin_delegations=[
                                                   (
                                                       accounts[i],
                                                       1
                                                   )
                                               ])
            tx_list.append(tx)
        self.process_confirm_block_tx(tx_list)
        self.make_blocks_to_end_calculation()

        # maintain
        block_count = 100
        for i in range(block_count):
            prev_block, hash_list = self.make_and_req_block(
                [],
                prev_block_generator=accounts[0].address,
                prev_block_validators=[account.address
                                       for account in accounts[1:PREP_MAIN_PREPS]])
            self._write_precommit_state(prev_block)
            tx_results: List['TransactionResult'] = self.get_tx_results(hash_list)
            for tx_result in tx_results:
                self.assertEqual(True, tx_result.status)

        # check new PREPS to MAIN_PREPS
        response: dict = self.get_main_prep_list()
        expected_preps: list = []
        expected_total_delegated: int = 0
        for account in accounts[:PREP_MAIN_PREPS]:
            expected_preps.append({
                'address': account.address,
                'delegated': 1
            })
            expected_total_delegated += 1
        expected_response: dict = {
            "preps": expected_preps,
            "totalDelegated": expected_total_delegated
        }
        self.assertEqual(expected_response, response)

        response: dict = self.get_prep(accounts[0])
        self.assertEqual(block_count, response["totalBlocks"])
        self.assertEqual(block_count, response["validatedBlocks"])