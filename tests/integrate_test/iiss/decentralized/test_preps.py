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
from unittest.mock import patch

from iconservice import ZERO_SCORE_ADDRESS
from iconservice.icon_constant import ICX_IN_LOOP, PREP_MAIN_PREPS, IISS_INITIAL_IREP, ConfigKey, PREP_PENALTY_SIGNATURE
from iconservice.icon_constant import PRepStatus, PRepGrade
from iconservice.iconscore.icon_score_event_log import EventLog
from tests.integrate_test.iiss.test_iiss_base import TestIISSBase


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

        # un-register first main prep
        tx: dict = self.create_unregister_prep_tx(self._addr_array[0])
        prev_block, tx_results = self._make_and_req_block([tx])
        self.assertEqual(int(True), tx_results[0].status)
        self._write_precommit_state(prev_block)

        response: dict = self.get_prep(self._addr_array[0])
        self.assertEqual(PRepStatus.UNREGISTERED.value, response['status'])

        # register user[PREP_MAIN_PREPS]
        index: int = PREP_MAIN_PREPS
        tx: dict = self.create_register_prep_tx(self._addr_array[index],
                                                public_key=f"0x{self.public_key_array[index].hex()}")
        prev_block, tx_results = self._make_and_req_block([tx])
        self.assertEqual(int(True), tx_results[0].status)
        self._write_precommit_state(prev_block)

        # delegate to PRep
        delegation_amount: int = 10000
        tx: dict = self.create_set_delegation_tx(self._addr_array[index],
                                                 [
                                                     (
                                                         self._addr_array[index],
                                                         delegation_amount
                                                     )
                                                 ])
        prev_block, tx_results = self._make_and_req_block([tx])
        self.assertEqual(int(True), tx_results[0].status)
        self._write_precommit_state(prev_block)

        prep_from_get_prep: dict = self.get_prep(str(self._addr_array[index]))

        # get prep list
        response: dict = self.get_prep_list(1, 1)
        self.assertEqual(1, response["startRanking"])
        self.assertEqual(delegation_amount, response["totalDelegated"])
        self.assertIsInstance(response["totalStake"], int)
        preps: list = response["preps"]
        prep: dict = preps[0]
        self.assertEqual(1, len(preps))
        self.assertIsInstance(preps, list)
        self.assertEqual(self._addr_array[index], prep["address"])
        self.assertEqual(f"node{self._addr_array[index]}", prep["name"])
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
                "address": self._addr_array[i],
                "delegated": 0
            })
        expected_preps.insert(0, {"address": self._addr_array[PREP_MAIN_PREPS], "delegated": delegation_amount})

        response: dict = self.get_main_prep_list()
        expected_response: dict = \
            {
                "preps": expected_preps,
                "totalDelegated": delegation_amount
            }
        self.assertEqual(expected_response, response)

    def test_low_productivity(self):

        # get totalBlocks in main prep
        response: dict = self.get_prep(self._addr_array[0])
        total_blocks: int = response['totalBlocks']

        # make blocks with prev_block_generator and prev_block_validators
        block_count: int = 20
        for i in range(block_count):
            prev_block, tx_results = self._make_and_req_block(
                [],
                prev_block_generator=self._addr_array[0],
                prev_block_validators=[self._addr_array[1], self._addr_array[2]])
            self._write_precommit_state(prev_block)

        for i in range(3):
            response: dict = self.get_prep(self._addr_array[i])
            self.assertEqual(total_blocks + block_count, response["totalBlocks"])
            self.assertEqual(block_count, response["validatedBlocks"])

        response: dict = self.get_prep(self._addr_array[3])
        self.assertEqual(total_blocks + block_count, response["totalBlocks"])
        self.assertEqual(0, response["validatedBlocks"])

    @patch('iconservice.prep.data.prep.PENALTY_GRACE_PERIOD', 80)
    def test_low_productivity_penalty1(self):
        # get totalBlocks in main prep
        response: dict = self.get_prep(self._addr_array[0])
        total_blocks: int = response['totalBlocks']
        expected_prep_penalty_event_logs: list = []
        _MAXIMUM_COUNT_FOR_ISSUE_EVENT_LOG = 5
        _STEADY_PREPS_COUNT = 13
        _UNCOOPERATIVE_PREP_COUNT = PREP_MAIN_PREPS - _STEADY_PREPS_COUNT

        expected_penalty_event_log_data = [PRepStatus.PENALTY2.value, 0]
        expected_penalty_event_logs = [EventLog(ZERO_SCORE_ADDRESS,
                                                [PREP_PENALTY_SIGNATURE, prep],
                                                expected_penalty_event_log_data)
                                       for prep in self._addr_array[_STEADY_PREPS_COUNT:PREP_MAIN_PREPS]]
        initial_main_preps_info = self.get_main_prep_list()['preps']
        initial_main_preps = list(map(lambda prep_dict: prep_dict['address'], initial_main_preps_info))
        for prep in self._addr_array[:PREP_MAIN_PREPS]:
            self.assertIn(prep, initial_main_preps)

        block_count = 90
        tx_list = []
        for i in range(PREP_MAIN_PREPS, len(self._addr_array)):
            tx = self._make_icx_send_tx(self._genesis, self._addr_array[i], 3000 * ICX_IN_LOOP)
            tx_list.append(tx)
        prev_block, tx_results = self._make_and_req_block(tx_list)
        self._write_precommit_state(prev_block)

        tx_list = []
        for i in range(PREP_MAIN_PREPS, len(self._addr_array)):
            tx = self.create_register_prep_tx(self._addr_array[i],
                                              public_key=f"0x{self.public_key_array[i].hex()}")
            tx_list.append(tx)
        prev_block, tx_results = self._make_and_req_block(tx_list)
        self._write_precommit_state(prev_block)

        # make blocks with prev_block_generator and prev_block_validators
        for i in range(block_count):
            prev_block, tx_results = self._make_and_req_block(
                [],
                prev_block_generator=self._addr_array[0],
                prev_block_validators=self._addr_array[1:_STEADY_PREPS_COUNT])
            self._write_precommit_state(prev_block)
            if len(tx_results[0].event_logs) > _MAXIMUM_COUNT_FOR_ISSUE_EVENT_LOG:
                event_logs = tx_results[0].event_logs
                for event_log in event_logs:
                    if event_log.indexed[0] == PREP_PENALTY_SIGNATURE:
                        expected_prep_penalty_event_logs.append(event_log)

        # uncooperative preps got penalty on 90th block since PENALTY_GRACE_PERIOD is 80
        for i in range(_STEADY_PREPS_COUNT):
            response: dict = self.get_prep(self._addr_array[i])
            expected_response: dict = \
                {
                    "totalBlocks": total_blocks + block_count + 2,
                    "validatedBlocks": block_count
                }
            self.assertEqual(expected_response['totalBlocks'], response['totalBlocks'])
            self.assertEqual(expected_response['validatedBlocks'], response['validatedBlocks'])

        for i in range(_STEADY_PREPS_COUNT, PREP_MAIN_PREPS):
            response: dict = self.get_prep(self._addr_array[i])
            expected_response: dict = \
                {
                    "totalBlocks": block_count,
                    "validatedBlocks": 0
                }
            self.assertEqual(expected_response['totalBlocks'], response['totalBlocks'])
            self.assertEqual(expected_response['validatedBlocks'], response['validatedBlocks'])

        main_preps_info = self.get_main_prep_list()['preps']
        main_preps = list(map(lambda prep_dict: prep_dict['address'], main_preps_info))

        # prep0~12 are still prep
        for index, prep in enumerate(self._addr_array[:_STEADY_PREPS_COUNT]):
            self.assertEqual(prep, main_preps[index])

        # prep13~21 got penalty
        for prep in self._addr_array[_STEADY_PREPS_COUNT:PREP_MAIN_PREPS]:
            self.assertNotIn(prep, main_preps)

        # prep22~30 became new preps(14th prep ~ 22th prep)
        for index, prep in enumerate(self._addr_array[PREP_MAIN_PREPS:PREP_MAIN_PREPS + _UNCOOPERATIVE_PREP_COUNT]):
            self.assertEqual(prep, main_preps[index + PREP_MAIN_PREPS - _UNCOOPERATIVE_PREP_COUNT])

        for index, event_log in enumerate(expected_penalty_event_logs):
            self.assertEqual(event_log.indexed[0], expected_prep_penalty_event_logs[index].indexed[0])
            self.assertEqual(event_log.indexed[1], expected_prep_penalty_event_logs[index].indexed[1])
            self.assertEqual(event_log.data, expected_prep_penalty_event_logs[index].data)

    def test_set_governance_variables1(self):
        origin_irep: int = IISS_INITIAL_IREP
        tx: dict = self.create_set_governance_variables(self._addr_array[0], origin_irep)
        prev_block, tx_results = self._make_and_req_block([tx])
        for tx_result in tx_results:
            self.assertEqual(int(True), tx_result.status)
        self._write_precommit_state(prev_block)

        response: dict = self.get_prep(self._addr_array[0])
        expected_irep: int = origin_irep
        expected_update_block_height: int = self._block_height
        self.assertEqual(expected_irep, response['irep'])
        self.assertEqual(expected_update_block_height, response['irepUpdateBlockHeight'])

        self.make_blocks_to_end_calculation()

        irep: int = origin_irep * 12 // 10
        tx: dict = self.create_set_governance_variables(self._addr_array[0], irep)
        prev_block, tx_results = self._make_and_req_block([tx])
        for tx_result in tx_results:
            self.assertEqual(int(True), tx_result.status)
        self._write_precommit_state(prev_block)

        response: dict = self.get_prep(self._addr_array[0])
        expected_irep: int = irep
        expected_update_block_height: int = self._block_height
        self.assertEqual(expected_irep, response['irep'])
        self.assertEqual(expected_update_block_height, response['irepUpdateBlockHeight'])

    def test_set_governance_variables2(self):
        origin_irep: int = IISS_INITIAL_IREP
        tx: dict = self.create_set_governance_variables(self._addr_array[0], origin_irep)
        prev_block, tx_results = self._make_and_req_block([tx])
        for tx_result in tx_results:
            self.assertEqual(int(True), tx_result.status)
        self._write_precommit_state(prev_block)

        response: dict = self.get_prep(self._addr_array[0])
        expected_irep: int = origin_irep
        expected_update_block_height: int = self._block_height
        self.assertEqual(expected_irep, response['irep'])
        self.assertEqual(expected_update_block_height, response['irepUpdateBlockHeight'])

        # term validate
        irep: int = origin_irep
        tx: dict = self.create_set_governance_variables(self._addr_array[0], irep)
        prev_block, tx_results = self._make_and_req_block([tx])
        self.assertEqual(int(True), tx_results[0].status)
        self.assertEqual(int(False), tx_results[1].status)
        self._write_precommit_state(prev_block)

        self.make_blocks_to_end_calculation()

        # 20% below
        irep: int = origin_irep * 8 - 1 // 10
        tx: dict = self.create_set_governance_variables(self._addr_array[0], irep)
        prev_block, tx_results = self._make_and_req_block([tx])
        self.assertEqual(int(True), tx_results[0].status)
        self.assertEqual(int(False), tx_results[1].status)
        self._write_precommit_state(prev_block)

        # 20 above
        irep: int = origin_irep * 12 + 1 // 10
        tx: dict = self.create_set_governance_variables(self._addr_array[0], irep)
        prev_block, tx_results = self._make_and_req_block([tx])
        self.assertEqual(int(True), tx_results[0].status)
        self.assertEqual(int(False), tx_results[1].status)
        self._write_precommit_state(prev_block)

    def test_set_governance_variables3(self):
        origin_irep: int = IISS_INITIAL_IREP
        tx: dict = self.create_set_governance_variables(self._addr_array[0], origin_irep)
        prev_block, tx_results = self._make_and_req_block([tx])
        for tx_result in tx_results:
            self.assertEqual(int(True), tx_result.status)
        self._write_precommit_state(prev_block)

        response: dict = self.get_prep(self._addr_array[0])
        expected_irep: int = origin_irep
        expected_update_block_height: int = self._block_height
        self.assertEqual(expected_irep, response['irep'])
        self.assertEqual(expected_update_block_height, response['irepUpdateBlockHeight'])

        irep: int = origin_irep

        possible_maximum_raise_irep_count: int = 6
        for i in range(possible_maximum_raise_irep_count):
            self.make_blocks_to_end_calculation()

            irep: int = irep * 12 // 10
            tx: dict = self.create_set_governance_variables(self._addr_array[0], irep)
            prev_block, tx_results = self._make_and_req_block([tx])
            for tx_result in tx_results:
                self.assertEqual(int(True), tx_result.status)
            self._write_precommit_state(prev_block)

        # max totalsupply limitation
        self.make_blocks_to_end_calculation()
        irep: int = irep * 12 // 10
        tx: dict = self.create_set_governance_variables(self._addr_array[0], irep)
        prev_block, tx_results = self._make_and_req_block([tx])
        self.assertEqual(int(True), tx_results[0].status)
        self.assertEqual(int(False), tx_results[1].status)
        self._write_precommit_state(prev_block)

    def test_weighted_average_of_irep(self):

        delegation1: int = 1
        tx1: dict = self.create_set_delegation_tx(self._addr_array[PREP_MAIN_PREPS],
                                                 [
                                                     (
                                                         self._addr_array[0],
                                                         delegation1
                                                     )
                                                 ])
        delegation2: int = 3
        tx2: dict = self.create_set_delegation_tx(self._addr_array[PREP_MAIN_PREPS + 1],
                                                  [
                                                      (
                                                          self._addr_array[1],
                                                          delegation2
                                                      )
                                                  ])
        prev_block, tx_results = self._make_and_req_block([tx1, tx2])
        for tx_result in tx_results:
            self.assertEqual(int(True), tx_result.status)
        self._write_precommit_state(prev_block)

        irep1: int = IISS_INITIAL_IREP * 12 // 10
        tx1: dict = self.create_set_governance_variables(self._addr_array[0], irep1)
        irep2: int = IISS_INITIAL_IREP * 8 // 10
        tx2: dict = self.create_set_governance_variables(self._addr_array[1], irep2)
        prev_block, tx_results = self._make_and_req_block([tx1, tx2])
        for tx_result in tx_results:
            self.assertEqual(int(True), tx_result.status)
        self._write_precommit_state(prev_block)

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

        delegation1: int = 1
        tx1: dict = self.create_set_delegation_tx(self._addr_array[PREP_MAIN_PREPS],
                                                  [
                                                      (
                                                          self._addr_array[0],
                                                          delegation1
                                                      )
                                                  ])
        delegation2: int = 3
        tx2: dict = self.create_set_delegation_tx(self._addr_array[PREP_MAIN_PREPS + 1],
                                                  [
                                                      (
                                                          self._addr_array[1],
                                                          delegation2
                                                      )
                                                  ])
        prev_block, tx_results = self._make_and_req_block([tx1, tx2])
        for tx_result in tx_results:
            self.assertEqual(int(True), tx_result.status)
        self._write_precommit_state(prev_block)

        irep1: int = IISS_INITIAL_IREP * 12 // 10
        tx1: dict = self.create_set_governance_variables(self._addr_array[0], irep1)
        irep2: int = IISS_INITIAL_IREP * 8 // 10
        tx2: dict = self.create_set_governance_variables(self._addr_array[1], irep2)
        prev_block, tx_results = self._make_and_req_block([tx1, tx2])
        for tx_result in tx_results:
            self.assertEqual(int(True), tx_result.status)
        self._write_precommit_state(prev_block)

        self.make_blocks_to_end_calculation()

        response: dict = self.get_iiss_info()
        expected_sum: int = IISS_INITIAL_IREP * 12 // 10 * delegation1 + IISS_INITIAL_IREP * 8 // 10 * delegation2
        expected_sum_delegation: int = delegation1 + delegation2
        expected_avg_irep: int = expected_sum // expected_sum_delegation
        self.assertEqual(expected_avg_irep, response['variable']['irep'])

        # register new user
        tx: dict = self.create_register_prep_tx(self._addr_array[PREP_MAIN_PREPS + 1],
                                                public_key=f"0x{self.public_key_array[PREP_MAIN_PREPS + 1].hex()}")
        prev_block, tx_results = self._make_and_req_block([tx])
        self.assertEqual(int(True), tx_results[0].status)
        self._write_precommit_state(prev_block)

        expected_block_height: int = self._block_height

        response: dict = self.get_prep(self._addr_array[PREP_MAIN_PREPS + 1])
        self.assertEqual(expected_avg_irep, response['irep'])
        self.assertEqual(expected_block_height, response['irepUpdateBlockHeight'])
