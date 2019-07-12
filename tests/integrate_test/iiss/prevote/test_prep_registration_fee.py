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

from iconservice.base.type_converter_templates import ConstantKeys
from iconservice.icon_constant import REV_IISS, PREP_MAIN_PREPS, ICX_IN_LOOP
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


class TestIntegratePrepRegstration(TestIISSBase):
    def test_preps(self):
        self.update_governance()

        # set Revision REV_IISS
        tx: dict = self.create_set_revision_tx(REV_IISS)
        prev_block, tx_results = self._make_and_req_block([tx])
        self.assertEqual(int(True), tx_results[0].status)
        self._write_precommit_state(prev_block)

        expected_burned_amount = 2_000 * ICX_IN_LOOP
        expected_total_supply: int = self.get_total_supply()

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

        for i in range(PREP_MAIN_PREPS):
            icx_amount_before_reg: int = self.get_balance(self._addr_array[i])
            tx: dict = self.create_register_prep_tx(self._addr_array[i],
                                                    public_key=f"0x{self.public_key_array[i].hex()}",
                                                    value=2000 * ICX_IN_LOOP)
            prev_block, tx_results = self._make_and_req_block([tx])
            self._write_precommit_state(prev_block)
            self.assertEqual(int(True), tx_results[0].status)

            expected_total_supply -= expected_burned_amount
            step_price = tx_results[0].step_price * tx_results[0].step_used
            self.assertEqual(expected_total_supply, self.get_total_supply())
            self.assertEqual(icx_amount_before_reg - expected_burned_amount - step_price,
                             self.get_balance(self._addr_array[i]))
