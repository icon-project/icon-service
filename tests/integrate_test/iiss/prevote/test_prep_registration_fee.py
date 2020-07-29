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

from iconservice import SYSTEM_SCORE_ADDRESS
from iconservice.icon_constant import Revision, PREP_MAIN_PREPS, ICX_IN_LOOP, ConfigKey, PREP_MAIN_AND_SUB_PREPS
from tests.integrate_test.iiss.test_iiss_base import TestIISSBase
from tests.integrate_test.test_integrate_base import TOTAL_SUPPLY

if TYPE_CHECKING:
    from iconservice.iconscore.icon_score_result import TransactionResult


class TestIntegratePrepRegistration(TestIISSBase):

    def setUp(self):
        super().setUp()
        self.update_governance()

        # set Revision REV_IISS
        self.set_revision(Revision.IISS.value)

        # distribute icx for register
        self.distribute_icx(accounts=self._accounts[:PREP_MAIN_PREPS],
                            init_balance=3000 * ICX_IN_LOOP)

    def _init_decentralized(self):
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
        self.set_revision(Revision.DECENTRALIZATION.value)

        self.make_blocks_to_end_calculation()

    def test_register_prep_with_invalid_icx_value(self):
        # failure case: If not input value when calling 'registerPRep' method, should not be registered
        self.register_prep(from_=self._accounts[0],
                           value=0,
                           expected_status=False)

        # failure case: If input invalid value (i.e. insufficient or excess ICX value)
        # when calling 'registerPRep' method, should not be registered
        insufficient_value = 1000 * ICX_IN_LOOP
        self.register_prep(from_=self._accounts[0],
                           value=insufficient_value,
                           expected_status=False)

        excess_value = 2500 * ICX_IN_LOOP
        self.register_prep(from_=self._accounts[0],
                           value=excess_value,
                           expected_status=False)

    def test_register_prep_burn_event_log_should_be_fixed_after_revision_9(self):
        preps: list = self.create_eoa_accounts(3)
        self.distribute_icx(accounts=preps,
                            init_balance=3000 * ICX_IN_LOOP)
        config_value = self._config[ConfigKey.PREP_REGISTRATION_FEE]

        # TEST: When revision is before 'DECENTRALIZATION', burn signature should not have type format
        prep = preps[0]

        reg_tx_result: 'TransactionResult' = self.register_prep(from_=prep, value=config_value)[0]
        actual_burn_signature = reg_tx_result.event_logs[0].indexed[0]

        self.assertEqual("ICXBurned", actual_burn_signature)

        # TEST: When revision is between 'DECENTRALIZATION' and 'FIX_BURN_EVENT_SIGNATURE',
        # burn signature should not have type format
        self._init_decentralized()
        prep = preps[1]

        reg_tx_result: 'TransactionResult' = self.register_prep(from_=prep, value=config_value)[1]
        actual_burn_signature = reg_tx_result.event_logs[0].indexed[0]

        self.assertEqual("ICXBurned", actual_burn_signature)

        # TEST: After 'FIX_BURN_EVENT_SIGNATURE' revision is accepted, burn signature should have type format
        self.set_revision(Revision.FIX_BURN_EVENT_SIGNATURE.value)
        prep = preps[2]

        reg_tx_result: 'TransactionResult' = self.register_prep(from_=prep, value=config_value)[1]
        actual_burn_signature = reg_tx_result.event_logs[0].indexed[0]

        self.assertEqual("ICXBurned(int)", actual_burn_signature)

    def test_register_prep_burn_signature(self):
        # success case: If input 2000 ICX as value when calling 'registerPRep' method, should be registered successfully
        expected_burned_amount = 2_000 * ICX_IN_LOOP
        expected_total_supply: int = self.get_total_supply()

        for i in range(PREP_MAIN_PREPS):
            icx_amount_before_reg: int = self.get_balance(self._accounts[i])
            tx_results: List['TransactionResult'] = self.register_prep(from_=self._accounts[i],
                                                                       value=self._config[
                                                                           ConfigKey.PREP_REGISTRATION_FEE])

            expected_total_supply -= expected_burned_amount
            step_price = tx_results[0].step_price * tx_results[0].step_used
            self.assertEqual(expected_total_supply, self.get_total_supply())
            self.assertEqual(icx_amount_before_reg - expected_burned_amount - step_price,
                             self.get_balance(self._accounts[i]))

        self.assertEqual(expected_total_supply, self.get_total_supply())

    def test_set_value_when_prep_related_set_method(self):
        # failure case: except registerPRep, value can not be set when calling prep related setting method
        arbitrary_value = 10
        # register prep
        self.register_prep(from_=self._accounts[0],
                           value=self._config[
                               ConfigKey.PREP_REGISTRATION_FEE])

        # unregisterPRep
        tx: dict = self.create_score_call_tx(from_=self._accounts[0],
                                             to_=SYSTEM_SCORE_ADDRESS,
                                             func_name="unregisterPRep",
                                             params={},
                                             value=arbitrary_value)
        self.process_confirm_block_tx([tx],
                                      expected_status=False)

        # setPRep
        tx: dict = self.create_score_call_tx(from_=self._accounts[0],
                                             to_=SYSTEM_SCORE_ADDRESS,
                                             func_name="setPRep",
                                             params={"name": f"new{str(self._accounts[0].address)}"},
                                             value=arbitrary_value)
        self.process_confirm_block_tx([tx],
                                      expected_status=False)

        # setGovernanceVariables
        arbitrary_irep = 10
        tx: dict = self.create_score_call_tx(from_=self._accounts[0],
                                             to_=SYSTEM_SCORE_ADDRESS,
                                             func_name="setGovernanceVariables",
                                             params={"irep": hex(arbitrary_irep)},
                                             value=arbitrary_value)
        self.process_confirm_block_tx([tx],
                                      expected_status=False)
