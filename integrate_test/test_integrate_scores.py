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

from iconcommons.icon_config import IconConfig
from iconservice.base.address import ZERO_SCORE_ADDRESS
from iconservice.icon_config import default_icon_config
from iconservice.icon_constant import ConfigKey
from iconservice.icon_inner_service import IconScoreInnerTask
from integrate_test.test_integrate_base import TestIntegrateBase

from hashlib import sha3_256

class TestIntegrateScores(TestIntegrateBase):
    def setUp(self):
        super().setUp()
        self.sample_root = "test_scores"

        conf = IconConfig("", default_icon_config)
        conf.load()
        conf.update_conf({ConfigKey.BUILTIN_SCORE_OWNER: str(self._admin_addr)})

        self._inner_task = IconScoreInnerTask(conf)

        is_commit, tx_results = self._run_async(self._genesis_invoke())
        self.assertEqual(is_commit, True)
        self.assertEqual(tx_results[0]['status'], hex(1))

    def test_l_coin(self):
        validate_tx_response1, tx1 = self._run_async(
            self._make_deploy_tx(self.sample_root, "l_coin_3", ZERO_SCORE_ADDRESS, self._admin_addr))
        self.assertEqual(validate_tx_response1, hex(0))

        precommit_req1, tx_results1 = self._run_async(self._make_and_req_block([tx1]))

        tx_result1 = self._get_tx_result(tx_results1, tx1)
        self.assertEqual(tx_result1['status'], hex(True))
        score_addr1 = tx_result1['scoreAddress']

        response = self._run_async(self._write_precommit_state(precommit_req1))
        self.assertEqual(response, hex(0))

    def test_using_crypto(self):
        validate_tx_response1, tx1 = self._run_async(
            self._make_deploy_tx(self.sample_root, "test_using_crypto", ZERO_SCORE_ADDRESS, self._admin_addr))
        self.assertEqual(validate_tx_response1, hex(0))

        precommit_req1, tx_results1 = self._run_async(self._make_and_req_block([tx1]))

        tx_result1 = self._get_tx_result(tx_results1, tx1)
        self.assertEqual(tx_result1['status'], hex(True))
        score_addr1 = tx_result1['scoreAddress']

        response = self._run_async(self._write_precommit_state(precommit_req1))
        self.assertEqual(response, hex(0))

        value = 'a'

        query_request = {
            "version": hex(self._version),
            "from": str(self._admin_addr),
            "to": score_addr1,
            "dataType": "call",
            "data": {
                "method": "get_value",
                "params": {"value": value}
            }
        }
        response = self._run_async(self._query(query_request))
        self.assertEqual(response, sha3_256(value.encode()).hexdigest())


    def test_db_returns(self):
        validate_tx_response1, tx1 = self._run_async(
            self._make_deploy_tx(self.sample_root, "test_db_returns", ZERO_SCORE_ADDRESS, self._admin_addr,
                                 deploy_params={"value": str(self._admin_addr), "value1": str(self._admin_addr)}))
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
                "method": "get_value1",
                "params": {}
            }
        }
        response = self._run_async(self._query(query_request))
        self.assertEqual(response, hex(0))

        value = 1 * self._icx_factor
        validate_tx_response2, tx2 = self._run_async(
            self._make_score_call_tx(self._admin_addr, score_addr1, 'set_value1', {"value": hex(value)}))
        self.assertEqual(validate_tx_response2, hex(0))

        precommit_req2, tx_results2 = self._run_async(self._make_and_req_block([tx2]))
        tx_result2 = self._get_tx_result(tx_results2, tx2)
        self.assertEqual(tx_result2['status'], hex(True))
        response = self._run_async(self._write_precommit_state(precommit_req2))
        self.assertEqual(response, hex(0))

        response = self._run_async(self._query(query_request))
        self.assertEqual(response, hex(value))

        query_request = {
            "version": hex(self._version),
            "from": str(self._admin_addr),
            "to": score_addr1,
            "dataType": "call",
            "data": {
                "method": "get_value2",
                "params": {}
            }
        }
        response = self._run_async(self._query(query_request))
        self.assertEqual(response, "")

        value = "a"
        validate_tx_response3, tx3 = self._run_async(
            self._make_score_call_tx(self._admin_addr, score_addr1, 'set_value2', {"value": value}))
        self.assertEqual(validate_tx_response3, hex(0))

        precommit_req3, tx_results3 = self._run_async(self._make_and_req_block([tx3]))
        tx_result3 = self._get_tx_result(tx_results3, tx3)
        self.assertEqual(tx_result3['status'], hex(True))
        response = self._run_async(self._write_precommit_state(precommit_req3))
        self.assertEqual(response, hex(0))

        response = self._run_async(self._query(query_request))
        self.assertEqual(response, value)

        query_request = {
            "version": hex(self._version),
            "from": str(self._admin_addr),
            "to": score_addr1,
            "dataType": "call",
            "data": {
                "method": "get_value3",
                "params": {}
            }
        }
        response = self._run_async(self._query(query_request))
        self.assertEqual(response, None)

        value = self._prev_block_hash
        validate_tx_response4, tx4 = self._run_async(
            self._make_score_call_tx(self._admin_addr, score_addr1, 'set_value3', {"value": bytes.hex(value)}))
        self.assertEqual(validate_tx_response4, hex(0))

        precommit_req4, tx_results4 = self._run_async(self._make_and_req_block([tx4]))
        tx_result4 = self._get_tx_result(tx_results4, tx4)
        self.assertEqual(tx_result4['status'], hex(True))
        response = self._run_async(self._write_precommit_state(precommit_req4))
        self.assertEqual(response, hex(0))

        response = self._run_async(self._query(query_request))
        self.assertEqual(response, f"0x{bytes.hex(value)}")

        query_request = {
            "version": hex(self._version),
            "from": str(self._admin_addr),
            "to": score_addr1,
            "dataType": "call",
            "data": {
                "method": "get_value4",
                "params": {}
            }
        }
        response = self._run_async(self._query(query_request))
        self.assertEqual(response, str(self._admin_addr))

        value = str(self._genesis_addr)
        validate_tx_response5, tx5 = self._run_async(
            self._make_score_call_tx(self._admin_addr, score_addr1, 'set_value4', {"value": value}))
        self.assertEqual(validate_tx_response5, hex(0))

        precommit_req5, tx_results5 = self._run_async(self._make_and_req_block([tx5]))
        tx_result5 = self._get_tx_result(tx_results5, tx5)
        self.assertEqual(tx_result5['status'], hex(True))
        response = self._run_async(self._write_precommit_state(precommit_req5))
        self.assertEqual(response, hex(0))

        response = self._run_async(self._query(query_request))
        self.assertEqual(response, value)

        query_request = {
            "version": hex(self._version),
            "from": str(self._admin_addr),
            "to": score_addr1,
            "dataType": "call",
            "data": {
                "method": "get_value5",
                "params": {}
            }
        }
        response = self._run_async(self._query(query_request))
        self.assertEqual(response, hex(False))

        value = True
        validate_tx_response6, tx6 = self._run_async(
            self._make_score_call_tx(self._admin_addr, score_addr1, 'set_value5', {"value": hex(value)}))
        self.assertEqual(validate_tx_response6, hex(0))

        precommit_req6, tx_results6 = self._run_async(self._make_and_req_block([tx6]))
        tx_result6 = self._get_tx_result(tx_results6, tx6)
        self.assertEqual(tx_result6['status'], hex(True))
        response = self._run_async(self._write_precommit_state(precommit_req6))
        self.assertEqual(response, hex(0))

        response = self._run_async(self._query(query_request))
        self.assertEqual(response, hex(value))

        query_request = {
            "version": hex(self._version),
            "from": str(self._admin_addr),
            "to": score_addr1,
            "dataType": "call",
            "data": {
                "method": "get_value6",
                "params": {}
            }
        }
        response = self._run_async(self._query(query_request))
        self.assertEqual(response, str(self._admin_addr))

        value = str(self._genesis_addr)
        validate_tx_response7, tx7 = self._run_async(
            self._make_score_call_tx(self._admin_addr, score_addr1, 'set_value6', {"value": value}))
        self.assertEqual(validate_tx_response7, hex(0))

        precommit_req7, tx_results7 = self._run_async(self._make_and_req_block([tx7]))
        tx_result7 = self._get_tx_result(tx_results7, tx7)
        self.assertEqual(tx_result7['status'], hex(True))
        response = self._run_async(self._write_precommit_state(precommit_req7))
        self.assertEqual(response, hex(0))

        response = self._run_async(self._query(query_request))
        self.assertEqual(response, value)
