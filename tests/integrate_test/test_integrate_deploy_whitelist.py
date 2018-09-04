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
from iconservice.base.exception import ExceptionCode
from iconservice.icon_constant import ConfigKey
from tests.integrate_test.test_integrate_base import TestIntegrateBase


class TestIntegrateDeployWhiteList(TestIntegrateBase):

    def _make_init_config(self) -> dict:
        return {ConfigKey.SERVICE: {ConfigKey.SERVICE_DEPLOYER_WHITELIST: True}}

    def test_score(self):
        value = 1 * self._icx_factor
        tx1 = self._make_deploy_tx("test_deploy_scores",
                                   "install/test_score",
                                   self._admin,
                                   ZERO_SCORE_ADDRESS,
                                   deploy_params={'value': hex(value)})

        prev_block, tx_results = self._make_and_req_block([tx1])

        self._write_precommit_state(prev_block)

        self.assertEqual(tx_results[0].status, int(True))
        score_addr1 = tx_results[0].score_address

        query_request = {
            "version": self._version,
            "from": self._admin,
            "to": score_addr1,
            "dataType": "call",
            "data": {
                "method": "get_value",
                "params": {}
            }
        }
        response = self._query(query_request)
        self.assertEqual(response, value)

        tx2 = self._make_score_call_tx(self._admin,
                                       score_addr1,
                                       'set_value',
                                       {"value": hex(value)})

        prev_block, tx_results = self._make_and_req_block([tx2])

        self._write_precommit_state(prev_block)

        self.assertEqual(tx_results[0].status, int(True))

    def test_score_add_deployer(self):
        value = 1 * self._icx_factor

        with self.assertRaises(BaseException) as e:
            self._make_deploy_tx("test_deploy_scores",
                                 "install/test_score",
                                 self._addr_array[0],
                                 ZERO_SCORE_ADDRESS,
                                 deploy_params={'value': hex(value)})
        self.assertEqual(e.exception.code, ExceptionCode.SERVER_ERROR)
        self.assertEqual(e.exception.message, f"Invalid deployer: no permission (address: {self._addr_array[0]})")

        tx1 = self._make_score_call_tx(self._admin,
                                       GOVERNANCE_SCORE_ADDRESS,
                                       'addDeployer',
                                       {"address": str(self._addr_array[0])})

        prev_block, tx_results = self._make_and_req_block([tx1])

        self._write_precommit_state(prev_block)

        self.assertEqual(tx_results[0].status, int(True))

        tx2 = self._make_deploy_tx("test_deploy_scores",
                                   "install/test_score",
                                   self._addr_array[0],
                                   ZERO_SCORE_ADDRESS,
                                   deploy_params={'value': hex(value)})

        prev_block, tx_results = self._make_and_req_block([tx2])

        self._write_precommit_state(prev_block)

        self.assertEqual(tx_results[0].status, int(True))
        score_addr1 = tx_results[0].score_address

        query_request = {
            "version": self._version,
            "from": self._admin,
            "to": score_addr1,
            "dataType": "call",
            "data": {
                "method": "get_value",
                "params": {}
            }
        }
        response = self._query(query_request)
        self.assertEqual(response, value)

        value2 = 2 * self._icx_factor
        tx2 = self._make_score_call_tx(self._addr_array[0],
                                       score_addr1,
                                       'set_value',
                                       {"value": hex(value2)})

        prev_block, tx_results = self._make_and_req_block([tx2])

        self._write_precommit_state(prev_block)

        self.assertEqual(tx_results[0].status, int(True))

        response = self._query(query_request)
        self.assertEqual(response, value2)

    def test_score_remove_deployer(self):
        value = 1 * self._icx_factor

        tx1 = self._make_score_call_tx(self._admin,
                                       GOVERNANCE_SCORE_ADDRESS,
                                       'addDeployer',
                                       {"address": str(self._addr_array[0])})

        prev_block, tx_results = self._make_and_req_block([tx1])

        self._write_precommit_state(prev_block)

        self.assertEqual(tx_results[0].status, int(True))

        tx2 = self._make_deploy_tx("test_deploy_scores",
                                   "install/test_score",
                                   self._addr_array[0],
                                   ZERO_SCORE_ADDRESS,
                                   deploy_params={'value': hex(value)})

        tx3 = self._make_score_call_tx(self._admin,
                                       GOVERNANCE_SCORE_ADDRESS,
                                       'removeDeployer',
                                       {"address": str(self._addr_array[0])})

        prev_block, tx_results = self._make_and_req_block([tx2, tx3])

        self._write_precommit_state(prev_block)

        self.assertEqual(tx_results[0].status, int(True))
        score_addr1 = tx_results[0].score_address
        self.assertEqual(tx_results[1].status, int(True))

        with self.assertRaises(BaseException) as e:
            self._make_deploy_tx("test_deploy_scores",
                                 "update/test_score",
                                 self._addr_array[0],
                                 score_addr1,
                                 deploy_params={'value': hex(value)})
        self.assertEqual(e.exception.code, ExceptionCode.SERVER_ERROR)
        self.assertEqual(e.exception.message, f"Invalid deployer: no permission (address: {self._addr_array[0]})")


if __name__ == '__main__':
    unittest.main()
