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

"""on_update parameters testcase"""

from iconservice import ZERO_SCORE_ADDRESS
from tests.integrate_test.test_integrate_base import TestIntegrateBase


class TestIntegrateOnUpdateParamters(TestIntegrateBase):

    def test_onupdate_parameters_success(self):
        # deploy
        tx1 = self._make_deploy_tx("test_deploy_scores/install",
                                   "sample_token",
                                   self._addr_array[0],
                                   ZERO_SCORE_ADDRESS, deploy_params={"init_supply": hex(1000), "decimal": "0x12"})

        prev_block, tx_results = self._make_and_req_block([tx1])

        self._write_precommit_state(prev_block)

        self.assertEqual(tx_results[0].status, int(True))

        score_addr1 = tx_results[0].score_address

        query_request = {
            "from": self._admin,
            "to": score_addr1,
            "dataType": "call",
            "data": {
                "method": "total_supply",
            }
        }

        total_supply = self._query(query_request)
        self.assertEqual(total_supply, 1000 * 10 ** 18)

        tx1 = self._make_deploy_tx("test_deploy_scores/install",
                                   "sample_token",
                                   self._addr_array[0],
                                   score_addr1, deploy_params={"update_supply": hex(2000), "decimal": "0x12"})

        prev_block, tx_results = self._make_and_req_block([tx1])

        self._write_precommit_state(prev_block)

        self.assertEqual(tx_results[0].status, int(True))

        total_supply = self._query(query_request)
        self.assertEqual(total_supply, 2000 * 10 ** 18)

    def test_more_parameters_onupdate(self):
        tx1 = self._make_deploy_tx("test_deploy_scores/install",
                                   "sample_token",
                                   self._addr_array[0],
                                   ZERO_SCORE_ADDRESS, deploy_params={"init_supply": hex(1000), "decimal": "0x12"})

        prev_block, tx_results = self._make_and_req_block([tx1])

        self._write_precommit_state(prev_block)

        self.assertEqual(tx_results[0].status, int(True))

        score_addr1 = tx_results[0].score_address

        query_request = {
            "from": self._admin,
            "to": score_addr1,
            "dataType": "call",
            "data": {
                "method": "total_supply",
            }
        }

        total_supply = self._query(query_request)
        self.assertEqual(total_supply, 1000 * 10 ** 18)

        tx1 = self._make_deploy_tx("test_deploy_scores/install", "sample_token", self._addr_array[0],
                                   score_addr1, deploy_params={"update_supply": hex(1000), "decimal": "0x12",
                                                               "additional_param": hex(123)})

        prev_block, tx_results = self._make_and_req_block([tx1])

        self._write_precommit_state(prev_block)

        self.assertEqual(tx_results[0].failure.code, 32000)
        self.assertTrue(tx_results[0].failure.message.find("on_update() got an unexpected keyword argument "
                                                           "'additional_param'") != -1)
        self.assertEqual(tx_results[0].status, int(False))

        total_supply = self._query(query_request)
        self.assertEqual(total_supply, 1000 * 10 ** 18)

    def test_missing_parameters_onupdate(self):
        # deploy
        tx1 = self._make_deploy_tx("test_deploy_scores/install",
                                   "sample_token",
                                   self._addr_array[0],
                                   ZERO_SCORE_ADDRESS, deploy_params={"init_supply": hex(1000), "decimal": "0x12"})

        tx2 = self._make_deploy_tx("test_deploy_scores/install",
                                   "sample_token",
                                   self._addr_array[0],
                                   ZERO_SCORE_ADDRESS, deploy_params={"init_supply": hex(1000), "decimal": "0x12"})

        tx3 = self._make_deploy_tx("test_deploy_scores/install",
                                   "sample_token",
                                   self._addr_array[0],
                                   ZERO_SCORE_ADDRESS, deploy_params={"init_supply": hex(1000), "decimal": "0x12"})

        prev_block, tx_results = self._make_and_req_block([tx1, tx2, tx3])
        self._write_precommit_state(prev_block)

        self.assertEqual(tx_results[0].status, int(True))
        self.assertEqual(tx_results[1].status, int(True))
        self.assertEqual(tx_results[2].status, int(True))

        score_addr1 = tx_results[0].score_address
        score_addr2 = tx_results[1].score_address
        score_addr3 = tx_results[2].score_address

        query_request = {
            "from": self._admin,
            "to": score_addr1,
            "dataType": "call",
            "data": {
                "method": "total_supply",
            }
        }

        total_supply = self._query(query_request)
        self.assertEqual(total_supply, 1000 * 10 ** 18)

        query_request['to'] = score_addr2
        total_supply = self._query(query_request)
        self.assertEqual(total_supply, 1000 * 10 ** 18)

        query_request['to'] = score_addr3
        total_supply = self._query(query_request)
        self.assertEqual(total_supply, 1000 * 10 ** 18)

        tx1 = self._make_deploy_tx("test_deploy_scores/install", "sample_token", self._addr_array[0],
                                   score_addr1, deploy_params={"decimal": "0x12"})
        tx2 = self._make_deploy_tx("test_deploy_scores/install", "sample_token", self._addr_array[0],
                                   score_addr2, deploy_params={"update_supply": hex(1000)})
        tx3 = self._make_deploy_tx("test_deploy_scores/install", "sample_token", self._addr_array[0],
                                   score_addr3, deploy_params={})

        prev_block, tx_results = self._make_and_req_block([tx1, tx2, tx3])

        self._write_precommit_state(prev_block)

        self.assertEqual(tx_results[0].failure.code, 32000)
        self.assertEqual(tx_results[1].failure.code, 32000)
        self.assertEqual(tx_results[2].failure.code, 32000)

        self.assertTrue(tx_results[0].failure.message.find("on_update() missing 1 required positional argument:") != -1)
        self.assertTrue(tx_results[1].failure.message.find("on_update() missing 1 required positional argument:") != -1)
        self.assertTrue(
            tx_results[2].failure.message.find("on_update() missing 2 required positional arguments:") != -1)

        self.assertEqual(tx_results[0].status, int(False))
        self.assertEqual(tx_results[1].status, int(False))
        self.assertEqual(tx_results[2].status, int(False))

        query_request['to'] = score_addr1
        total_supply = self._query(query_request)
        self.assertEqual(total_supply, 1000 * 10 ** 18)

        query_request['to'] = score_addr2
        total_supply = self._query(query_request)
        self.assertEqual(total_supply, 1000 * 10 ** 18)

        query_request['to'] = score_addr3
        total_supply = self._query(query_request)
        self.assertEqual(total_supply, 1000 * 10 ** 18)

    def test_invalid_paramter_value_onupdate(self):
        tx1 = self._make_deploy_tx("test_deploy_scores/install", "sample_token", self._addr_array[0],
                                   ZERO_SCORE_ADDRESS, deploy_params={"init_supply": hex(1000), "decimal": "0x12"})

        tx2 = self._make_deploy_tx("test_deploy_scores/install", "sample_token", self._addr_array[0],
                                   ZERO_SCORE_ADDRESS, deploy_params={"init_supply": hex(1000), "decimal": "0x12"})

        prev_block, tx_results = self._make_and_req_block([tx1, tx2])
        self._write_precommit_state(prev_block)

        self.assertEqual(tx_results[0].status, int(True))
        self.assertEqual(tx_results[1].status, int(True))

        score_addr1 = tx_results[0].score_address
        score_addr2 = tx_results[1].score_address

        query_request = {
            "from": self._admin,
            "to": score_addr1,
            "dataType": "call",
            "data": {
                "method": "total_supply",
            }
        }

        total_supply = self._query(query_request)
        self.assertEqual(total_supply, 1000 * 10 ** 18)

        query_request['to'] = score_addr2
        total_supply = self._query(query_request)
        self.assertEqual(total_supply, 1000 * 10 ** 18)

        tx1 = self._make_deploy_tx("test_deploy_scores/install", "sample_token", self._addr_array[0],
                                   score_addr1, deploy_params={"update_supply": str(self._addr_array[0]),
                                                               "decimal": "0x12"})

        tx2 = self._make_deploy_tx("test_deploy_scores/install", "sample_token", self._addr_array[0],
                                   score_addr2, deploy_params={"update_supply": hex(2000), "decimal": "0x12",
                                                               "address_param": "0x12"})

        prev_block, tx_results = self._make_and_req_block([tx1, tx2])

        self._write_precommit_state(prev_block)

        self.assertEqual(tx_results[0].failure.code, 32000)
        self.assertEqual(tx_results[1].failure.code, 32602)

        self.assertTrue(tx_results[0].failure.message.find("invalid literal for int()") != -1)
        self.assertTrue(tx_results[1].failure.message.find("Invalid address") != -1)

        self.assertEqual(tx_results[0].status, int(False))
        self.assertEqual(tx_results[1].status, int(False))

        query_request['to'] = score_addr1
        total_supply = self._query(query_request)
        self.assertEqual(total_supply, 1000 * 10 ** 18)

        query_request['to'] = score_addr2
        total_supply = self._query(query_request)
        self.assertEqual(total_supply, 1000 * 10 ** 18)
