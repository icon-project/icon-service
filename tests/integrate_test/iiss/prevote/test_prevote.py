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

"""Test for icon_score_base.py and icon_score_base2.py"""

import unittest

from iconservice.base.exception import MethodNotFoundException
from iconservice.icon_constant import REV_IISS, ConfigKey, ICX_IN_LOOP
from tests.integrate_test.iiss.test_iiss_base import TestIISSBase


class TestIISS(TestIISSBase):
    def _make_init_config(self) -> dict:
        config: dict = super()._make_init_config()
        config[ConfigKey.PREP_REGISTRATION_FEE] = 0
        return config

    def test_get_IISS_info(self):
        self.update_governance()

        # set Revision REV_IISS
        tx: dict = self.create_set_revision_tx(REV_IISS)
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)

        block_height: int = self._block_height

        # get iiss info
        response: dict = self.get_iiss_info()
        expected_response = {
            'nextCalculation': block_height + 1,
            'nextPRepTerm': 0,
            'variable': {
                "irep": 0,
                "rrep": 1200
            }
        }
        self.assertEqual(expected_response, response)

    def test_estimate_step_prevote(self):
        self.update_governance()

        # set Revision REV_IISS
        tx: dict = self.create_set_revision_tx(REV_IISS)
        prev_block, tx_results = self._make_and_req_block([tx])
        self.assertEqual(int(True), tx_results[0].status)
        self._write_precommit_state(prev_block)

        balance: int = 3000 * ICX_IN_LOOP
        tx = self._make_icx_send_tx(self._genesis, self._addr_array[0], balance)
        prev_block, tx_results = self._make_and_req_block([tx])
        self.assertEqual(int(True), tx_results[0].status)
        self._write_precommit_state(prev_block)

        # set stake
        tx: dict = self.create_set_stake_tx(self._addr_array[0], 0)
        self.estimate_step(tx)

        # set delegation
        tx: dict = self.create_set_delegation_tx(self._addr_array[0], [(self._addr_array[0], 0)])
        self.estimate_step(tx)

        # claim iscore
        tx: dict = self.create_claim_tx(self._addr_array[0])
        self.estimate_step(tx)

        # register prep
        tx: dict = self.create_register_prep_tx(self._addr_array[0], public_key=f"0x{self.public_key_array[0].hex()}")
        self.estimate_step(tx)

        # real register prep
        tx: dict = self.create_register_prep_tx(self._addr_array[0], public_key=f"0x{self.public_key_array[0].hex()}")
        prev_block, tx_results = self._make_and_req_block([tx])
        self.assertEqual(int(True), tx_results[0].status)
        self._write_precommit_state(prev_block)

        # set prep
        tx: dict = self.create_set_prep_tx(self._addr_array[0], {"name": f"new{str(self._addr_array[0])}"})
        self.estimate_step(tx)

        # set governance variable
        tx: dict = self.create_set_governance_variables(self._addr_array[0], 5_000_000)
        with self.assertRaises(MethodNotFoundException):
            self.estimate_step(tx)

        # unregister prep
        tx: dict = self.create_unregister_prep_tx(self._addr_array[0])
        self.estimate_step(tx)


if __name__ == '__main__':
    unittest.main()
