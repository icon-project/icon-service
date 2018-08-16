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
from iconservice import ExceptionCode
from iconservice.base.address import AddressPrefix, ZERO_SCORE_ADDRESS, GOVERNANCE_SCORE_ADDRESS
from iconservice.icon_config import default_icon_config
from iconservice.icon_constant import ConfigKey
from iconservice.icon_inner_service import IconScoreInnerTask
from tests import create_address, raise_exception_start_tag, raise_exception_end_tag
from integrate_test.test_integrate_base import TestIntegrateBase


class TestIntegrateDeployBlackList(TestIntegrateBase):
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

    def test_score_add_blacklist(self):
        value = 1 * self._icx_factor
        validate_tx_response1, tx1 = self._run_async(
            self._make_deploy_tx(self.sample_root, "install/test_score", ZERO_SCORE_ADDRESS, self._admin_addr,
                                 deploy_params={'value': hex(value)}))
        self.assertEqual(validate_tx_response1, hex(0))

        validate_tx_response2, tx2 = self._run_async(
            self._make_deploy_tx("test_internal_call_scores", "test_link_score", ZERO_SCORE_ADDRESS, self._admin_addr,
                                 deploy_params={'value': hex(value)}))
        self.assertEqual(validate_tx_response2, hex(0))

        precommit_req1, tx_results1 = self._run_async(self._make_and_req_block([tx1, tx2]))

        tx_result1 = self._get_tx_result(tx_results1, tx1)
        self.assertEqual(tx_result1['status'], hex(True))
        score_addr1 = tx_result1['scoreAddress']

        tx_result2 = self._get_tx_result(tx_results1, tx2)
        self.assertEqual(tx_result2['status'], hex(True))
        score_addr2 = tx_result2['scoreAddress']

        response = self._run_async(self._write_precommit_state(precommit_req1))
        self.assertEqual(response, hex(0))

        validate_tx_response3, tx3 = self._run_async(
            self._make_score_call_tx(self._admin_addr, score_addr2, 'add_score_func', {"score_addr": score_addr1}))
        self.assertEqual(validate_tx_response3, hex(0))

        validate_tx_response4, tx4 = self._run_async(
            self._make_score_call_tx(self._admin_addr, GOVERNANCE_SCORE_ADDRESS, 'addToScoreBlackList',
                                     {"address": score_addr1}))
        self.assertEqual(validate_tx_response4, hex(0))

        precommit_req3, tx_results3 = self._run_async(self._make_and_req_block([tx3, tx4]))
        tx_result3 = self._get_tx_result(tx_results3, tx3)
        self.assertEqual(tx_result3['status'], hex(True))
        tx_result4 = self._get_tx_result(tx_results3, tx4)
        self.assertEqual(tx_result4['status'], hex(True))

        response = self._run_async(self._write_precommit_state(precommit_req3))
        self.assertEqual(response, hex(0))

        query_request = {
            "version": hex(self._version),
            "from": str(self._admin_addr),
            "to": score_addr1,
            "dataType": "call",
            "data": {
                "method": "get_value",
                "params": {}
            }
        }
        raise_exception_start_tag("test_score_add_blacklist")
        response = self._run_async(self._query(query_request))
        self.assertEqual(response['error']['code'], ExceptionCode.SERVER_ERROR)

        value = 2 * self._icx_factor
        validate_tx_response3, tx3 = self._run_async(
            self._make_score_call_tx(self._admin_addr, score_addr1, 'set_value', {"value": hex(value)}))
        self.assertEqual(validate_tx_response3['error']['code'], ExceptionCode.SERVER_ERROR)

        precommit_req3, error_response = self._run_async(self._make_and_req_block([tx3]))
        self.assertEqual(error_response['error']['code'], ExceptionCode.SERVER_ERROR)

        query_request = {
            "version": hex(self._version),
            "from": str(self._admin_addr),
            "to": score_addr2,
            "dataType": "call",
            "data": {
                "method": "get_value",
                "params": {}
            }
        }

        response = self._run_async(self._query(query_request))
        self.assertEqual(response['error']['code'], ExceptionCode.SERVER_ERROR)
        raise_exception_end_tag("test_score_add_blacklist")

    def test_score_add_blacklist_not_version_field(self):
        value = 1 * self._icx_factor
        validate_tx_response1, tx1 = self._run_async(
            self._make_deploy_tx(self.sample_root, "install/test_score", ZERO_SCORE_ADDRESS, self._admin_addr,
                                 deploy_params={'value': hex(value)}))
        self.assertEqual(validate_tx_response1, hex(0))

        precommit_req1, tx_results1 = self._run_async(self._make_and_req_block([tx1]))

        tx_result1 = self._get_tx_result(tx_results1, tx1)
        self.assertEqual(tx_result1['status'], hex(True))
        score_addr1 = tx_result1['scoreAddress']

        response = self._run_async(self._write_precommit_state(precommit_req1))
        self.assertEqual(response, hex(0))

        validate_tx_response2, tx2 = self._run_async(
            self._make_score_call_tx(self._admin_addr, GOVERNANCE_SCORE_ADDRESS, 'addToScoreBlackList',
                                     {"address": score_addr1}))
        self.assertEqual(validate_tx_response2, hex(0))

        precommit_req2, tx_results2 = self._run_async(self._make_and_req_block([tx2]))
        tx_result2 = self._get_tx_result(tx_results2, tx2)
        self.assertEqual(tx_result2['status'], hex(True))

        response = self._run_async(self._write_precommit_state(precommit_req2))
        self.assertEqual(response, hex(0))

        query_request = {
            "from": str(self._admin_addr),
            "to": str(GOVERNANCE_SCORE_ADDRESS),
            "dataType": "call",
            "data": {
                "method": "isInScoreBlackList",
                "params": {"address": score_addr1}
            }
        }
        response = self._run_async(self._query(query_request))
        self.assertEqual(response, hex(True))

        query_request = {
            "to": score_addr1,
            "dataType": "call",
            "data": {
                "method": "get_value",
                "params": {}
            }
        }
        raise_exception_start_tag("test_score_add_blacklist")
        response = self._run_async(self._query(query_request))
        self.assertEqual(response['error']['code'], ExceptionCode.SERVER_ERROR)

        value = 2 * self._icx_factor
        validate_tx_response3, tx3 = self._run_async(
            self._make_score_call_tx(self._admin_addr, score_addr1, 'set_value', {"value": hex(value)}))
        self.assertEqual(validate_tx_response3['error']['code'], ExceptionCode.SERVER_ERROR)

        precommit_req3, error_response = self._run_async(self._make_and_req_block([tx3]))
        self.assertEqual(error_response['error']['code'], ExceptionCode.SERVER_ERROR)
        raise_exception_end_tag("test_score_add_blacklist")

    def test_score_remove_deployer(self):
        value = 1 * self._icx_factor
        validate_tx_response1, tx1 = self._run_async(
            self._make_deploy_tx(self.sample_root, "install/test_score", ZERO_SCORE_ADDRESS, self._admin_addr,
                                 deploy_params={'value': hex(value)}))
        self.assertEqual(validate_tx_response1, hex(0))

        precommit_req1, tx_results1 = self._run_async(self._make_and_req_block([tx1]))

        tx_result1 = self._get_tx_result(tx_results1, tx1)
        self.assertEqual(tx_result1['status'], hex(True))
        score_addr1 = tx_result1['scoreAddress']

        response = self._run_async(self._write_precommit_state(precommit_req1))
        self.assertEqual(response, hex(0))

        validate_tx_response2, tx2 = self._run_async(
            self._make_score_call_tx(self._admin_addr, GOVERNANCE_SCORE_ADDRESS, 'addToScoreBlackList',
                                     {"address": str(score_addr1)}))
        self.assertEqual(validate_tx_response2, hex(0))

        validate_tx_response3, tx3 = self._run_async(
            self._make_score_call_tx(self._admin_addr, GOVERNANCE_SCORE_ADDRESS, 'removeFromScoreBlackList',
                                     {"address": str(score_addr1)}))
        self.assertEqual(validate_tx_response3, hex(0))

        precommit_req2, tx_results2 = self._run_async(self._make_and_req_block([tx2, tx3]))
        tx_result2 = self._get_tx_result(tx_results2, tx2)
        self.assertEqual(tx_result2['status'], hex(True))

        response = self._run_async(self._write_precommit_state(precommit_req2))
        self.assertEqual(response, hex(0))

        query_request = {
            "version": hex(self._version),
            "from": str(self._admin_addr),
            "to": score_addr1,
            "dataType": "call",
            "data": {
                "method": "get_value",
                "params": {}
            }
        }

        response = self._run_async(self._query(query_request))
        self.assertEqual(response, hex(value))

        value = 1 * self._icx_factor
        validate_tx_response4, tx4 = self._run_async(
            self._make_score_call_tx(self._admin_addr, score_addr1, 'set_value', {"value": hex(value)}))
        self.assertEqual(validate_tx_response4, hex(0))

        precommit_req3, tx_results3 = self._run_async(self._make_and_req_block([tx4]))
        tx_result4 = self._get_tx_result(tx_results3, tx4)
        self.assertEqual(tx_result4['status'], hex(True))

        response = self._run_async(self._write_precommit_state(precommit_req3))
        self.assertEqual(response, hex(0))

        response = self._run_async(self._query(query_request))
        self.assertEqual(response, hex(value))


if __name__ == '__main__':
    unittest.main()
