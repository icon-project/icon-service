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

from iconcommons.icon_config import IconConfig
from iconservice.base.address import ZERO_SCORE_ADDRESS, GOVERNANCE_SCORE_ADDRESS, AddressPrefix
from iconservice.icon_config import default_icon_config
from iconservice.icon_constant import ConfigKey
from iconservice.icon_inner_service import IconScoreInnerTask
from tests import create_address
from integrate_test.test_integrate_base import TestIntegrateBase


class TestIntegrateDeployAuditDeployOwner(TestIntegrateBase):
    def setUp(self):
        super().setUp()
        self.sample_root = "test_audit_deploy_owner"

        conf = IconConfig("", default_icon_config)
        conf.load()
        conf.update_conf({ConfigKey.BUILTIN_SCORE_OWNER: str(self._admin_addr),
                          ConfigKey.SERVICE: {ConfigKey.SERVICE_AUDIT: True}})

        self._inner_task = IconScoreInnerTask(conf)
        self._inner_task._open()

        is_commit, tx_results = self._run_async(self._genesis_invoke())
        self.assertEqual(is_commit, True)
        self.assertEqual(tx_results[0]['status'], hex(1))

    def test_score(self):
        addr1 = create_address(AddressPrefix.EOA)
        addr2 = create_address(AddressPrefix.EOA)
        validate_tx_response1, tx1 = self._run_async(
            self._make_deploy_tx(self.sample_root, "test_score", ZERO_SCORE_ADDRESS, addr1))
        self.assertEqual(validate_tx_response1, hex(0))

        precommit_req1, tx_results1 = self._run_async(self._make_and_req_block([tx1]))

        tx_result1 = self._get_tx_result(tx_results1, tx1)
        self.assertEqual(tx_result1['status'], hex(True))
        tx_hash1 = tx_result1['txHash']
        score_addr1 = tx_result1['scoreAddress']

        response = self._run_async(self._write_precommit_state(precommit_req1))
        self.assertEqual(response, hex(0))

        validate_tx_response2, tx2 = self._run_async(
            self._make_score_call_tx(self._admin_addr, GOVERNANCE_SCORE_ADDRESS, 'acceptScore', {"txHash": tx_hash1}))
        self.assertEqual(validate_tx_response2, hex(0))

        precommit_req2, tx_results2 = self._run_async(self._make_and_req_block([tx2]))
        tx_result2 = self._get_tx_result(tx_results2, tx2)
        self.assertEqual(tx_result2['status'], hex(True))

        response = self._run_async(self._write_precommit_state(precommit_req2))
        self.assertEqual(response, hex(0))

        validate_tx_response3, tx3 = self._run_async(
            self._make_deploy_tx(self.sample_root, "test_link_score", ZERO_SCORE_ADDRESS, addr2,
                                 deploy_params={"score_addr": score_addr1}))
        self.assertEqual(validate_tx_response3, hex(0))

        precommit_req3, tx_results3 = self._run_async(self._make_and_req_block([tx3]))
        tx_result3 = self._get_tx_result(tx_results3, tx3)
        self.assertEqual(tx_result3['status'], hex(True))
        score_addr2 = tx_result3['scoreAddress']
        tx_hash2 = tx_result3['txHash']

        response = self._run_async(self._write_precommit_state(precommit_req3))
        self.assertEqual(response, hex(0))

        validate_tx_response4, tx4 = self._run_async(
            self._make_score_call_tx(self._admin_addr, GOVERNANCE_SCORE_ADDRESS, 'acceptScore', {"txHash": tx_hash2}))
        self.assertEqual(validate_tx_response4, hex(0))

        precommit_req4, tx_results4 = self._run_async(self._make_and_req_block([tx4]))
        tx_result4 = self._get_tx_result(tx_results4, tx4)
        self.assertEqual(tx_result4['status'], hex(True))
        event_logs: list = tx_result4['eventLogs']
        # before_install, hello, after_install, _ = event_logs
        # before_install = before_install['indexed']
        # hello = hello['indexed']
        # after_install = after_install['indexed']
        # self.assertEqual(before_install[1], str(addr2))
        # self.assertEqual(before_install[2], str(addr2))
        # self.assertEqual(hello[1], score_addr2)
        # self.assertEqual(hello[2], str(addr2))
        # self.assertEqual(after_install[1], str(addr2))
        # self.assertEqual(after_install[2], str(addr2))


if __name__ == '__main__':
    unittest.main()
