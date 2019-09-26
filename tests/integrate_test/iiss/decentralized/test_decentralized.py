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

from iconservice.icon_constant import REVISION, \
    PREP_MAIN_PREPS, ICX_IN_LOOP, ConfigKey, IISS_MIN_IREP, IISS_INITIAL_IREP, PREP_MAIN_AND_SUB_PREPS
from tests.integrate_test.iiss.test_iiss_base import TestIISSBase
from tests.integrate_test.test_integrate_base import TOTAL_SUPPLY


class TestIISSDecentralized(TestIISSBase):
    def _make_init_config(self) -> dict:
        config: dict = super()._make_init_config()
        config[ConfigKey.PREP_REGISTRATION_FEE] = 0
        return config

    def test_decentralized1(self):
        # decentralized
        self.update_governance()

        # set Revision REV_IISS
        self.set_revision(REVISION.IISS.value)

        total_supply = TOTAL_SUPPLY * ICX_IN_LOOP
        # Minimum_delegate_amount is 0.02 * total_supply
        # In this test delegate 0.03*total_supply because `Issue transaction` exists since REV_IISS
        minimum_delegate_amount_for_decentralization: int = total_supply * 2 // 1000 + 1
        init_balance: int = minimum_delegate_amount_for_decentralization * 2

        # distribute icx PREP_MAIN_PREPS ~ PREP_MAIN_PREPS + PREP_MAIN_PREPS - 1
        self.distribute_icx(accounts=self._accounts[PREP_MAIN_PREPS:PREP_MAIN_AND_SUB_PREPS],
                            init_balance=init_balance)

        # stake PREP_MAIN_PREPS ~ PREP_MAIN_PREPS + PREP_MAIN_PREPS - 1
        stake_amount: int = minimum_delegate_amount_for_decentralization
        tx_list: list = []
        for i in range(PREP_MAIN_PREPS):
            tx: dict = self.create_set_stake_tx(from_=self._accounts[PREP_MAIN_PREPS + i],
                                                value=stake_amount)
            tx_list.append(tx)
        self.process_confirm_block_tx(tx_list)

        # distribute icx for register PREP_MAIN_PREPS ~ PREP_MAIN_PREPS + PREP_MAIN_PREPS - 1
        self.distribute_icx(accounts=self._accounts[:PREP_MAIN_PREPS],
                            init_balance=3000 * ICX_IN_LOOP)

        # register PRep
        tx_list: list = []
        for account in self._accounts[:PREP_MAIN_PREPS]:
            tx: dict = self.create_register_prep_tx(from_=account)
            tx_list.append(tx)
        self.process_confirm_block_tx(tx_list)

        # delegate to PRep
        tx_list: list = []
        for i in range(PREP_MAIN_PREPS):
            tx: dict = self.create_set_delegation_tx(from_=self._accounts[PREP_MAIN_PREPS + i],
                                                     origin_delegations=[
                                                         (
                                                             self._accounts[i],
                                                             minimum_delegate_amount_for_decentralization
                                                         )
                                                     ])
            tx_list.append(tx)
        self.process_confirm_block_tx(tx_list)

        # get main prep
        response: dict = self.get_main_prep_list()
        expected_response: dict = {
            "preps": [],
            "totalDelegated": 0
        }
        self.assertEqual(expected_response, response)

        # set Revision REV_IISS (decentralization)
        self.set_revision(REVISION.DECENTRALIZATION.value)

        self.make_blocks_to_end_calculation()

        # get main prep
        response: dict = self.get_main_prep_list()
        expected_preps: list = []
        expected_total_delegated: int = 0
        for account in self._accounts[:PREP_MAIN_PREPS]:
            expected_preps.append({
                'address': account.address,
                'delegated': minimum_delegate_amount_for_decentralization
            })
            expected_total_delegated += minimum_delegate_amount_for_decentralization
        expected_response: dict = {
            "preps": expected_preps,
            "totalDelegated": expected_total_delegated
        }
        self.assertEqual(expected_response, response)

    def test_block_sync(self):
        self.update_governance()

        # set Revision REV_IISS
        self.set_revision(REVISION.IISS.value)

        for i in range(10):
            end_block: int = self.make_blocks_to_end_calculation()
            self.make_blocks(end_block + 1)
            response: dict = self.get_iiss_info()
            self.assertNotEqual(end_block, response['nextCalculation'])

        self.init_decentralized()
        for i in range(10):
            end_block: int = self.make_blocks_to_end_calculation()
            self.make_blocks(end_block + 1)
            response: dict = self.get_iiss_info()
            self.assertNotEqual(end_block, response['nextCalculation'])
            self.assertNotEqual(end_block, response["nextPRepTerm"])
            self.assertEqual(response['nextCalculation'], response["nextPRepTerm"])

    def test_estimate_step(self):
        self.init_decentralized()

        prep_id: int = PREP_MAIN_PREPS + 1
        balance: int = 3000 * ICX_IN_LOOP
        tx = self.create_transfer_icx_tx(from_=self._admin,
                                         to_=self._accounts[prep_id],
                                         value=balance)
        self.process_confirm_block_tx([tx])

        # set stake
        tx: dict = self.create_set_stake_tx(from_=self._accounts[prep_id],
                                            value=0)
        self.estimate_step(tx)

        # set delegation
        tx: dict = self.create_set_delegation_tx(from_=self._accounts[prep_id],
                                                 origin_delegations=[(self._accounts[prep_id], 0)])
        self.estimate_step(tx)

        # claim iscore
        tx: dict = self.create_claim_tx(from_=self._accounts[prep_id])
        self.estimate_step(tx)

        # register prep
        tx: dict = self.create_register_prep_tx(from_=self._accounts[prep_id])
        self.estimate_step(tx)

        # real register prep
        self.register_prep(from_=self._accounts[prep_id])

        # set prep
        tx: dict = self.create_set_prep_tx(from_=self._accounts[prep_id],
                                           set_data={"name": f"new{str(self._accounts[prep_id])}"})
        self.estimate_step(tx)

        self.make_blocks_to_end_calculation()

        # set governance variable
        tx: dict = self.create_set_governance_variables(from_=self._accounts[prep_id],
                                                        irep=IISS_MIN_IREP)
        self.estimate_step(tx)

        # unregister prep
        tx: dict = self.create_unregister_prep_tx(self._accounts[prep_id])
        self.estimate_step(tx)

    def test_irep_each_revision(self):
        # decentralized
        self.update_governance()

        # set Revision REV_IISS
        self.set_revision(REVISION.IISS.value)

        expected_irep_when_rev_iiss = 0
        response: dict = self.get_iiss_info()
        self.assertEqual(expected_irep_when_rev_iiss, response['variable']['irep'])

        total_supply = TOTAL_SUPPLY * ICX_IN_LOOP
        # Minimum_delegate_amount is 0.02 * total_supply
        # In this test delegate 0.03*total_supply because `Issue transaction` exists since REV_IISS
        minimum_delegate_amount_for_decentralization: int = total_supply * 2 // 1000 + 1
        init_balance: int = minimum_delegate_amount_for_decentralization * 10

        # distribute icx PREP_MAIN_PREPS ~ PREP_MAIN_PREPS + PREP_MAIN_PREPS - 1
        tx_list: list = []
        for i in range(PREP_MAIN_PREPS):
            tx: dict = self.create_transfer_icx_tx(from_=self._admin,
                                                   to_=self._accounts[PREP_MAIN_PREPS + i],
                                                   value=init_balance)
            tx_list.append(tx)
        self.process_confirm_block_tx(tx_list)

        # stake PREP_MAIN_PREPS ~ PREP_MAIN_PREPS + PREP_MAIN_PREPS - 1
        stake_amount: int = minimum_delegate_amount_for_decentralization
        tx_list: list = []
        for i in range(PREP_MAIN_PREPS):
            tx: dict = self.create_set_stake_tx(from_=self._accounts[PREP_MAIN_PREPS + i],
                                                value=stake_amount)
            tx_list.append(tx)
        self.process_confirm_block_tx(tx_list)

        # distribute icx for register PREP_MAIN_PREPS ~ PREP_MAIN_PREPS + PREP_MAIN_PREPS - 1
        tx_list: list = []
        for i in range(PREP_MAIN_PREPS):
            tx: dict = self.create_transfer_icx_tx(from_=self._admin,
                                                   to_=self._accounts[i],
                                                   value=3000 * ICX_IN_LOOP)
            tx_list.append(tx)
        self.process_confirm_block_tx(tx_list)

        # register PRep
        tx_list: list = []
        for i, account in enumerate(self._accounts[:PREP_MAIN_PREPS]):
            tx: dict = self.create_register_prep_tx(from_=account)
            tx_list.append(tx)
        self.process_confirm_block_tx(tx_list)

        # irep of each prep should be 50,000 ICX when revision IISS_REV
        expected_inital_irep_of_prep = IISS_INITIAL_IREP
        for account in self._accounts[:PREP_MAIN_PREPS]:
            response = self.get_prep(from_=account)
            self.assertEqual(expected_inital_irep_of_prep, response['irep'])

        # delegate to PRep
        tx_list: list = []
        for i in range(PREP_MAIN_PREPS):
            tx: dict = self.create_set_delegation_tx(from_=self._accounts[PREP_MAIN_PREPS + i],
                                                     origin_delegations=[
                                                         (
                                                             self._accounts[i],
                                                             minimum_delegate_amount_for_decentralization
                                                         )
                                                     ])
            tx_list.append(tx)
        self.process_confirm_block_tx(tx_list)

        # set Revision REV_IISS (decentralization)
        self.set_revision(REVISION.DECENTRALIZATION.value)

        self.make_blocks_to_end_calculation()

        # after decentralization, irep should be 50,000
        expected_irep_when_decentralized = IISS_INITIAL_IREP
        response: dict = self.get_iiss_info()
        self.assertEqual(expected_irep_when_decentralized, response['variable']['irep'])
