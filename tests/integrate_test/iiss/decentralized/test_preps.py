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

from iconservice.base.type_converter_templates import ConstantKeys
from iconservice.icon_constant import ICX_IN_LOOP, PREP_MAIN_PREPS, IISS_INITIAL_IREP, ConfigKey, \
    PREP_MAIN_AND_SUB_PREPS
from iconservice.icon_constant import PRepStatus, PRepGrade
from tests.integrate_test.iiss.test_iiss_base import TestIISSBase

if TYPE_CHECKING:
    from iconservice.iconscore.icon_score_result import TransactionResult


class TestPreps(TestIISSBase):
    def _make_init_config(self) -> dict:
        config: dict = super()._make_init_config()
        config[ConfigKey.PREP_REGISTRATION_FEE] = 0
        return config

    def setUp(self):
        super().setUp()
        self.init_decentralized()

    def test_prep_rotate(self):
        """
        Scenario
        0. decentralized (All P-Reps have none delegations)
        1. unregisters the first main prep
        2. delegates 10000 loop to the last prep
        3. check main preps sorted
        :return:
        """
        self.distribute_icx(accounts=self._accounts[:PREP_MAIN_AND_SUB_PREPS],
                            init_balance=10000 * ICX_IN_LOOP)

        # un-register first main prep
        self.unregister_prep(from_=self._accounts[0])

        response: dict = self.get_prep(self._accounts[0])
        self.assertEqual(PRepStatus.UNREGISTERED.value, response['status'])

        self.distribute_icx(accounts=self._accounts[PREP_MAIN_PREPS: PREP_MAIN_PREPS + 1],
                            init_balance=20000)

        self.set_stake(from_=self._accounts[PREP_MAIN_PREPS],
                       value=10000)

        # register user[PREP_MAIN_PREPS]
        index: int = PREP_MAIN_PREPS
        self.register_prep(from_=self._accounts[index])

        # delegate to PRep
        delegation_amount: int = 10000
        self.set_delegation(from_=self._accounts[index],
                            origin_delegations=[
                                (
                                    self._accounts[index],
                                    delegation_amount
                                )
                            ])

        prep_from_get_prep: dict = self.get_prep(self._accounts[index])

        # get prep list
        response: dict = self.get_prep_list(1, 1)
        self.assertEqual(1, response["startRanking"])
        self.assertEqual(delegation_amount, response["totalDelegated"])
        self.assertIsInstance(response["totalStake"], int)
        preps: list = response["preps"]
        prep: dict = preps[0]
        self.assertEqual(1, len(preps))
        self.assertIsInstance(preps, list)
        self.assertEqual(self._accounts[index].address, prep["address"])
        self.assertEqual(str(self._accounts[index]), prep["name"])
        self.assertEqual(delegation_amount, prep["delegated"])
        self.assertIsInstance(PRepGrade(prep["grade"]), PRepGrade)
        for key in ("name", "country", "city", "delegated", "grade", "totalBlocks", "validatedBlocks"):
            self.assertEqual(prep_from_get_prep[key], prep[key])

        # make blocks
        self.make_blocks_to_end_calculation()

        # get main prep list
        expected_preps: list = []
        for i in range(1, PREP_MAIN_PREPS):
            expected_preps.append({
                "address": self._accounts[i].address,
                "delegated": 0
            })
        expected_preps.insert(0, {"address": self._accounts[PREP_MAIN_PREPS].address,
                                  "delegated": delegation_amount})

        response: dict = self.get_main_prep_list()
        expected_response: dict = \
            {
                "preps": expected_preps,
                "totalDelegated": delegation_amount
            }
        self.assertEqual(expected_response, response)

    def test_low_productivity(self):

        # get totalBlocks in main prep
        response: dict = self.get_prep(self._accounts[0])
        total_blocks: int = response['totalBlocks']

        # make blocks with prev_block_generator and prev_block_validators
        block_count: int = 20
        self.make_blocks(
            to=self._block_height + block_count,
            prev_block_generator=self._accounts[0].address,
            prev_block_validators=[self._accounts[1].address,
                                   self._accounts[2].address]
        )

        for i in range(3):
            response: dict = self.get_prep(self._accounts[i])
            self.assertEqual(total_blocks + block_count, response["totalBlocks"])
            self.assertEqual(block_count, response["validatedBlocks"])

        response: dict = self.get_prep(self._accounts[3])
        self.assertEqual(total_blocks + block_count, response["totalBlocks"])
        self.assertEqual(0, response["validatedBlocks"])

    def test_set_governance_variables1(self):

        self.distribute_icx(accounts=self._accounts[:1],
                            init_balance=10000 * ICX_IN_LOOP)

        origin_irep: int = IISS_INITIAL_IREP
        tx: dict = self.create_set_governance_variables(from_=self._accounts[0],
                                                        irep=origin_irep)
        self.process_confirm_block_tx([tx])

        response: dict = self.get_prep(self._accounts[0])
        expected_irep: int = origin_irep
        expected_update_block_height: int = self._block_height
        self.assertEqual(expected_irep, response['irep'])
        self.assertEqual(expected_update_block_height, response['irepUpdateBlockHeight'])

        self.make_blocks_to_end_calculation()

        irep: int = origin_irep * 12 // 10
        tx: dict = self.create_set_governance_variables(self._accounts[0], irep)
        self.process_confirm_block_tx([tx])

        response: dict = self.get_prep(self._accounts[0])
        expected_irep: int = irep
        expected_update_block_height: int = self._block_height
        self.assertEqual(expected_irep, response['irep'])
        self.assertEqual(expected_update_block_height, response['irepUpdateBlockHeight'])

    def test_set_governance_variables2(self):
        self.distribute_icx(accounts=self._accounts[:1],
                            init_balance=10000 * ICX_IN_LOOP)

        origin_irep: int = IISS_INITIAL_IREP
        tx: dict = self.create_set_governance_variables(self._accounts[0], origin_irep)
        self.process_confirm_block_tx([tx])

        response: dict = self.get_prep(self._accounts[0])
        expected_irep: int = origin_irep
        expected_update_block_height: int = self._block_height
        self.assertEqual(expected_irep, response['irep'])
        self.assertEqual(expected_update_block_height, response['irepUpdateBlockHeight'])

        # term validate
        irep: int = origin_irep
        tx: dict = self.create_set_governance_variables(self._accounts[0], irep)
        prev_block, hash_list = self.make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        tx_results: List['TransactionResult'] = self.get_tx_results(hash_list)
        self.assertEqual(int(True), tx_results[0].status)
        self.assertEqual(int(False), tx_results[1].status)

        self.make_blocks_to_end_calculation()

        # 20% below
        irep: int = origin_irep * 8 - 1 // 10
        tx: dict = self.create_set_governance_variables(self._accounts[0], irep)
        prev_block, hash_list = self.make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        tx_results: List['TransactionResult'] = self.get_tx_results(hash_list)
        self.assertEqual(int(True), tx_results[0].status)
        self.assertEqual(int(False), tx_results[1].status)

        # 20 above
        irep: int = origin_irep * 12 + 1 // 10
        tx: dict = self.create_set_governance_variables(self._accounts[0], irep)
        prev_block, tx_results = self.make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        tx_results: List['TransactionResult'] = self.get_tx_results(hash_list)
        self.assertEqual(int(True), tx_results[0].status)
        self.assertEqual(int(False), tx_results[1].status)

    def test_set_governance_variables3(self):
        self.distribute_icx(accounts=self._accounts[:1],
                            init_balance=10000 * ICX_IN_LOOP)

        origin_irep: int = IISS_INITIAL_IREP
        tx: dict = self.create_set_governance_variables(from_=self._accounts[0],
                                                        irep=origin_irep)
        self.process_confirm_block_tx([tx])

        response: dict = self.get_prep(self._accounts[0])
        expected_irep: int = origin_irep
        expected_update_block_height: int = self._block_height
        self.assertEqual(expected_irep, response['irep'])
        self.assertEqual(expected_update_block_height, response['irepUpdateBlockHeight'])

        irep: int = origin_irep

        possible_maximum_raise_irep_count: int = 6
        for i in range(possible_maximum_raise_irep_count):
            self.make_blocks_to_end_calculation()

            irep: int = irep * 12 // 10
            tx: dict = self.create_set_governance_variables(from_=self._accounts[0],
                                                            irep=irep)
            self.process_confirm_block_tx([tx])

        # max totalsupply limitation
        self.make_blocks_to_end_calculation()
        irep: int = irep * 12 // 10
        tx: dict = self.create_set_governance_variables(from_=self._accounts[0],
                                                        irep=irep)
        prev_block, hash_list = self.make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        tx_results: List['TransactionResult'] = self.get_tx_results(hash_list)
        self.assertEqual(int(True), tx_results[0].status)
        self.assertEqual(int(False), tx_results[1].status)

    def test_weighted_average_of_irep(self):
        self.distribute_icx(accounts=self._accounts[:2] + self._accounts[PREP_MAIN_PREPS:PREP_MAIN_PREPS + 2],
                            init_balance=1 * ICX_IN_LOOP)

        tx_list = []
        for account in self._accounts[PREP_MAIN_PREPS:PREP_MAIN_PREPS + 2]:
            tx = self.create_set_stake_tx(from_=account,
                                          value=3)
            tx_list.append(tx)
        self.process_confirm_block_tx(tx_list)

        delegation1: int = 1
        tx1: dict = self.create_set_delegation_tx(from_=self._accounts[PREP_MAIN_PREPS],
                                                  origin_delegations=[
                                                      (
                                                          self._accounts[0],
                                                          delegation1
                                                      )
                                                  ])
        delegation2: int = 3
        tx2: dict = self.create_set_delegation_tx(from_=self._accounts[PREP_MAIN_PREPS + 1],
                                                  origin_delegations=[
                                                      (
                                                          self._accounts[1],
                                                          delegation2
                                                      )
                                                  ])
        self.process_confirm_block_tx([tx1, tx2])

        irep1: int = IISS_INITIAL_IREP * 12 // 10
        tx1: dict = self.create_set_governance_variables(self._accounts[0], irep1)
        irep2: int = IISS_INITIAL_IREP * 8 // 10
        tx2: dict = self.create_set_governance_variables(self._accounts[1], irep2)
        self.process_confirm_block_tx([tx1, tx2])

        self.make_blocks_to_end_calculation()

        response: dict = self.get_iiss_info()
        expected_sum: int = IISS_INITIAL_IREP * 12 // 10 * delegation1 + IISS_INITIAL_IREP * 8 // 10 * delegation2
        expected_sum_delegation: int = delegation1 + delegation2
        expected_avg_irep: int = expected_sum // expected_sum_delegation
        self.assertEqual(expected_avg_irep, response['variable']['irep'])

    def test_sync_end_block_height_of_calc_and_term(self):
        response: dict = self.get_iiss_info()
        self.assertEqual(response['nextCalculation'], response['nextPRepTerm'])

    def test_register_prep_apply_terms_irep(self):
        self.distribute_icx(accounts=self._accounts[:2] + self._accounts[PREP_MAIN_PREPS:PREP_MAIN_PREPS + 2],
                            init_balance=1 * ICX_IN_LOOP)

        tx_list = []
        for account in self._accounts[PREP_MAIN_PREPS:PREP_MAIN_PREPS + 2]:
            tx = self.create_set_stake_tx(from_=account,
                                          value=3)
            tx_list.append(tx)
        self.process_confirm_block_tx(tx_list)

        delegation1: int = 1
        tx1: dict = self.create_set_delegation_tx(from_=self._accounts[PREP_MAIN_PREPS],
                                                  origin_delegations=[
                                                      (
                                                          self._accounts[0],
                                                          delegation1
                                                      )
                                                  ])
        delegation2: int = 3
        tx2: dict = self.create_set_delegation_tx(from_=self._accounts[PREP_MAIN_PREPS + 1],
                                                  origin_delegations=[
                                                      (
                                                          self._accounts[1],
                                                          delegation2
                                                      )
                                                  ])
        self.process_confirm_block_tx([tx1, tx2])

        irep1: int = IISS_INITIAL_IREP * 12 // 10
        tx1: dict = self.create_set_governance_variables(from_=self._accounts[0],
                                                         irep=irep1)
        irep2: int = IISS_INITIAL_IREP * 8 // 10
        tx2: dict = self.create_set_governance_variables(from_=self._accounts[1],
                                                         irep=irep2)
        self.process_confirm_block_tx([tx1, tx2])

        self.make_blocks_to_end_calculation()

        response: dict = self.get_iiss_info()
        expected_sum: int = IISS_INITIAL_IREP * 12 // 10 * delegation1 + IISS_INITIAL_IREP * 8 // 10 * delegation2
        expected_sum_delegation: int = delegation1 + delegation2
        expected_avg_irep: int = expected_sum // expected_sum_delegation
        self.assertEqual(expected_avg_irep, response['variable']['irep'])

        # register new user
        self.register_prep(from_=self._accounts[PREP_MAIN_PREPS + 1])

        expected_block_height: int = self._block_height

        response: dict = self.get_prep(self._accounts[PREP_MAIN_PREPS + 1])
        self.assertEqual(expected_avg_irep, response['irep'])
        self.assertEqual(expected_block_height, response['irepUpdateBlockHeight'])

    def test_get_prep_term(self):
        bottom_preps = self.create_eoa_accounts(10)
        accounts = self._accounts + bottom_preps
        term_info: dict = self.get_prep_term()
        preps = term_info['preps']
        required_fields = ["blockHeight", 'sequence', 'startBlockHeight',
                           'endBlockHeight', 'totalSupply', 'totalDelegated', 'irep']
        for field in required_fields:
            self.assertIn(field, term_info)

        for i, account in enumerate(accounts[:PREP_MAIN_PREPS]):
            data: dict = self.create_register_prep_params(account)
            prep = preps[i]
            self.assertEqual(prep[ConstantKeys.NAME], data[ConstantKeys.NAME])
            self.assertEqual(prep[ConstantKeys.COUNTRY], data[ConstantKeys.COUNTRY])
            self.assertEqual(prep[ConstantKeys.CITY], data[ConstantKeys.CITY])
            self.assertEqual(prep["grade"], PRepGrade.MAIN.value)
            self.assertEqual(prep[ConstantKeys.ADDRESS], account.address)
            self.assertEqual(prep[ConstantKeys.P2P_ENDPOINT], data[ConstantKeys.P2P_ENDPOINT])

        # distribute icx for register
        self.distribute_icx(accounts=accounts[PREP_MAIN_PREPS:PREP_MAIN_AND_SUB_PREPS],
                            init_balance=3000 * ICX_IN_LOOP)
        # register PReps
        tx_list: list = []
        for account in accounts[PREP_MAIN_PREPS:PREP_MAIN_AND_SUB_PREPS]:
            tx: dict = self.create_register_prep_tx(from_=account)
            tx_list.append(tx)
        self.process_confirm_block_tx(tx_list)

        self.make_blocks_to_end_calculation()

        term_info: dict = self.get_prep_term()
        preps = term_info['preps']

        self.assertEqual(len(preps), PREP_MAIN_AND_SUB_PREPS)
        for i, account in enumerate(accounts[:PREP_MAIN_AND_SUB_PREPS]):
            data: dict = self.create_register_prep_params(account)
            prep = preps[i]
            self.assertEqual(prep[ConstantKeys.NAME], data[ConstantKeys.NAME])
            self.assertEqual(prep[ConstantKeys.COUNTRY], data[ConstantKeys.COUNTRY])
            self.assertEqual(prep[ConstantKeys.CITY], data[ConstantKeys.CITY])
            self.assertIn(prep["grade"], (PRepGrade.MAIN.value, PRepGrade.SUB.value))
            self.assertEqual(prep[ConstantKeys.ADDRESS], account.address)
            self.assertEqual(prep[ConstantKeys.P2P_ENDPOINT], data[ConstantKeys.P2P_ENDPOINT])
