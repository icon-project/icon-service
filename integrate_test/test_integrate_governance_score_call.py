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
from iconservice.base.address import AddressPrefix, GOVERNANCE_SCORE_ADDRESS
from iconservice.icon_config import default_icon_config
from iconservice.icon_constant import ConfigKey
from iconservice.icon_inner_service import IconScoreInnerTask
from tests import create_address
from integrate_test.test_integrate_base import TestIntegrateBase


class TestIntegrateGovernanceScoreCall(TestIntegrateBase):
    def setUp(self):
        super().setUp()
        self.sample_root = "test_deploy_scores"
        self._addr1 = create_address(AddressPrefix.EOA)

        conf = IconConfig("", default_icon_config)
        conf.load()
        conf.update_conf({ConfigKey.BUILTIN_SCORE_OWNER: str(self._admin_addr)})

        self._inner_task = IconScoreInnerTask(conf)
        self._inner_task._open()

        is_commit, tx_results = self._run_async(self._genesis_invoke())
        self.assertEqual(is_commit, True)
        self.assertEqual(tx_results[0]['status'], hex(1))

    def test_governance_score_call1(self):
        query_request = {
            "version": hex(self._version),
            "from": str(self._admin_addr),
            "to": str(GOVERNANCE_SCORE_ADDRESS),
            "dataType": "call",
            "data": {
                "method": "isDeployer",
                "params": {
                    "address": str(self._admin_addr)
                }
            }
        }

        response = self._run_async(self._query(query_request))
        self.assertEqual(response, hex(True))

    def test_governance_score_call2(self):
        query_request = {
            "version": hex(self._version),
            "from": str(self._admin_addr),
            "to": str(GOVERNANCE_SCORE_ADDRESS),
            "dataType": "call",
            "data": {
                "method": "isDeployer",
                "params": {
                    "address": str(self._addr1)
                }
            }
        }

        response = self._run_async(self._query(query_request))
        self.assertEqual(response, hex(False))

        validate_tx_response1, tx1 = self._run_async(
            self._make_score_call_tx(
                self._admin_addr, GOVERNANCE_SCORE_ADDRESS, 'addDeployer', {"address": str(self._addr1)}))
        self.assertEqual(validate_tx_response1, hex(0))

        precommit_req1, tx_results1 = self._run_async(self._make_and_req_block([tx1]))
        tx_result1 = self._get_tx_result(tx_results1, tx1)
        self.assertEqual(tx_result1['status'], hex(True))
        response = self._run_async(self._write_precommit_state(precommit_req1))
        self.assertEqual(response, hex(0))

        response = self._run_async(self._query(query_request))
        self.assertEqual(response, hex(True))


if __name__ == '__main__':
    unittest.main()
