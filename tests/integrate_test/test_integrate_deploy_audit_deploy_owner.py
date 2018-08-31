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


class TestIntegrateDeployAuditDeployOwner(TestIntegrateBase):

    def _make_init_config(self) -> dict:
        return {ConfigKey.SERVICE: {ConfigKey.SERVICE_AUDIT: True}}

    def test_score(self):
        tx1 = self._make_deploy_tx("test_audit_deploy_owner",
                                   "test_score",
                                   self._addr_array[0],
                                   ZERO_SCORE_ADDRESS)

        prev_block, tx_results = self._make_and_req_block([tx1])

        self._write_precommit_state(prev_block)

        self.assertEqual(tx_results[0].status, int(True))
        score_addr1 = tx_results[0].score_address
        tx_hash1 = tx_results[0].tx_hash

        tx2 = self._make_score_call_tx(self._admin,
                                       GOVERNANCE_SCORE_ADDRESS,
                                       'acceptScore',
                                       {"txHash": f'0x{bytes.hex(tx_hash1)}'})

        prev_block, tx_results = self._make_and_req_block([tx2])

        self._write_precommit_state(prev_block)

        self.assertEqual(tx_results[0].status, int(True))

        tx3 = self._make_deploy_tx("test_audit_deploy_owner",
                                   "test_link_score",
                                   self._addr_array[1],
                                   ZERO_SCORE_ADDRESS,
                                   deploy_params={"score_addr": str(score_addr1)})

        prev_block, tx_results = self._make_and_req_block([tx3])

        self._write_precommit_state(prev_block)

        self.assertEqual(tx_results[0].status, int(True))
        score_addr2 = tx_results[0].score_address
        tx_hash2 = tx_results[0].tx_hash

        tx4 = self._make_score_call_tx(self._admin,
                                       GOVERNANCE_SCORE_ADDRESS,
                                       'acceptScore',
                                       {"txHash": f'0x{bytes.hex(tx_hash2)}'})

        prev_block, tx_results = self._make_and_req_block([tx4])

        self._write_precommit_state(prev_block)

        self.assertEqual(tx_results[0].status, int(True))

        event_logs: list = tx_results[0].event_logs
        before_install, hello, after_install, _ = event_logs
        before_install = before_install.indexed
        hello = hello.indexed
        after_install = after_install.indexed
        self.assertEqual(before_install[1], self._addr_array[1])
        self.assertEqual(hello[1], score_addr2)
        self.assertEqual(after_install[1], self._addr_array[1])


if __name__ == '__main__':
    unittest.main()
