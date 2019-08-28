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

from iconservice.icon_constant import ICX_IN_LOOP, PREP_MAIN_PREPS, PREP_MAIN_AND_SUB_PREPS, PREP_PENALTY_SIGNATURE
from iconservice.prep.data import PRep
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

    def test_prep_replace_in_term1(self):
        PRep._penalty_grace_period = 40
        """
        scenario 1
            when it starts new preps on new term, normal case, while 100 block.
        expected :
            all new preps have maintained until 100 block because it already passed GRACE_PERIOD
        """

        self.distribute_icx(accounts=self._accounts[:PREP_MAIN_PREPS],
                            init_balance=1 * ICX_IN_LOOP)

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

        tx_list: list = []
        # unregister prev_main_preps
        for account in self._accounts[:PREP_MAIN_PREPS]:
            tx: dict = self.create_unregister_prep_tx(from_=account)
            tx_list.append(tx)
        tx_results: ['TransactionResult'] = self.process_confirm_block_tx(tx_list=tx_list,
                                                                          prev_block_generator=accounts[0].address,
                                                                          prev_block_validators=[
                                                                              account.address
                                                                              for account in accounts[1:PREP_MAIN_PREPS]
                                                                          ])
        for tx_result in tx_results[1:]:
            self.assertEqual("PRepUnregistered(Address)", tx_result.event_logs[0].indexed[0])

        # maintain
        block_count = 39
        self.make_blocks(to=self._block_height + block_count,
                         prev_block_generator=accounts[0].address,
                         prev_block_validators=[
                             account.address
                             for account in accounts[1:PREP_MAIN_PREPS]
                         ])

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

        for i in range(PREP_MAIN_PREPS):
            response: dict = self.get_prep(accounts[i])
            self.assertEqual(block_count, response["totalBlocks"])
            self.assertEqual(block_count, response["validatedBlocks"])

    def test_prep_replace_in_term2(self):
        PRep._penalty_grace_period = 40
        """
        scenario 2
            when it starts new preps on new term, half count (MAIN_PREPS // 2) preps have done to validate block until GRACE_PERIOD.
        expected :
            half preps are normal case. but another half preps don't validate block(static values are all zero).
            so after GRACE_PERIOD will replace half preps.
        """

        self.distribute_icx(accounts=self._accounts[:PREP_MAIN_PREPS],
                            init_balance=1 * ICX_IN_LOOP)
        accounts: List['EOAAccount'] = self.create_eoa_accounts(PREP_MAIN_AND_SUB_PREPS)
        self.distribute_icx(accounts=accounts,
                            init_balance=3000 * ICX_IN_LOOP)

        # replace new PREPS
        half_prep_count: int = PREP_MAIN_PREPS // 2
        test_prep_count: int = PREP_MAIN_PREPS + half_prep_count
        tx_list = []
        for i in range(test_prep_count):
            tx = self.create_register_prep_tx(from_=accounts[i])
            tx_list.append(tx)
            tx = self.create_set_stake_tx(from_=accounts[i + test_prep_count],
                                          value=1)
            tx_list.append(tx)
            tx = self.create_set_delegation_tx(from_=accounts[i + test_prep_count],
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

        tx_list: list = []
        # unregister prev_main_preps
        for account in self._accounts[:PREP_MAIN_PREPS]:
            tx: dict = self.create_unregister_prep_tx(from_=account)
            tx_list.append(tx)
        tx_results: ['TransactionResult'] = self.process_confirm_block_tx(tx_list=tx_list,
                                                                          prev_block_generator=accounts[0].address,
                                                                          prev_block_validators=[
                                                                              account.address
                                                                              for account in accounts[1:half_prep_count]
                                                                          ])
        for tx_result in tx_results[1:]:
            self.assertEqual("PRepUnregistered(Address)", tx_result.event_logs[0].indexed[0])

        # maintain until GRACE_PERIOD
        block_count1 = 39
        self.make_blocks(to=self._block_height + block_count1,
                         prev_block_generator=accounts[0].address,
                         prev_block_validators=[
                             account.address
                             for account in accounts[1:half_prep_count]
                         ])

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

        for i in range(half_prep_count):
            response: dict = self.get_prep(accounts[i])
            self.assertEqual(block_count1, response["totalBlocks"])
            self.assertEqual(block_count1, response["validatedBlocks"])
        for i in range(half_prep_count, PREP_MAIN_PREPS):
            response: dict = self.get_prep(accounts[i])
            self.assertEqual(block_count1, response["totalBlocks"])
            self.assertEqual(0, response["validatedBlocks"])

        block_count2 = 10
        tx_results: List[List['TransactionResult']] = self.make_blocks(
            to=self._block_height + block_count2,
            prev_block_generator=accounts[0].address,
            prev_block_validators=
            [
                account.address
                for account in
                accounts[
                    1:half_prep_count
                ]
            ] +
            [
                account.address
                for account in
                accounts
                [
                    PREP_MAIN_PREPS: PREP_MAIN_PREPS + half_prep_count + 1]
                ]
        )

        for event_log in tx_results[0][0].event_logs[3:]:
            self.assertEqual(PREP_PENALTY_SIGNATURE, event_log.indexed[0])

        # check new PREPS to MAIN_PREPS
        response: dict = self.get_main_prep_list()

        expected_preps: list = []
        expected_total_delegated: int = 0

        for account in accounts[:half_prep_count]:
            expected_preps.append({
                'address': account.address,
                'delegated': 1
            })
            expected_total_delegated += 1
        for account in accounts[PREP_MAIN_PREPS:PREP_MAIN_PREPS + half_prep_count]:
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

        for i in range(half_prep_count):
            response: dict = self.get_prep(accounts[i])
            self.assertEqual(block_count1 + block_count2, response["totalBlocks"])
            self.assertEqual(block_count1 + block_count2, response["validatedBlocks"])

        for i in range(half_prep_count, PREP_MAIN_PREPS):
            response: dict = self.get_prep(accounts[i])
            self.assertEqual(block_count1 + 2, response["totalBlocks"])
            self.assertEqual(0, response["validatedBlocks"])

        for i in range(PREP_MAIN_PREPS, PREP_MAIN_PREPS + half_prep_count):
            response: dict = self.get_prep(accounts[i])
            self.assertEqual(block_count2 - 1 - 1, response["totalBlocks"])
            self.assertEqual(block_count2 - 1 - 1, response["validatedBlocks"])

    def test_prep_replace_in_term3(self):
        """
        scenario 3
            unregister prep half_prep_count on current preps
        """

        # get main prep
        response: dict = self.get_main_prep_list()
        expected_preps: list = []
        for account in self._accounts[:PREP_MAIN_PREPS]:
            expected_preps.append({
                'address': account.address,
                'delegated': 0
            })
        expected_response: dict = {
            "preps": expected_preps,
            "totalDelegated": 0
        }
        self.assertEqual(expected_response, response)

        self.distribute_icx(accounts=self._accounts[:PREP_MAIN_PREPS],
                            init_balance=1 * ICX_IN_LOOP)
        accounts: List['EOAAccount'] = self.create_eoa_accounts(PREP_MAIN_PREPS)
        self.distribute_icx(accounts=accounts,
                            init_balance=3000 * ICX_IN_LOOP)

        # replace new PREPS
        half_prep_count: int = PREP_MAIN_PREPS // 2
        tx_list = []
        for i in range(half_prep_count):
            tx = self.create_register_prep_tx(from_=accounts[i])
            tx_list.append(tx)
            tx = self.create_register_prep_tx(from_=accounts[i + half_prep_count])
            tx_list.append(tx)

            tx = self.create_set_stake_tx(from_=accounts[i],
                                          value=1)
            tx_list.append(tx)
            tx = self.create_set_stake_tx(from_=accounts[i + half_prep_count],
                                          value=1)
            tx_list.append(tx)
            tx = self.create_set_delegation_tx(from_=accounts[i + half_prep_count],
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
        block_count = 20
        self.make_blocks(to=self._block_height + block_count)

        # check new PREPS to MAIN_PREPS
        response: dict = self.get_main_prep_list()
        expected_preps: list = []
        expected_total_delegated: int = 0
        for account in accounts[:half_prep_count]:
            expected_preps.append({
                'address': account.address,
                'delegated': 1
            })
            expected_total_delegated += 1
        for account in self._accounts[:half_prep_count]:
            expected_preps.append({
                'address': account.address,
                'delegated': 0
            })
            expected_total_delegated += 0
        expected_response: dict = {
            "preps": expected_preps,
            "totalDelegated": expected_total_delegated
        }
        self.assertEqual(expected_response, response)

        for i in range(half_prep_count):
            response: dict = self.get_prep(accounts[i])
            self.assertEqual(block_count - 1, response["totalBlocks"])
            self.assertEqual(0, response["validatedBlocks"])

        count = 9
        for i in range(count):
            self.unregister_prep(accounts[i])

        # check new PREPS to MAIN_PREPS
        response: dict = self.get_main_prep_list()
        expected_preps: list = []
        expected_total_delegated: int = 0

        for account in self._accounts[half_prep_count:half_prep_count + count]:
            expected_preps.append({
                'address': account.address,
                'delegated': 0
            })
            expected_total_delegated += 0
        for account in accounts[count:half_prep_count]:
            expected_preps.append({
                'address': account.address,
                'delegated': 1
            })
            expected_total_delegated += 1
        for account in self._accounts[:half_prep_count]:
            expected_preps.append({
                'address': account.address,
                'delegated': 0
            })
            expected_total_delegated += 0
        expected_response: dict = {
            "preps": expected_preps,
            "totalDelegated": expected_total_delegated
        }
        self.assertEqual(expected_response, response)

        self.unregister_prep(accounts[9])

        # check new PREPS to MAIN_PREPS
        response: dict = self.get_main_prep_list()
        expected_preps: list = []
        expected_total_delegated: int = 0

        for account in accounts[half_prep_count - 1:half_prep_count]:
            expected_preps.append({
                'address': account.address,
                'delegated': 1
            })
            expected_total_delegated += 1
        for account in self._accounts[:PREP_MAIN_PREPS - 1]:
            expected_preps.append({
                'address': account.address,
                'delegated': 0
            })
            expected_total_delegated += 0
        expected_response: dict = {
            "preps": expected_preps,
            "totalDelegated": expected_total_delegated
        }
        self.assertEqual(expected_response, response)

    def test_prep_replace_in_term4(self):
        PRep._penalty_grace_period: int = 40
        PRep._max_unvalidated_sequence_blocks: int = 5

        """
        scenario 4
            when it starts new preps on new term, half count (MAIN_PREPS // 2) preps have done to validate block continuously.
        expected :
            half preps are normal case. but another half preps don't validate block(static values are all zero).
        """

        self.distribute_icx(accounts=self._accounts[:PREP_MAIN_PREPS],
                            init_balance=1 * ICX_IN_LOOP)
        accounts: List['EOAAccount'] = self.create_eoa_accounts(PREP_MAIN_AND_SUB_PREPS)
        self.distribute_icx(accounts=accounts,
                            init_balance=3000 * ICX_IN_LOOP)

        # replace new PREPS
        half_prep_count: int = PREP_MAIN_PREPS // 2
        test_prep_count: int = PREP_MAIN_PREPS + half_prep_count
        tx_list = []
        for i in range(test_prep_count):
            tx = self.create_register_prep_tx(from_=accounts[i])
            tx_list.append(tx)
            tx = self.create_set_stake_tx(from_=accounts[i + test_prep_count],
                                          value=1)
            tx_list.append(tx)
            tx = self.create_set_delegation_tx(from_=accounts[i + test_prep_count],
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

        tx_list: list = []
        # unregister prev_main_preps
        for account in self._accounts[:PREP_MAIN_PREPS]:
            tx: dict = self.create_unregister_prep_tx(from_=account)
            tx_list.append(tx)
        self.process_confirm_block_tx(tx_list=tx_list,
                                      prev_block_generator=accounts[0].address,
                                      prev_block_validators=[
                                          account.address
                                          for account in accounts[1:half_prep_count]
                                      ])

        # maintain until GRACE_PERIOD
        block_count1 = 100
        self.make_blocks(to=self._block_height + block_count1,
                         prev_block_generator=accounts[0].address,
                         prev_block_validators=[
                             account.address
                             for account in accounts[1:PREP_MAIN_PREPS]
                         ])

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

        for i in range(PREP_MAIN_PREPS):
            response: dict = self.get_prep(accounts[i])
            self.assertEqual(block_count1, response["totalBlocks"])
            self.assertEqual(block_count1, response["validatedBlocks"])

        block_count2 = 6
        self.make_blocks(to=self._block_height + block_count2,
                         prev_block_generator=accounts[0].address,
                         prev_block_validators=[
                             account.address
                             for account in accounts[1:half_prep_count]
                         ])

        # check new PREPS to MAIN_PREPS
        response: dict = self.get_main_prep_list()

        expected_preps: list = []
        expected_total_delegated: int = 0

        for account in accounts[:half_prep_count]:
            expected_preps.append({
                'address': account.address,
                'delegated': 1
            })
            expected_total_delegated += 1
        for account in accounts[PREP_MAIN_PREPS:PREP_MAIN_PREPS + half_prep_count]:
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

        block_count3 = 4
        self.make_blocks(to=self._block_height + block_count3,
                         prev_block_generator=accounts[0].address,
                         prev_block_validators=[
                             account.address
                             for account in accounts[1:half_prep_count]
                         ])

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

        for i in range(half_prep_count):
            response: dict = self.get_prep(accounts[i])
            self.assertEqual(block_count1 + block_count2 + block_count3, response["totalBlocks"])
            self.assertEqual(block_count1 + block_count2 + block_count3, response["validatedBlocks"])

        for i in range(half_prep_count, PREP_MAIN_PREPS):
            response: dict = self.get_prep(accounts[i])
            self.assertEqual(block_count1 + block_count2, response["totalBlocks"])
            self.assertEqual(block_count1, response["validatedBlocks"])

        for i in range(PREP_MAIN_PREPS, PREP_MAIN_PREPS + half_prep_count):
            response: dict = self.get_prep(accounts[i])
            self.assertEqual(block_count3, response["totalBlocks"])
            self.assertEqual(0, response["validatedBlocks"])

        block_count4 = 4
        self.make_blocks(to=self._block_height + block_count4,
                         prev_block_generator=accounts[0].address,
                         prev_block_validators=[
                             account.address
                             for account in accounts[1:PREP_MAIN_PREPS]
                         ])

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

        block_count4 = 5
        self.make_blocks(to=self._block_height + block_count4,
                         prev_block_generator=accounts[0].address,
                         prev_block_validators=[
                             account.address
                             for account in accounts[1:half_prep_count]
                         ])

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
