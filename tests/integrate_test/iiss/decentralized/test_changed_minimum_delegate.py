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
    PREP_MAIN_PREPS, ICX_IN_LOOP, ConfigKey, IISS_MIN_IREP, IISS_INITIAL_IREP
from tests.integrate_test.iiss.test_iiss_base import TestIISSBase
from tests.integrate_test.test_integrate_base import TOTAL_SUPPLY


class TestChangedMinimumDelegate(TestIISSBase):
    def _make_init_config(self) -> dict:
        config: dict = super()._make_init_config()
        config[ConfigKey.MIN_DELEGATION_PERCENT_FOR_DECENTRALIZE] = {
            ConfigKey.NUMERATOR: 0,
            ConfigKey.DENOMINATOR: 0
        }
        return config

    def test_decentralized_minimum_delegation_set_zero(self):
        self.update_governance()
        # set Revision REV_IISS
        tx: dict = self.create_set_revision_tx(REV_IISS)
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)

        main_preps = self._addr_array[:PREP_MAIN_PREPS]

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
            tx: dict = self.create_register_prep_tx(address,
                                                    public_key=f"0x{self.public_key_array[i].hex()}",
                                                    value=2000 * ICX_IN_LOOP)
            tx_list.append(tx)
        prev_block, tx_results = self._make_and_req_block(tx_list)
        for tx_result in tx_results:
            self.assertEqual(int(True), tx_result.status)
        self._write_precommit_state(prev_block)

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
                'delegated': 0
            })
            expected_total_delegated += 0
        expected_response: dict = {
            "preps": expected_preps,
            "totalDelegated": 0
        }
        self.assertEqual(expected_response, response)


