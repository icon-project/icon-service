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

import unittest

from iconservice.base.address import ZERO_SCORE_ADDRESS, GOVERNANCE_SCORE_ADDRESS
from iconservice.icon_constant import ConfigKey
from tests.integrate_test.test_integrate_base import TestIntegrateBase


class TestIntegrateSendingIcx(TestIntegrateBase):

    def _make_init_config(self) -> dict:
        return {ConfigKey.SERVICE: {ConfigKey.SERVICE_FEE: True}}

    def _update_governance(self):
        tx = self._make_deploy_tx("test_builtin",
                                  "0_0_4/governance",
                                  self._admin,
                                  GOVERNANCE_SCORE_ADDRESS)
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        tx = self._make_score_call_tx(self._admin,
                                      GOVERNANCE_SCORE_ADDRESS,
                                      "setRevision",
                                      {"code": hex(3), "name": "1.1.2.7"})
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)

    def test_fail_icx_validator(self):
        icx = 3 * 10 ** 16
        tx = self._make_icx_send_tx(self._genesis, self._addr_array[0], icx, step_limit=1 * 10 ** 6)
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)

        # Checks SCORE balance. It should be 0
        response = self._query({"address": self._addr_array[0]}, 'icx_getBalance')
        self.assertEqual(icx, response)

        tx1 = self._make_icx_send_tx(self._addr_array[0], self._addr_array[1], 1 * 10 ** 16, support_v2=True)
        tx2 = self._make_icx_send_tx(self._addr_array[0], self._addr_array[1], 1 * 10 ** 16, support_v2=True)

        prev_block, tx_results = self._make_and_req_block([tx1, tx2])
        self._write_precommit_state(prev_block)

        self.assertEqual(tx_results[0].status, 1)
        self.assertEqual(tx_results[0].step_used, 1_000_000)

        self.assertEqual(tx_results[1].status, 1)
        # wrong!
        self.assertEqual(tx_results[1].step_used, 0)

    def test_fix_icx_validator(self):
        self._update_governance()

        icx = 3 * 10 ** 16
        tx = self._make_icx_send_tx(self._genesis, self._addr_array[0], icx, step_limit=1 * 10 ** 6)
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)

        # Checks SCORE balance. It should be 0
        response = self._query({"address": self._addr_array[0]}, 'icx_getBalance')
        self.assertEqual(icx, response)

        tx1 = self._make_icx_send_tx(self._addr_array[0], self._addr_array[1], 1 * 10 ** 16, support_v2=True)
        tx2 = self._make_icx_send_tx(self._addr_array[0], self._addr_array[1], 1 * 10 ** 16, support_v2=True)

        prev_block, tx_results = self._make_and_req_block([tx1, tx2])
        self._write_precommit_state(prev_block)

        self.assertEqual(tx_results[0].status, 1)
        self.assertEqual(tx_results[0].step_used, 1000000)

        self.assertEqual(tx_results[1].status, 0)


if __name__ == '__main__':
    unittest.main()
