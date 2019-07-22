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

from iconservice.icon_constant import REV_DECENTRALIZATION, REV_IISS, \
    PREP_MAIN_PREPS, ICX_IN_LOOP, ConfigKey, IISS_MIN_IREP
from tests.integrate_test.iiss.test_iiss_base import TestIISSBase
from tests.integrate_test.test_integrate_base import TOTAL_SUPPLY


class TestIISSDecentralized(TestIISSBase):
    def _make_init_config(self) -> dict:
        config: dict = super()._make_init_config()
        config[ConfigKey.PREP_REGISTRATION_FEE] = 0
        return config

    def test_decentralized1(self):
        self.update_governance()

        # set Revision REV_IISS
        tx: dict = self.create_set_revision_tx(REV_IISS)
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)

        main_preps = self._addr_array[:PREP_MAIN_PREPS]

        total_supply = TOTAL_SUPPLY * ICX_IN_LOOP
        # Minimum_delegate_amount is 0.02 * total_supply
        # In this test delegate 0.02*total_supply + 1 because `Issue transaction` exists since REV_IISS
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

        # distribute icx for register PREP_MAIN_PREPS ~ PREP_MAIN_PREPS + PREP_MAIN_PREPS - 1
        tx_list: list = []
        for i in range(PREP_MAIN_PREPS):
            tx: dict = self._make_icx_send_tx(self._genesis,
                                              self._addr_array[i],
                                              3000 * ICX_IN_LOOP)
            tx_list.append(tx)
        prev_block, tx_results = self._make_and_req_block(tx_list)
        for tx_result in tx_results:
            self.assertEqual(int(True), tx_result.status)
        self._write_precommit_state(prev_block)

        # register PRep
        tx_list: list = []
        for i, address in enumerate(main_preps):
            tx: dict = self.create_register_prep_tx(address, public_key=f"0x{self.public_key_array[i].hex()}")
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

    def test_estimate_step(self):
        self.init_decentralized()

        prep_id: int = PREP_MAIN_PREPS + 1
        balance: int = 3000 * ICX_IN_LOOP
        tx = self._make_icx_send_tx(self._genesis, self._addr_array[prep_id], balance)
        prev_block, tx_results = self._make_and_req_block([tx])
        self.assertEqual(int(True), tx_results[0].status)
        self._write_precommit_state(prev_block)

        # set stake
        tx: dict = self.create_set_stake_tx(self._addr_array[prep_id], 0)
        self.estimate_step(tx)

        # set delegation
        tx: dict = self.create_set_delegation_tx(self._addr_array[prep_id], [(self._addr_array[prep_id], 0)])
        self.estimate_step(tx)

        # claim iscore
        tx: dict = self.create_claim_tx(self._addr_array[prep_id])
        self.estimate_step(tx)

        # register prep
        tx: dict = self.create_register_prep_tx(self._addr_array[prep_id],
                                                public_key=f"0x{self.public_key_array[prep_id].hex()}")
        self.estimate_step(tx)

        # real register prep
        tx: dict = self.create_register_prep_tx(self._addr_array[prep_id],
                                                public_key=f"0x{self.public_key_array[prep_id].hex()}")
        prev_block, tx_results = self._make_and_req_block([tx])
        self.assertEqual(int(True), tx_results[0].status)
        self._write_precommit_state(prev_block)

        # set prep
        tx: dict = self.create_set_prep_tx(self._addr_array[prep_id],
                                           {"name": f"new{str(self._addr_array[prep_id])}"})
        self.estimate_step(tx)

        self.make_blocks_to_end_calculation()

        # set governance variable
        tx: dict = self.create_set_governance_variables(self._addr_array[prep_id], IISS_MIN_IREP)
        self.estimate_step(tx)

        # unregister prep
        tx: dict = self.create_unregister_prep_tx(self._addr_array[prep_id])
        self.estimate_step(tx)
