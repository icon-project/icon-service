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
from typing import TYPE_CHECKING

from iconservice.icon_constant import REV_IISS, PREP_MAIN_PREPS, ICX_IN_LOOP, REV_DECENTRALIZATION
from tests.integrate_test.iiss.test_iiss_base import TestIISSBase
from tests.integrate_test.test_integrate_base import TOTAL_SUPPLY

if TYPE_CHECKING:
    pass


class TestPreps(TestIISSBase):

    def setUp(self):
        super().setUp()

        # decentralized
        self.update_governance()

        # set Revision REV_IISS
        tx: dict = self.create_set_revision_tx(REV_IISS)
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)

        main_preps = self._addr_array[:PREP_MAIN_PREPS]

        total_supply = TOTAL_SUPPLY * ICX_IN_LOOP
        # Minimum_delegate_amount is 0.02 * total_supply
        # In this test delegate 0.03*total_supply because `Issue transaction` exists since REV_IISS
        minimum_delegate_amount_for_decentralization: int = total_supply * 2 // 1000 + 1
        init_balance: int = minimum_delegate_amount_for_decentralization * 10

        # distribute icx PREP_MAIN_PREPS ~ PREP_MAIN_PREPS + PREP_MAIN_PREPS - 1
        tx_list: list = []
        for i in range(PREP_MAIN_PREPS):
            tx: dict = self._make_icx_send_tx(self._genesis,
                                              self._addr_array[PREP_MAIN_PREPS + i],
                                              init_balance)
            tx_list.append(tx)
        prev_block, tx_results = self._make_and_req_block(tx_list)
        for tx_result in tx_results:
            self.assertEqual(int(True), tx_result.status)
        self._write_precommit_state(prev_block)

        # stake PREP_MAIN_PREPS ~ PREP_MAIN_PREPS + PREP_MAIN_PREPS - 1
        stake_amount: int = minimum_delegate_amount_for_decentralization
        tx_list: list = []
        for i in range(PREP_MAIN_PREPS):
            tx: dict = self.create_set_stake_tx(self._addr_array[PREP_MAIN_PREPS + i],
                                                stake_amount)
            tx_list.append(tx)
        prev_block, tx_results = self._make_and_req_block(tx_list)
        for tx_result in tx_results:
            self.assertEqual(int(True), tx_result.status)
        self._write_precommit_state(prev_block)

        # register PRep
        tx_list: list = []
        for address in main_preps:
            tx: dict = self.create_register_perp_tx(address)
            tx_list.append(tx)
        prev_block, tx_results = self._make_and_req_block(tx_list)
        for tx_result in tx_results:
            self.assertEqual(int(True), tx_result.status)
        self._write_precommit_state(prev_block)

        # delegate to PRep
        tx_list: list = []
        for i in range(PREP_MAIN_PREPS):
            tx: dict = self.create_set_delegation_tx(self._addr_array[PREP_MAIN_PREPS + i],
                                                     [
                                                         (
                                                             self._addr_array[i],
                                                             minimum_delegate_amount_for_decentralization
                                                         )
                                                     ])
            tx_list.append(tx)
        prev_block, tx_results = self._make_and_req_block(tx_list)
        for tx_result in tx_results:
            self.assertEqual(int(True), tx_result.status)
        self._write_precommit_state(prev_block)

        # get main prep
        response: dict = self.get_main_prep_list()
        expected_response: dict = {
            "preps": [],
            "totalDelegated": 0
        }
        self.assertEqual(expected_response, response)

        # set Revision REV_IISS (decentralization)
        tx: dict = self.create_set_revision_tx(REV_DECENTRALIZATION)
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)

        # get main prep
        response: dict = self.get_main_prep_list()
        expected_preps: list = []
        expected_total_delegated: int = 0
        for address in main_preps:
            expected_preps.append({
                'address': address,
                'delegated': minimum_delegate_amount_for_decentralization
            })
            expected_total_delegated += minimum_delegate_amount_for_decentralization
        expected_response: dict = {
            "preps": expected_preps,
            "totalDelegated": expected_total_delegated
        }
        self.assertEqual(expected_response, response)

        # delegate to PRep 0
        tx_list: list = []
        for i in range(PREP_MAIN_PREPS):
            tx: dict = self.create_set_delegation_tx(self._addr_array[PREP_MAIN_PREPS + i],
                                                     [
                                                         (
                                                             self._addr_array[i],
                                                             0
                                                         )
                                                     ])
            tx_list.append(tx)
        prev_block, tx_results = self._make_and_req_block(tx_list)
        for tx_result in tx_results:
            self.assertEqual(int(True), tx_result.status)
        self._write_precommit_state(prev_block)

        self.make_blocks_to_next_calculation()

        # get main prep
        response: dict = self.get_main_prep_list()
        expected_preps: list = []
        for address in main_preps:
            expected_preps.append({
                'address': address,
                'delegated': 0
            })
        expected_response: dict = {
            "preps": expected_preps,
            "totalDelegated": 0
        }
        self.assertEqual(expected_response, response)

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
        tx: dict = self.create_unregister_perp_tx(self._addr_array[0])
        prev_block, tx_results = self._make_and_req_block([tx])
        self.assertEqual(int(True), tx_results[0].status)
        self._write_precommit_state(prev_block)

        response: dict = self.get_prep(self._addr_array[0])
        self.assertEqual(1, response['status'])

        # register user[PREP_MAIN_PREPS]
        tx: dict = self.create_register_perp_tx(self._addr_array[PREP_MAIN_PREPS])
        prev_block, tx_results = self._make_and_req_block([tx])
        self.assertEqual(int(True), tx_results[0].status)
        self._write_precommit_state(prev_block)

        # delegate to PRep
        delegation_amount: int = 10000
        tx: dict = self.create_set_delegation_tx(self._addr_array[PREP_MAIN_PREPS],
                                                 [
                                                     (
                                                         self._addr_array[PREP_MAIN_PREPS],
                                                         delegation_amount
                                                     )
                                                 ])
        prev_block, tx_results = self._make_and_req_block([tx])
        self.assertEqual(int(True), tx_results[0].status)
        self._write_precommit_state(prev_block)

        # get prep list
        response: dict = self.get_prep_list(1, 1)
        expected_response: dict = \
            {
                "preps":
                    [{
                        "address": self._addr_array[PREP_MAIN_PREPS],
                        "delegated": delegation_amount
                    }],
                "startRanking": 1,
                "totalDelegated": delegation_amount
            }
        self.assertEqual(expected_response, response)

        # make blocks
        self.make_blocks_to_next_calculation()

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
        self.make_blocks_to_next_calculation()

        # get totalBlocks in main prep
        response: dict = self.get_prep(self._addr_array[0])
        total_blocks: int = response['stats']['totalBlocks']

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
            expected_response: dict = \
                {
                    "totalBlocks": total_blocks + block_count,
                    "validatedBlocks": block_count
                }
            self.assertEqual(expected_response, response["stats"])

        response: dict = self.get_prep(self._addr_array[3])
        expected_response: dict = \
            {
                "totalBlocks": total_blocks + block_count,
                "validatedBlocks": 0
            }
        self.assertEqual(expected_response, response["stats"])

    def test_sync_end_block_height_of_calc_and_term(self):
        # TODO We need to remake this logic
        pass

        # _PREPS_LEN = 200
        # _MAIN_PREPS_LEN = 22
        # _AMOUNT_DELEGATE = 10000
        # _MINIMUM_DELEGATE_AMOUNT = 10 ** 18
        # _TEST_BLOCK_HEIGHT = 30
        #
        # self._update_governance()
        # self._set_revision(REV_IISS)
        #
        # addr_array = [create_address() for _ in range(_PREPS_LEN)]
        #
        # total_supply = 800_460_000 * self._icx_factor
        #
        # # Minimum_delegate_amount is 0.02 * total_supply
        # # In this test delegate 0.03*total_supply because `Issue transaction` exists since REV_IISS
        # delegate_amount = total_supply * 3 // 1000
        #
        # # generate preps
        # self._decentralize(addr_array, delegate_amount)
        #
        # response = self._get_prep_list()
        # total_delegated: int = response['totalDelegated']
        # prep_list: list = response['preps']
        #
        # self.assertEqual(delegate_amount * 22, total_delegated)
        # self.assertEqual(_PREPS_LEN, len(prep_list))
        #
        # self._set_revision(REV_DECENTRALIZATION)
        #
        # # check if generating main preps
        # main_preps = self._get_main_perps()["preps"]
        # self.assertEqual(_MAIN_PREPS_LEN, len(main_preps))
        #
        # for i in range(_TEST_BLOCK_HEIGHT):
        #     try:
        #         prev_block, tx_results = self._make_and_req_block([])
        #         self._write_precommit_state(prev_block)
        #     except AssertionError:
        #         self.assertTrue(False)

    # TODO We need to fix after implement method "setGovernanceVariable

    # def test_weighted_average_of_irep(self):
    #     """
    #     Scenario
    #     1. generates preps and delegates more than minumum delegated amount to 22 preps
    #     2. sets revision to REV_DECENTRALIZATION and generates main and sub preps
    #     3. check wighted average of irep correct
    #     :return:
    #     """
    #
    #     _PREPS_LEN = 50
    #     context = IconScoreContext(IconScoreContextType.DIRECT)
    #     _AMOUNT_DELEGATE = int(get_minimum_delegate_for_bottom_prep(context=context) * 2)
    #
    #     self._update_governance()
    #     self._set_revision(REV_IISS)
    #     addresses: List['Address'] = [create_address() for _ in range(_PREPS_LEN)]
    #
    #     self._send_icx_in_loop(addresses[0], _AMOUNT_DELEGATE * 10)
    #     self._send_icx_in_loop(addresses[1], _AMOUNT_DELEGATE * 10)
    #
    #     buf_total_irep = 0
    #     # Generate P-Reps
    #     for i in range(_PREPS_LEN):
    #         if i < PREP_MAIN_PREPS:
    #             buf_total_irep += IISS_INITIAL_IREP
    #             reg_data: dict = create_register_prep_params(i)
    #             self._reg_prep(addresses[i], reg_data)
    #
    #         from_addr_for_stake: tuple = (self._admin, addresses[0], addresses[1])
    #
    #         idx_for_stake = 10
    #         for idx, from_addr in enumerate(from_addr_for_stake):
    #             # stake
    #             self._stake(from_addr, _AMOUNT_DELEGATE * 10)
    #             delegations = []
    #             for i in range(idx_for_stake - 10, idx_for_stake):
    #                 if i > 21:
    #                     break
    #                 delegations.append({
    #                     "address": str(addresses[i]),
    #                     "value": hex(_AMOUNT_DELEGATE)
    #                 })
    #             self._delegate(from_addr, delegations)
    #             idx_for_stake += 10
    #
    #         # set revision to REV_DECENTRALIZATION
    #         tx = self._make_score_call_tx(self._admin, GOVERNANCE_SCORE_ADDRESS, 'setRevision',
    #                                       {"code": hex(REV_DECENTRALIZATION), "name": f"1.1.{REV_DECENTRALIZATION}"})
    #         block, invoke_response, main_prep_as_dict = self._make_and_req_block_for_prep_test([tx])
    #         self.assertEqual((_AMOUNT_DELEGATE * buf_total_irep) // (_AMOUNT_DELEGATE * PREP_MAIN_PREPS),
    #                          main_prep_as_dict['irep'])

    # def test_prep_set_irep_in_term(self):
    #     _PREPS_LEN = 22
    #     self._update_governance()
    #     self._set_revision(REV_IISS)
    #
    #     addr_array = [create_address() for _ in range(_PREPS_LEN)]
    #
    #     total_supply = 800_460_000 * self._icx_factor
    #
    #     # Minimum_delegate_amount is 0.02 * total_supply
    #     # In this test delegate 0.03*total_supply because `Issue transaction` exists since REV_IISS
    #     delegate_amount = total_supply * 3 // 1000
    #
    #     # generate preps
    #     self._decentralize(addr_array, delegate_amount)
    #
    #     # set revision to REV_DECENTRALIZATION
    #     tx = self._make_score_call_tx(self._admin, GOVERNANCE_SCORE_ADDRESS, 'setRevision',
    #                                   {"code": hex(REV_DECENTRALIZATION), "name": f"1.1.{REV_DECENTRALIZATION}"})
    #     prev_block, tx_results, main_prep_as_dict = self._make_and_req_block_for_prep_test([tx])
    #     self.assertIsNotNone(main_prep_as_dict)
    #
    #     for i in range(2):
    #         prev_block, tx_results = self._make_and_req_block(
    #             [],
    #             prev_block_generator=addr_array[0],
    #             prev_block_validators=[addr_array[1], addr_array[2]])
    #         self._write_precommit_state(prev_block)
    #
    #     data: dict = create_register_prep_params(index=0)
    #
    #     expected_response: dict = data
    #     response: dict = self._get_prep(addr_array[0])
    #     register = response["registration"]
    #
    #     self.assertEqual(expected_response[ConstantKeys.NAME], register[ConstantKeys.NAME])
    #     self.assertEqual(expected_response[ConstantKeys.EMAIL], register[ConstantKeys.EMAIL])
    #     self.assertEqual(expected_response[ConstantKeys.WEBSITE], register[ConstantKeys.WEBSITE])
    #     self.assertEqual(expected_response[ConstantKeys.DETAILS], register[ConstantKeys.DETAILS])
    #     self.assertEqual(expected_response[ConstantKeys.P2P_END_POINT], register[ConstantKeys.P2P_END_POINT])
    #     self.assertEqual(expected_response[ConstantKeys.PUBLIC_KEY], register[ConstantKeys.PUBLIC_KEY])
    #     self.assertEqual(IISS_INITIAL_IREP, register[ConstantKeys.IREP])
    #
    #     irep_value = int(IISS_INITIAL_IREP * 12 // 10)
    #
    #     set_prep_data1: dict = {
    #         ConstantKeys.IREP: irep_value,
    #     }
    #     prev_block, tx_results = self._set_prep(addr_array[0], set_prep_data1)
    #     self.assertEqual(int(True), tx_results[0].status)
    #     self._write_precommit_state(prev_block)
    #
    #     response: dict = self._get_prep(addr_array[0])
    #     register = response["registration"]
    #     self.assertEqual(data[ConstantKeys.NAME], register[ConstantKeys.NAME])
    #     self.assertEqual(data[ConstantKeys.WEBSITE], register[ConstantKeys.WEBSITE])
    #     self.assertEqual(hex(set_prep_data1[ConstantKeys.IREP]), hex(register[ConstantKeys.IREP]))
    #
    #     irep_value2 = int(irep_value * 1.1)
    #
    #     set_prep_data2: dict = {
    #         ConstantKeys.IREP: hex(irep_value2),
    #     }
    #     tx = self._make_score_call_tx(addr_array[0],
    #                                   ZERO_SCORE_ADDRESS,
    #                                   'setPRep',
    #                                   set_prep_data2)
    #     prev_block, tx_results = self._make_and_req_block([tx])
    #     set_result = tx_results[0]
    #     self.assertEqual(set_result.status, 0)
    #     failure_message = set_result.failure.message
    #     self.assertEqual(failure_message, "irep can only be changed once during the term.")
    #
    #     response: dict = self._get_prep(addr_array[0])
    #     register = response["registration"]
    #     self.assertEqual(data[ConstantKeys.NAME], register[ConstantKeys.NAME])
    #     self.assertEqual(data[ConstantKeys.WEBSITE], register[ConstantKeys.WEBSITE])
    #     self.assertNotEqual(set_prep_data2[ConstantKeys.IREP], hex(register[ConstantKeys.IREP]))
    #
    # def test_prep_set_irep_in_term_case2(self):
    #     """Case when prep tries to set invalid irep(less than 0.8*prev_irep, greater than 1.2*prev_irep)
    #     after that prep tries to set same irep twice in term"""
    #     _PREPS_LEN = 22
    #     self._update_governance()
    #     self._set_revision(REV_IISS)
    #
    #     addr_array = [create_address() for _ in range(_PREPS_LEN)]
    #
    #     total_supply = 800_460_000 * self._icx_factor
    #
    #     # Minimum_delegate_amount is 0.02 * total_supply
    #     # In this test delegate 0.03*total_supply because `Issue transaction` exists since REV_IISS
    #     delegate_amount = total_supply * 3 // 1000
    #
    #     # generate preps
    #     self._decentralize(addr_array, delegate_amount)
    #
    #     # set revision to REV_DECENTRALIZATION
    #     tx = self._make_score_call_tx(self._admin, GOVERNANCE_SCORE_ADDRESS, 'setRevision',
    #                                   {"code": hex(REV_DECENTRALIZATION), "name": f"1.1.{REV_DECENTRALIZATION}"})
    #     prev_block, tx_results, main_prep_as_dict = self._make_and_req_block_for_prep_test([tx])
    #     self.assertIsNotNone(main_prep_as_dict)
    #
    #     for i in range(2):
    #         prev_block, tx_results = self._make_and_req_block(
    #             [],
    #             prev_block_generator=addr_array[0],
    #             prev_block_validators=[addr_array[1], addr_array[2]])
    #         self._write_precommit_state(prev_block)
    #
    #     data: dict = create_register_prep_params(index=0)
    #
    #     expected_response: dict = data
    #     response: dict = self._get_prep(addr_array[0])
    #     register = response["registration"]
    #
    #     self.assertEqual(expected_response[ConstantKeys.NAME], register[ConstantKeys.NAME])
    #     self.assertEqual(expected_response[ConstantKeys.EMAIL], register[ConstantKeys.EMAIL])
    #     self.assertEqual(expected_response[ConstantKeys.WEBSITE], register[ConstantKeys.WEBSITE])
    #     self.assertEqual(expected_response[ConstantKeys.DETAILS], register[ConstantKeys.DETAILS])
    #     self.assertEqual(expected_response[ConstantKeys.P2P_END_POINT], register[ConstantKeys.P2P_END_POINT])
    #     self.assertEqual(expected_response[ConstantKeys.PUBLIC_KEY], register[ConstantKeys.PUBLIC_KEY])
    #     self.assertEqual(IISS_INITIAL_IREP, register[ConstantKeys.IREP])
    #
    #     # irep < prev_irep * 0.8
    #     irep_value = int(IISS_INITIAL_IREP * 0.79)
    #
    #     set_prep_data1: dict = {
    #         ConstantKeys.IREP: irep_value,
    #     }
    #     prev_block, tx_results = self._set_prep(addr_array[0], set_prep_data1)
    #     self.assertEqual(int(False), tx_results[0].status)
    #     self._write_precommit_state(prev_block)
    #
    #     response: dict = self._get_prep(addr_array[0])
    #     register = response["registration"]
    #     self.assertEqual(data[ConstantKeys.NAME], register[ConstantKeys.NAME])
    #     self.assertEqual(data[ConstantKeys.WEBSITE], register[ConstantKeys.WEBSITE])
    #     self.assertEqual(hex(IISS_INITIAL_IREP), hex(register[ConstantKeys.IREP]))
    #
    #     # irep > prev_irep * 1.2
    #     irep_value = int(IISS_INITIAL_IREP * 1.21)
    #     set_prep_data2: dict = {
    #         ConstantKeys.IREP: irep_value,
    #     }
    #     prev_block, tx_results = self._set_prep(addr_array[0], set_prep_data2)
    #     self.assertEqual(int(False), tx_results[0].status)
    #     self._write_precommit_state(prev_block)
    #
    #     response: dict = self._get_prep(addr_array[0])
    #     register = response["registration"]
    #     self.assertEqual(data[ConstantKeys.NAME], register[ConstantKeys.NAME])
    #     self.assertEqual(data[ConstantKeys.WEBSITE], register[ConstantKeys.WEBSITE])
    #     self.assertEqual(hex(IISS_INITIAL_IREP), hex(register[ConstantKeys.IREP]))
    #
    #     # set same irep twice in term
    #     irep_value3 = int(IISS_INITIAL_IREP * 1.1)
    #     set_prep_data3: dict = {
    #         ConstantKeys.IREP: hex(irep_value3),
    #     }
    #     tx = self._make_score_call_tx(addr_array[0],
    #                                   ZERO_SCORE_ADDRESS,
    #                                   'setPRep',
    #                                   set_prep_data3)
    #     prev_block, tx_results = self._make_and_req_block([tx])
    #     self._write_precommit_state(prev_block)
    #     set_result = tx_results[0]
    #     self.assertEqual(set_result.status, 1)
    #
    #     response: dict = self._get_prep(addr_array[0])
    #     register = response["registration"]
    #     self.assertEqual(data[ConstantKeys.NAME], register[ConstantKeys.NAME])
    #     self.assertEqual(data[ConstantKeys.WEBSITE], register[ConstantKeys.WEBSITE])
    #     self.assertNotEqual(set_prep_data2[ConstantKeys.IREP], hex(register[ConstantKeys.IREP]))
    #
    #     tx = self._make_score_call_tx(addr_array[0],
    #                                   ZERO_SCORE_ADDRESS,
    #                                   'setPRep',
    #                                   set_prep_data3)
    #     prev_block, tx_results = self._make_and_req_block([tx])
    #     set_result = tx_results[0]
    #     self.assertEqual(set_result.status, 0)
    #     failure_message = set_result.failure.message
    #     self.assertEqual(failure_message, "irep can only be changed once during the term.")
    #
    #     response: dict = self._get_prep(addr_array[0])
    #     register = response["registration"]
    #     self.assertEqual(data[ConstantKeys.NAME], register[ConstantKeys.NAME])
    #     self.assertEqual(data[ConstantKeys.WEBSITE], register[ConstantKeys.WEBSITE])
