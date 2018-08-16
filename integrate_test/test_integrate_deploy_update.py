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
from iconservice.base.address import AddressPrefix, ZERO_SCORE_ADDRESS
from iconservice.base.exception import ExceptionCode
from iconservice.icon_config import default_icon_config
from iconservice.icon_constant import ConfigKey
from iconservice.icon_inner_service import IconScoreInnerTask
from integrate_test.test_integrate_base import TestIntegrateBase
from tests import create_address, raise_exception_start_tag, raise_exception_end_tag


class TestIntegrateDeployUpdate(TestIntegrateBase):
    def setUp(self):
        super().setUp()
        self.sample_root = "test_deploy_scores"
        self._addr1 = create_address(AddressPrefix.EOA)

        conf = IconConfig("", default_icon_config)
        conf.load()
        conf.update_conf({ConfigKey.BUILTIN_SCORE_OWNER: str(self._admin_addr)})

        self._inner_task = IconScoreInnerTask(conf)

        is_commit, tx_results = self._run_async(self._genesis_invoke())
        self.assertEqual(is_commit, True)
        self.assertEqual(tx_results[0]['status'], hex(1))

    def test_score(self):
        value1 = 1 * self._icx_factor
        validate_tx_response1, tx1 = self._run_async(
            self._make_deploy_tx(self.sample_root, "install/test_score", ZERO_SCORE_ADDRESS, self._admin_addr,
                                 deploy_params={'value': hex(value1)}))
        self.assertEqual(validate_tx_response1, hex(0))

        precommit_req1, tx_results1 = self._run_async(self._make_and_req_block([tx1]))

        tx_result1 = self._get_tx_result(tx_results1, tx1)
        self.assertEqual(tx_result1['status'], hex(True))
        score_addr1 = tx_result1['scoreAddress']

        response = self._run_async(self._write_precommit_state(precommit_req1))
        self.assertEqual(response, hex(0))

        value2 = 2 * self._icx_factor
        validate_tx_response2, tx2 = self._run_async(
            self._make_deploy_tx(self.sample_root, "update/test_score", score_addr1, self._admin_addr,
                                 deploy_params={'value': hex(value2)}))
        self.assertEqual(validate_tx_response2, hex(0))

        precommit_req2, tx_results2 = self._run_async(self._make_and_req_block([tx2]))

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
        self.assertEqual(response, hex(value1 + value2))

        value3 = 2 * self._icx_factor
        validate_tx_response3, tx3 = self._run_async(
            self._make_score_call_tx(self._admin_addr, score_addr1, 'set_value', {"value": hex(value3)}))
        self.assertEqual(validate_tx_response3, hex(0))

        precommit_req3, tx_results3 = self._run_async(self._make_and_req_block([tx3]))
        tx_result3 = self._get_tx_result(tx_results3, tx3)
        self.assertEqual(tx_result3['status'], hex(True))

        response = self._run_async(self._write_precommit_state(precommit_req3))
        self.assertEqual(response, hex(0))

        response = self._run_async(self._query(query_request))
        self.assertEqual(response, hex(value3 * 2))

    def test_score_tx_order(self):
        value1 = 1 * self._icx_factor
        validate_tx_response1, tx1 = self._run_async(
            self._make_deploy_tx(self.sample_root, "install/test_score", ZERO_SCORE_ADDRESS, self._admin_addr,
                                 deploy_params={'value': hex(value1)}))
        self.assertEqual(validate_tx_response1, hex(0))

        precommit_req1, tx_results1 = self._run_async(self._make_and_req_block([tx1]))
        tx_result1 = self._get_tx_result(tx_results1, tx1)
        self.assertEqual(tx_result1['status'], hex(True))
        score_addr1 = tx_result1['scoreAddress']

        response = self._run_async(self._write_precommit_state(precommit_req1))
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
        self.assertEqual(response, hex(value1))

        value2 = 2 * self._icx_factor
        validate_tx_response2, tx2 = self._run_async(
            self._make_score_call_tx(self._admin_addr, score_addr1, 'set_value', {"value": hex(value2)}))
        self.assertEqual(validate_tx_response2, hex(0))

        validate_tx_response3, tx3 = self._run_async(
            self._make_deploy_tx(self.sample_root, "update/test_score", score_addr1, self._admin_addr,
                                 deploy_params={'value': hex(value2)}))
        self.assertEqual(validate_tx_response3, hex(0))

        validate_tx_response4, tx4 = self._run_async(
            self._make_score_call_tx(self._admin_addr, score_addr1, 'set_value', {"value": hex(value2)}))
        self.assertEqual(validate_tx_response4, hex(0))

        precommit_req2, tx_results2 = self._run_async(self._make_and_req_block([tx2, tx3, tx4]))
        tx_result2 = self._get_tx_result(tx_results2, tx2)
        self.assertEqual(tx_result2['status'], hex(True))
        tx_result3 = self._get_tx_result(tx_results2, tx3)
        self.assertEqual(tx_result3['status'], hex(True))
        tx_result4 = self._get_tx_result(tx_results2, tx4)
        self.assertEqual(tx_result4['status'], hex(True))

        response = self._run_async(self._write_precommit_state(precommit_req2))
        self.assertEqual(response, hex(0))

        response = self._run_async(self._query(query_request))
        self.assertEqual(response, hex(value2 * 2))

    def test_invalid_owner(self):
        value1 = 1 * self._icx_factor
        validate_tx_response1, tx1 = self._run_async(
            self._make_deploy_tx(self.sample_root, "install/test_score", ZERO_SCORE_ADDRESS, self._admin_addr,
                                 deploy_params={'value': hex(value1)}))
        self.assertEqual(validate_tx_response1, hex(0))

        precommit_req1, tx_results1 = self._run_async(self._make_and_req_block([tx1]))

        tx_result1 = self._get_tx_result(tx_results1, tx1)
        self.assertEqual(tx_result1['status'], hex(True))
        score_addr1 = tx_result1['scoreAddress']

        response = self._run_async(self._write_precommit_state(precommit_req1))
        self.assertEqual(response, hex(0))

        value2 = 2 * self._icx_factor
        validate_tx_response2, tx2 = self._run_async(
            self._make_deploy_tx(self.sample_root, "update/test_score", score_addr1, self._addr1,
                                 deploy_params={'value': hex(value2)}))
        self.assertEqual(validate_tx_response2, hex(0))

        raise_exception_start_tag("test_invalid_owner")
        precommit_req2, tx_results2 = self._run_async(self._make_and_req_block([tx2]))

        tx_result2 = self._get_tx_result(tx_results2, tx2)
        self.assertEqual(tx_result2['status'], hex(False))
        self.assertEqual(tx_result2['failure']['code'], hex(ExceptionCode.SERVER_ERROR))
        raise_exception_end_tag("test_invalid_owner")

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
        self.assertEqual(response, hex(value1))

        value3 = 3 * self._icx_factor
        validate_tx_response3, tx3 = self._run_async(
            self._make_score_call_tx(self._admin_addr, score_addr1, 'set_value', {"value": hex(value3)}))
        self.assertEqual(validate_tx_response3, hex(0))

        precommit_req3, tx_results3 = self._run_async(self._make_and_req_block([tx3]))
        tx_result3 = self._get_tx_result(tx_results3, tx3)
        self.assertEqual(tx_result3['status'], hex(True))

        response = self._run_async(self._write_precommit_state(precommit_req3))
        self.assertEqual(response, hex(0))

        response = self._run_async(self._query(query_request))
        self.assertEqual(response, hex(value3))

    def test_score_no_zip(self):
        value1 = 1 * self._icx_factor
        validate_tx_response1, tx1 = self._run_async(
            self._make_deploy_tx(self.sample_root, "install/test_score", ZERO_SCORE_ADDRESS, self._admin_addr,
                                 deploy_params={'value': hex(value1)}))
        self.assertEqual(validate_tx_response1, hex(0))

        precommit_req1, tx_results1 = self._run_async(self._make_and_req_block([tx1]))

        tx_result1 = self._get_tx_result(tx_results1, tx1)
        self.assertEqual(tx_result1['status'], hex(True))
        score_addr1 = tx_result1['scoreAddress']

        response = self._run_async(self._write_precommit_state(precommit_req1))
        self.assertEqual(response, hex(0))

        value2 = 2 * self._icx_factor
        validate_tx_response2, tx2 = self._run_async(
            self._make_deploy_tx(self.sample_root, "update/test_score", score_addr1, self._admin_addr, data=b'invalid',
                                 deploy_params={'value': hex(value2)}))
        self.assertEqual(validate_tx_response2, hex(0))

        raise_exception_start_tag("test_score_no_zip")
        precommit_req2, tx_results2 = self._run_async(self._make_and_req_block([tx2]))

        tx_result2 = self._get_tx_result(tx_results2, tx2)
        self.assertEqual(tx_result2['status'], hex(False))
        self.assertEqual(tx_result2['failure']['code'], hex(ExceptionCode.SERVER_ERROR))
        raise_exception_end_tag("test_score_no_zip")

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
        self.assertEqual(response, hex(value1))

        value3 = 3 * self._icx_factor
        validate_tx_response3, tx3 = self._run_async(
            self._make_score_call_tx(self._admin_addr, score_addr1, 'set_value', {"value": hex(value3)}))
        self.assertEqual(validate_tx_response3, hex(0))

        precommit_req3, tx_results3 = self._run_async(self._make_and_req_block([tx3]))
        tx_result3 = self._get_tx_result(tx_results3, tx3)
        self.assertEqual(tx_result3['status'], hex(True))

        response = self._run_async(self._write_precommit_state(precommit_req3))
        self.assertEqual(response, hex(0))

        response = self._run_async(self._query(query_request))
        self.assertEqual(response, hex(value3))

    def test_score_no_scorebase(self):
        value1 = 1 * self._icx_factor
        validate_tx_response1, tx1 = self._run_async(
            self._make_deploy_tx(self.sample_root, "install/test_score", ZERO_SCORE_ADDRESS, self._admin_addr,
                                 deploy_params={'value': hex(value1)}))
        self.assertEqual(validate_tx_response1, hex(0))

        precommit_req1, tx_results1 = self._run_async(self._make_and_req_block([tx1]))

        tx_result1 = self._get_tx_result(tx_results1, tx1)
        self.assertEqual(tx_result1['status'], hex(True))
        score_addr1 = tx_result1['scoreAddress']

        response = self._run_async(self._write_precommit_state(precommit_req1))
        self.assertEqual(response, hex(0))

        value2 = 2 * self._icx_factor
        validate_tx_response2, tx2 = self._run_async(
            self._make_deploy_tx(self.sample_root, "install/test_score_no_scorebase", score_addr1, self._admin_addr,
                                 deploy_params={'value': hex(value2)}))
        self.assertEqual(validate_tx_response2, hex(0))

        raise_exception_start_tag("test_score_no_scorebase")
        precommit_req2, tx_results2 = self._run_async(self._make_and_req_block([tx2]))

        tx_result2 = self._get_tx_result(tx_results2, tx2)
        self.assertEqual(tx_result2['status'], hex(False))
        self.assertEqual(tx_result2['failure']['code'], hex(ExceptionCode.SERVER_ERROR))
        raise_exception_end_tag("test_score_no_scorebase")

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
        self.assertEqual(response, hex(value1))

        value3 = 3 * self._icx_factor
        validate_tx_response3, tx3 = self._run_async(
            self._make_score_call_tx(self._admin_addr, score_addr1, 'set_value', {"value": hex(value3)}))
        self.assertEqual(validate_tx_response3, hex(0))

        precommit_req3, tx_results3 = self._run_async(self._make_and_req_block([tx3]))
        tx_result3 = self._get_tx_result(tx_results3, tx3)
        self.assertEqual(tx_result3['status'], hex(True))

        response = self._run_async(self._write_precommit_state(precommit_req3))
        self.assertEqual(response, hex(0))

        response = self._run_async(self._query(query_request))
        self.assertEqual(response, hex(value3))

    def test_score_on_update_error(self):
        value1 = 1 * self._icx_factor
        validate_tx_response1, tx1 = self._run_async(
            self._make_deploy_tx(self.sample_root, "install/test_score", ZERO_SCORE_ADDRESS, self._admin_addr,
                                 deploy_params={'value': hex(value1)}))
        self.assertEqual(validate_tx_response1, hex(0))

        precommit_req1, tx_results1 = self._run_async(self._make_and_req_block([tx1]))

        tx_result1 = self._get_tx_result(tx_results1, tx1)
        self.assertEqual(tx_result1['status'], hex(True))
        score_addr1 = tx_result1['scoreAddress']

        response = self._run_async(self._write_precommit_state(precommit_req1))
        self.assertEqual(response, hex(0))

        value2 = 2 * self._icx_factor
        validate_tx_response2, tx2 = self._run_async(
            self._make_deploy_tx(self.sample_root, "update/test_score_on_update_error", score_addr1, self._admin_addr,
                                 deploy_params={'value': hex(value2)}))
        self.assertEqual(validate_tx_response2, hex(0))

        raise_exception_start_tag("test_score_on_update_error")
        precommit_req2, tx_results2 = self._run_async(self._make_and_req_block([tx2]))

        tx_result2 = self._get_tx_result(tx_results2, tx2)
        self.assertEqual(tx_result2['status'], hex(False))
        self.assertEqual(tx_result2['failure']['code'], hex(ExceptionCode.SERVER_ERROR))
        raise_exception_end_tag("test_score_on_update_error")

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
        self.assertEqual(response, hex(value1))

        value3 = 3 * self._icx_factor
        validate_tx_response3, tx3 = self._run_async(
            self._make_score_call_tx(self._admin_addr, score_addr1, 'set_value', {"value": hex(value3)}))
        self.assertEqual(validate_tx_response3, hex(0))

        precommit_req3, tx_results3 = self._run_async(self._make_and_req_block([tx3]))
        tx_result3 = self._get_tx_result(tx_results3, tx3)
        self.assertEqual(tx_result3['status'], hex(True))

        response = self._run_async(self._write_precommit_state(precommit_req3))
        self.assertEqual(response, hex(0))

        response = self._run_async(self._query(query_request))
        self.assertEqual(response, hex(value3))

    def test_score_no_external_func(self):
        value1 = 1 * self._icx_factor
        validate_tx_response1, tx1 = self._run_async(
            self._make_deploy_tx(self.sample_root, "install/test_score", ZERO_SCORE_ADDRESS, self._admin_addr,
                                 deploy_params={'value': hex(value1)}))
        self.assertEqual(validate_tx_response1, hex(0))

        precommit_req1, tx_results1 = self._run_async(self._make_and_req_block([tx1]))

        tx_result1 = self._get_tx_result(tx_results1, tx1)
        self.assertEqual(tx_result1['status'], hex(True))
        score_addr1 = tx_result1['scoreAddress']

        response = self._run_async(self._write_precommit_state(precommit_req1))
        self.assertEqual(response, hex(0))

        value2 = 2 * self._icx_factor
        validate_tx_response2, tx2 = self._run_async(
            self._make_deploy_tx(self.sample_root, "install/test_score_no_external_func", score_addr1, self._admin_addr,
                                 deploy_params={'value': hex(value2)}))
        self.assertEqual(validate_tx_response2, hex(0))

        raise_exception_start_tag("test_score_no_external_func")
        precommit_req2, tx_results2 = self._run_async(self._make_and_req_block([tx2]))

        tx_result2 = self._get_tx_result(tx_results2, tx2)
        self.assertEqual(tx_result2['status'], hex(False))
        self.assertEqual(tx_result2['failure']['code'], hex(ExceptionCode.SCORE_ERROR))
        raise_exception_end_tag("test_score_no_external_func")

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
        self.assertEqual(response, hex(value1))

        value3 = 3 * self._icx_factor
        validate_tx_response3, tx3 = self._run_async(
            self._make_score_call_tx(self._admin_addr, score_addr1, 'set_value', {"value": hex(value3)}))
        self.assertEqual(validate_tx_response3, hex(0))

        precommit_req3, tx_results3 = self._run_async(self._make_and_req_block([tx3]))
        tx_result3 = self._get_tx_result(tx_results3, tx3)
        self.assertEqual(tx_result3['status'], hex(True))

        response = self._run_async(self._write_precommit_state(precommit_req3))
        self.assertEqual(response, hex(0))

        response = self._run_async(self._query(query_request))
        self.assertEqual(response, hex(value3))

    def test_score_with_korean_comments(self):
        value1 = 1 * self._icx_factor
        validate_tx_response1, tx1 = self._run_async(
            self._make_deploy_tx(self.sample_root, "install/test_score", ZERO_SCORE_ADDRESS, self._admin_addr,
                                 deploy_params={'value': hex(value1)}))
        self.assertEqual(validate_tx_response1, hex(0))

        precommit_req1, tx_results1 = self._run_async(self._make_and_req_block([tx1]))

        tx_result1 = self._get_tx_result(tx_results1, tx1)
        self.assertEqual(tx_result1['status'], hex(True))
        score_addr1 = tx_result1['scoreAddress']

        response = self._run_async(self._write_precommit_state(precommit_req1))
        self.assertEqual(response, hex(0))

        value2 = 2 * self._icx_factor
        validate_tx_response2, tx2 = self._run_async(
            self._make_deploy_tx(self.sample_root, "install/test_score_with_korean_comments", score_addr1, self._admin_addr,
                                 deploy_params={'value': hex(value2)}))
        self.assertEqual(validate_tx_response2, hex(0))

        raise_exception_start_tag("test_score_with_korean_comments")
        precommit_req2, tx_results2 = self._run_async(self._make_and_req_block([tx2]))

        tx_result2 = self._get_tx_result(tx_results2, tx2)
        self.assertEqual(tx_result2['status'], hex(False))
        self.assertEqual(tx_result2['failure']['code'], hex(ExceptionCode.SERVER_ERROR))
        raise_exception_end_tag("test_score_with_korean_comments")

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
        self.assertEqual(response, hex(value1))

        value3 = 3 * self._icx_factor
        validate_tx_response3, tx3 = self._run_async(
            self._make_score_call_tx(self._admin_addr, score_addr1, 'set_value', {"value": hex(value3)}))
        self.assertEqual(validate_tx_response3, hex(0))

        precommit_req3, tx_results3 = self._run_async(self._make_and_req_block([tx3]))
        tx_result3 = self._get_tx_result(tx_results3, tx3)
        self.assertEqual(tx_result3['status'], hex(True))

        response = self._run_async(self._write_precommit_state(precommit_req3))
        self.assertEqual(response, hex(0))

        response = self._run_async(self._query(query_request))
        self.assertEqual(response, hex(value3))

    def test_score_no_python(self):
        value1 = 1 * self._icx_factor
        validate_tx_response1, tx1 = self._run_async(
            self._make_deploy_tx(self.sample_root, "install/test_score", ZERO_SCORE_ADDRESS, self._admin_addr,
                                 deploy_params={'value': hex(value1)}))
        self.assertEqual(validate_tx_response1, hex(0))

        precommit_req1, tx_results1 = self._run_async(self._make_and_req_block([tx1]))

        tx_result1 = self._get_tx_result(tx_results1, tx1)
        self.assertEqual(tx_result1['status'], hex(True))
        score_addr1 = tx_result1['scoreAddress']

        response = self._run_async(self._write_precommit_state(precommit_req1))
        self.assertEqual(response, hex(0))

        value2 = 2 * self._icx_factor
        validate_tx_response2, tx2 = self._run_async(
            self._make_deploy_tx(self.sample_root, "install/test_score_no_python", score_addr1,
                                 self._admin_addr,
                                 deploy_params={'value': hex(value2)}))
        self.assertEqual(validate_tx_response2, hex(0))

        raise_exception_start_tag("test_score_no_python")
        precommit_req2, tx_results2 = self._run_async(self._make_and_req_block([tx2]))

        tx_result2 = self._get_tx_result(tx_results2, tx2)
        self.assertEqual(tx_result2['status'], hex(False))
        self.assertEqual(tx_result2['failure']['code'], hex(ExceptionCode.SERVER_ERROR))
        raise_exception_end_tag("test_score_no_python")

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
        self.assertEqual(response, hex(value1))

        value3 = 3 * self._icx_factor
        validate_tx_response3, tx3 = self._run_async(
            self._make_score_call_tx(self._admin_addr, score_addr1, 'set_value', {"value": hex(value3)}))
        self.assertEqual(validate_tx_response3, hex(0))

        precommit_req3, tx_results3 = self._run_async(self._make_and_req_block([tx3]))
        tx_result3 = self._get_tx_result(tx_results3, tx3)
        self.assertEqual(tx_result3['status'], hex(True))

        response = self._run_async(self._write_precommit_state(precommit_req3))
        self.assertEqual(response, hex(0))

        response = self._run_async(self._query(query_request))
        self.assertEqual(response, hex(value3))


if __name__ == '__main__':
    unittest.main()
