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
from iconservice import ZERO_SCORE_ADDRESS
from iconservice.base.type_converter_templates import ConstantKeys
from iconservice.icon_constant import REV_IISS, PREP_MAIN_PREPS, ICX_IN_LOOP, ConfigKey
from tests.integrate_test.iiss.test_iiss_base import TestIISSBase

name = "prep"

prep_register_data = {
    ConstantKeys.NAME: name,
    ConstantKeys.EMAIL: f"{name}@example.com",
    ConstantKeys.WEBSITE: f"https://{name}.example.com",
    ConstantKeys.DETAILS: f"https://{name}.example.com/details",
    ConstantKeys.P2P_ENDPOINT: f"{name}.example.com:7100",
    ConstantKeys.PUBLIC_KEY: "0x12"
}


class TestIntegratePrepRegistration(TestIISSBase):

    def setUp(self):
        super().setUp()
        self.update_governance()

        # set Revision REV_IISS
        tx: dict = self.create_set_revision_tx(REV_IISS)
        prev_block, tx_results = self._make_and_req_block([tx])
        self.assertEqual(int(True), tx_results[0].status)
        self._write_precommit_state(prev_block)

        # distribute icx for register
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

    def test_register_prep_with_invalid_icx_value(self):
        # failure case: If not input value when calling 'registerPRep' method, should not be registered
        tx: dict = self.create_register_prep_tx(self._addr_array[0],
                                                public_key=f"0x{self.public_key_array[0].hex()}",
                                                value=0)
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        self.assertEqual(int(False), tx_results[0].status)

        # failure case: If input invalid value (i.e. insufficient or excess ICX value)
        # when calling 'registerPRep' method, should not be registered
        insufficient_value = 1000 * ICX_IN_LOOP
        tx: dict = self.create_register_prep_tx(self._addr_array[0],
                                                public_key=f"0x{self.public_key_array[0].hex()}",
                                                value=insufficient_value)
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        self.assertEqual(int(False), tx_results[0].status)

        excess_value = 2500 * ICX_IN_LOOP
        tx: dict = self.create_register_prep_tx(self._addr_array[0],
                                                public_key=f"0x{self.public_key_array[0].hex()}",
                                                value=excess_value)
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        self.assertEqual(int(False), tx_results[0].status)

    def test_register_prep(self):
        # success case: If input 2000 ICX as value when calling 'registerPRep' method, should be registered successfully
        expected_burned_amount = 2_000 * ICX_IN_LOOP
        expected_total_supply: int = self.get_total_supply()

        for i in range(PREP_MAIN_PREPS):
            icx_amount_before_reg: int = self.get_balance(self._addr_array[i])
            tx: dict = self.create_register_prep_tx(self._addr_array[i],
                                                    public_key=f"0x{self.public_key_array[i].hex()}",
                                                    value=self._config[ConfigKey.PREP_REGISTRATION_FEE])
            prev_block, tx_results = self._make_and_req_block([tx])
            self._write_precommit_state(prev_block)
            self.assertEqual(int(True), tx_results[0].status)

            expected_total_supply -= expected_burned_amount
            step_price = tx_results[0].step_price * tx_results[0].step_used
            self.assertEqual(expected_total_supply, self.get_total_supply())
            self.assertEqual(icx_amount_before_reg - expected_burned_amount - step_price,
                             self.get_balance(self._addr_array[i]))

    def test_set_value_when_prep_related_set_method(self):
        # failure case: except registerPRep, value can not be set when calling prep related setting method
        arbitrary_value = 10
        # register prep
        tx: dict = self.create_register_prep_tx(self._addr_array[0],
                                                public_key=f"0x{self.public_key_array[0].hex()}",
                                                value=self._config[ConfigKey.PREP_REGISTRATION_FEE])
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        self.assertEqual(int(True), tx_results[0].status)

        # unregisterPRep
        tx: dict = self._make_score_call_tx(self._addr_array[0],
                                            ZERO_SCORE_ADDRESS,
                                            'unregisterPRep', {}, value=arbitrary_value)
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        self.assertEqual(int(False), tx_results[0].status)

        # setPRep
        tx: dict = self._make_score_call_tx(self._addr_array[0],
                                            ZERO_SCORE_ADDRESS,
                                            'setPRep',
                                            {"name": f"new{str(self._addr_array[0])}"},
                                            value=arbitrary_value)
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        self.assertEqual(int(False), tx_results[0].status)

        # setGovernanceVariables
        arbitrary_irep = 10
        tx: dict = self._make_score_call_tx(addr_from=self._addr_array[0],
                                            addr_to=ZERO_SCORE_ADDRESS,
                                            method="setGovernanceVariables",
                                            params={"irep": hex(arbitrary_irep)},
                                            value=arbitrary_value)
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        self.assertEqual(int(False), tx_results[0].status)
