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

"""score method parameters testcase"""

from iconservice import ZERO_SCORE_ADDRESS, Address
from iconservice.base.exception import InvalidParamsException
from tests.integrate_test.test_integrate_base import TestIntegrateBase


class TestIntegrateMethodParamters(TestIntegrateBase):

    def test_parameters_success_cases(self):
        # deploy
        tx1 = self._make_deploy_tx("test_deploy_scores/install",
                                   "sample_token",
                                   self._addr_array[0],
                                   ZERO_SCORE_ADDRESS, deploy_params={"init_supply": hex(1000), "decimal": "0x12"})

        prev_block, tx_results = self._make_and_req_block([tx1])

        self._write_precommit_state(prev_block)

        self.assertEqual(tx_results[0].status, int(True))
        score_addr1 = tx_results[0].score_address

        # balance_of test
        query_request = {
            "from": self._admin,
            "to": score_addr1,
            "dataType": "call",
            "data": {
                "method": "balance_of",
                "params": {
                    "addr_from": str(self._addr_array[0])
                }
            }
        }
        response = self._query(query_request)
        self.assertEqual(response, 1000 * 10 ** 18)

        # transfer test
        tx2 = self._make_score_call_tx(self._addr_array[0],
                                       score_addr1,
                                       'transfer',
                                       {"addr_to": str(self._addr_array[1]), "value": hex(100 * 10 ** 18)})

        prev_block, tx_results = self._make_and_req_block([tx2])

        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))

        # balance_of test
        query_request = {
            "from": self._admin,
            "to": score_addr1,
            "dataType": "call",
            "data": {
                "method": "balance_of",
                "params": {
                    "addr_from": str(self._addr_array[0])
                }
            }
        }
        response = self._query(query_request)
        self.assertEqual(response, 900 * 10 ** 18)

        query_request['data']['params']['addr_from'] = str(self._addr_array[1])
        response = self._query(query_request)
        self.assertEqual(response, 100 * 10 ** 18)

    def test_more_parameters_query(self):
        tx1 = self._make_deploy_tx("test_deploy_scores/install", "sample_token", self._addr_array[0],
                                   ZERO_SCORE_ADDRESS, deploy_params={"init_supply": hex(1000), "decimal": "0x12"})

        prev_block, tx_results = self._make_and_req_block([tx1])

        self._write_precommit_state(prev_block)

        self.assertEqual(tx_results[0].status, int(True))
        score_addr1 = tx_results[0].score_address

        # balance_of test
        query_request = {
            "from": self._admin,
            "to": score_addr1,
            "dataType": "call",
            "data": {
                "method": "balance_of",
                "params": {
                    "addr_from": str(self._addr_array[0]),
                    "more_param": hex(1)
                }
            }
        }

        self.assertRaises(TypeError, self._query, query_request)

    def test_less_parameters_query(self):
        tx1 = self._make_deploy_tx("test_deploy_scores/install", "sample_token", self._addr_array[0],
                                   ZERO_SCORE_ADDRESS, deploy_params={"init_supply": hex(1000), "decimal": "0x12"})

        prev_block, tx_results = self._make_and_req_block([tx1])

        self._write_precommit_state(prev_block)

        score_addr1 = tx_results[0].score_address

        # balance_of test
        query_request = {
            "from": self._admin,
            "to": score_addr1,
            "dataType": "call",
            "data": {
                "method": "balance_of",
                "params": {}
            }
        }

        self.assertRaises(TypeError, self._query, query_request)

    def test_invalid_paramter_value_query(self):
        tx1 = self._make_deploy_tx("test_deploy_scores/install", "sample_token", self._addr_array[0],
                                   ZERO_SCORE_ADDRESS, deploy_params={"init_supply": hex(1000), "decimal": "0x12"})

        prev_block, tx_results = self._make_and_req_block([tx1])

        self._write_precommit_state(prev_block)

        score_addr1 = tx_results[0].score_address

        # balance_of test
        query_request = {
            "from": self._admin,
            "to": score_addr1,
            "dataType": "call",
            "data": {
                "method": "balance_of",
                "params": {
                    "addr_from": hex(1)
                }
            }
        }

        self.assertRaises(InvalidParamsException, self._query, query_request)

    def test_invalid_address_query(self):
        tx1 = self._make_deploy_tx("test_deploy_scores/install", "sample_token", self._addr_array[0],
                                   ZERO_SCORE_ADDRESS, deploy_params={"init_supply": hex(1000), "decimal": "0x12"})

        prev_block, tx_results = self._make_and_req_block([tx1])

        self._write_precommit_state(prev_block)

        score_addr1 = tx_results[0].score_address

        # balance_of test
        query_request = {
            "from": self._admin,
            "to": score_addr1,
            "dataType": "call",
            "data": {
                "method": "balance_of",
                "params": {
                    "addr_from": str(self._addr_array[0])[:20]
                }
            }
        }

        self.assertRaises(InvalidParamsException, self._query, query_request)

    def test_more_parameters_invoke(self):
        tx1 = self._make_deploy_tx("test_deploy_scores/install", "sample_token", self._addr_array[0],
                                   ZERO_SCORE_ADDRESS, deploy_params={"init_supply": hex(1000), "decimal": "0x12"})

        prev_block, tx_results = self._make_and_req_block([tx1])

        self._write_precommit_state(prev_block)

        score_addr1 = tx_results[0].score_address

        # transfer test
        tx2 = self._make_score_call_tx(self._addr_array[0],
                                       score_addr1,
                                       'transfer',
                                       {"addr_to": str(self._addr_array[1]), "value": hex(100 * 10 ** 18),
                                        "additional_param": hex(1)})

        prev_block, tx_results = self._make_and_req_block([tx2])

        self.assertEqual(tx_results[0].failure.code, 32000)
        self.assertTrue(tx_results[0].failure.message.find("got an unexpected keyword argument") != -1)

        query_request = {
            "from": self._admin,
            "to": score_addr1,
            "dataType": "call",
            "data": {
                "method": "balance_of",
                "params": {
                    "addr_from": str(self._addr_array[0])
                }
            }
        }
        response = self._query(query_request)
        self.assertEqual(response, 1000 * 10 ** 18)

    def test_less_parameters_invoke(self):
        tx1 = self._make_deploy_tx("test_deploy_scores/install", "sample_token", self._addr_array[0],
                                   ZERO_SCORE_ADDRESS, deploy_params={"init_supply": hex(1000), "decimal": "0x12"})

        prev_block, tx_results = self._make_and_req_block([tx1])

        self._write_precommit_state(prev_block)

        score_addr1 = tx_results[0].score_address

        # transfer test
        tx2 = self._make_score_call_tx(self._addr_array[0],
                                       score_addr1,
                                       'transfer',
                                       {"value": hex(100 * 10 ** 18)})

        prev_block, tx_results = self._make_and_req_block([tx2])

        self.assertEqual(tx_results[0].failure.code, 32000)
        self.assertTrue(tx_results[0].failure.message.find("missing 1 required positional argument") != -1)

        query_request = {
            "from": self._admin,
            "to": score_addr1,
            "dataType": "call",
            "data": {
                "method": "balance_of",
                "params": {
                    "addr_from": str(self._addr_array[0])
                }
            }
        }
        response = self._query(query_request)
        self.assertEqual(response, 1000 * 10 ** 18)

    def test_invalid_paramters_invoke(self):
        tx1 = self._make_deploy_tx("test_deploy_scores/install", "sample_token", self._addr_array[0],
                                   ZERO_SCORE_ADDRESS, deploy_params={"init_supply": hex(1000), "decimal": "0x12"})

        prev_block, tx_results = self._make_and_req_block([tx1])

        self._write_precommit_state(prev_block)

        score_addr1 = tx_results[0].score_address

        # transfer test
        tx1 = self._make_score_call_tx(self._addr_array[0],
                                       score_addr1,
                                       'transfer',
                                       {"addr_to": str(self._addr_array[1]), "value": str(self._addr_array[0])})

        prev_block, tx_results = self._make_and_req_block([tx1])

        self.assertEqual(tx_results[0].failure.code, 32000)
        self.assertTrue(tx_results[0].failure.message.find("invalid literal for int()") != -1)

        # check balance
        query_request = {
            "from": self._admin,
            "to": score_addr1,
            "dataType": "call",
            "data": {
                "method": "balance_of",
                "params": {
                    "addr_from": str(self._addr_array[0])
                }
            }
        }
        response = self._query(query_request)
        self.assertEqual(response, 1000 * 10 ** 18)

    def test_invalid_address_invoke(self):
        tx1 = self._make_deploy_tx("test_deploy_scores/install", "sample_token", self._addr_array[0],
                                   ZERO_SCORE_ADDRESS, deploy_params={"init_supply": hex(1000), "decimal": "0x12"})

        prev_block, tx_results = self._make_and_req_block([tx1])

        self._write_precommit_state(prev_block)

        score_addr1 = tx_results[0].score_address

        # transfer test
        tx2 = self._make_score_call_tx(self._addr_array[0],
                                       score_addr1,
                                       'transfer',
                                       {"addr_to": str(self._addr_array[1])[:20], "value": str(self._addr_array[0])})

        prev_block, tx_results = self._make_and_req_block([tx2])

        self.assertEqual(tx_results[0].failure.code, 32602)

        # check balance
        query_request = {
            "from": self._admin,
            "to": score_addr1,
            "dataType": "call",
            "data": {
                "method": "balance_of",
                "params": {
                    "addr_from": str(self._addr_array[0])
                }
            }
        }
        response = self._query(query_request)
        self.assertEqual(response, 1000 * 10 ** 18)

    def test_default_parameters(self):
        tx1 = self._make_deploy_tx("test_scores", "test_db_returns_default_value", self._addr_array[0],
                                   ZERO_SCORE_ADDRESS,
                                   deploy_params={})
        prev_block, tx_results = self._make_and_req_block([tx1])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))
        score_addr1 = tx_results[0].score_address

        val1 = 3
        val2 = "string"
        val3 = b'bytestring'
        val4 = Address.from_string(f"hx{'0'*40}")
        val5 = False
        val6 = Address.from_string(f"hx{'abcd1234'*5}")

        query_request = {
            "from": self._admin,
            "to": score_addr1,
            "dataType": "call",
            "data": {
                "method": "get_value1",
                "params": {}
            }
        }
        response = self._query(query_request)
        self.assertEqual(response, val1)

        query_request['data']['method'] = 'get_value2'
        response = self._query(query_request)
        self.assertEqual(response, val2)

        query_request['data']['method'] = 'get_value3'
        response = self._query(query_request)
        self.assertEqual(response, val3)

        query_request['data']['method'] = 'get_value4'
        response = self._query(query_request)
        self.assertEqual(response, val4)

        query_request['data']['method'] = 'get_value5'
        response = self._query(query_request)
        self.assertEqual(response, val5)

        query_request['data']['method'] = 'get_value6'
        response = self._query(query_request)
        self.assertEqual(response, val6)

    def test_primitive_type_parameters_methods(self):
        tx1 = self._make_deploy_tx("test_scores", "test_db_returns", self._addr_array[0], ZERO_SCORE_ADDRESS,
                                   deploy_params={"value": str(self._addr_array[1]),
                                                  "value1": str(self._addr_array[1])})

        prev_block, tx_results = self._make_and_req_block([tx1])

        self._write_precommit_state(prev_block)

        self.assertEqual(tx_results[0].status, int(True))
        score_addr1 = tx_results[0].score_address

        query_request = {
            "from": self._admin,
            "to": score_addr1,
            "dataType": "call",
            "data": {
                "method": "get_value1",
                "params": {}
            }
        }
        response = self._query(query_request)
        self.assertEqual(response, 0)

        value = 1 * self._icx_factor
        tx2 = self._make_score_call_tx(self._addr_array[0], score_addr1, 'set_value1', {"value": hex(value)})

        prev_block, tx_results = self._make_and_req_block([tx2])

        self._write_precommit_state(prev_block)

        self.assertEqual(tx_results[0].status, int(True))

        response = self._query(query_request)
        self.assertEqual(response, value)

        query_request['data']['method'] = "get_value2"
        response = self._query(query_request)
        self.assertEqual(response, "")

        value = "a"
        tx3 = self._make_score_call_tx(self._addr_array[0], score_addr1, 'set_value2', {"value": value})

        prev_block, tx_results = self._make_and_req_block([tx3])

        self._write_precommit_state(prev_block)

        self.assertEqual(tx_results[0].status, int(True))

        response = self._query(query_request)
        self.assertEqual(response, value)

        query_request['data']['method'] = "get_value3"
        response = self._query(query_request)
        self.assertEqual(response, None)

        value = self._prev_block_hash
        tx4 = self._make_score_call_tx(self._addr_array[0], score_addr1, 'set_value3', {"value": bytes.hex(value)})

        prev_block, tx_results = self._make_and_req_block([tx4])

        self._write_precommit_state(prev_block)

        self.assertEqual(tx_results[0].status, int(True))

        response = self._query(query_request)
        self.assertEqual(response, value)

        query_request['data']['method'] = "get_value4"
        response = self._query(query_request)
        self.assertEqual(response, self._addr_array[1])

        value = self._genesis
        tx5 = self._make_score_call_tx(self._addr_array[0], score_addr1, 'set_value4', {"value": str(value)})

        prev_block, tx_results = self._make_and_req_block([tx5])

        self._write_precommit_state(prev_block)

        self.assertEqual(tx_results[0].status, int(True))

        response = self._query(query_request)
        self.assertEqual(response, value)

        query_request['data']['method'] = "get_value5"
        response = self._query(query_request)
        self.assertEqual(response, False)

        value = True
        tx6 = self._make_score_call_tx(self._addr_array[0], score_addr1, 'set_value5', {"value": hex(int(value))})

        prev_block, tx_results = self._make_and_req_block([tx6])

        self._write_precommit_state(prev_block)

        self.assertEqual(tx_results[0].status, int(True))

        response = self._query(query_request)
        self.assertEqual(response, value)

        query_request['data']['method'] = "get_value6"
        response = self._query(query_request)
        self.assertEqual(response, self._addr_array[1])

        value = self._genesis
        tx7 = self._make_score_call_tx(self._addr_array[0], score_addr1, 'set_value6', {"value": str(value)})

        prev_block, tx_results = self._make_and_req_block([tx7])

        self._write_precommit_state(prev_block)

        self.assertEqual(tx_results[0].status, int(True))

        response = self._query(query_request)
        self.assertEqual(response, value)

        # test if dict type param can be passed
        value = {"a": 123}
        tx8 = self._make_score_call_tx(self._addr_array[0], score_addr1, 'set_value6', {"value": str(value)})

        prev_block, tx_results = self._make_and_req_block([tx8])

        self._write_precommit_state(prev_block)

        self.assertEqual(tx_results[0].status, int(False))

    # test for empty parameter invoke method
    def test_empty_parameter_invoke(self):
        tx1 = self._make_deploy_tx("test_deploy_scores/install", "test_score", self._addr_array[0], ZERO_SCORE_ADDRESS)
        prev_block, tx_results = self._make_and_req_block([tx1])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))
        score_addr1 = tx_results[0].score_address
        query_request = {
            "from": self._admin,
            "to": score_addr1,
            "dataType": "call",
            "data": {
                "method": "get_value",
                "params": {}
            }
        }
        response = self._query(query_request)
        self.assertEqual(response, 1000)

        tx2 = self._make_score_call_tx(self._addr_array[0], score_addr1, 'set_value', params={"value": "0x12"})
        prev_block, tx_results = self._make_and_req_block([tx2])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))
        response = self._query(query_request)
        self.assertEqual(response, 18)

        # token test
        tx1 = self._make_deploy_tx("test_deploy_scores/install", "sample_token", self._addr_array[0],
                                   ZERO_SCORE_ADDRESS,
                                   deploy_params={"init_supply": hex(1000), "decimal": "0x12"})
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
                "params": {}
            }
        }
        response = self._query(query_request)
        self.assertEqual(response, 10 ** 21)
        tx2 = self._make_score_call_tx(self._addr_array[0], score_addr1, 'mint', params={})
        prev_block, tx_results = self._make_and_req_block([tx2])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))
        response = self._query(query_request)
        self.assertEqual(response, 10 ** 21 + 1)

    # unsupported parameter type testcase
    def test_kwargs_parameter_method(self):
        tx1 = self._make_deploy_tx("test_deploy_scores/install", "test_kwargs_score", self._addr_array[0],
                                   ZERO_SCORE_ADDRESS, deploy_params={"value": str(self._addr_array[1]),
                                                                      "value1": str(self._addr_array[1])})
        prev_block, tx_results = self._make_and_req_block([tx1])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(False))

    # unsupported parameter type testcase
    def test_list_parameters_query(self):
        # deploy
        tx1 = self._make_deploy_tx("test_deploy_scores/install", "test_list_params_score", self._addr_array[0],
                                   ZERO_SCORE_ADDRESS, deploy_params={"init_supply": hex(1000), "decimal": "0x12"})
        prev_block, tx_results = self._make_and_req_block([tx1])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(False))
        self.assertEqual(tx_results[0].failure.code, 32000)
        self.assertTrue(tx_results[0].failure.message.find("'Unsupported type for 'list_param: <class 'list'>'") != -1)

    def test_dict_parameters_query(self):
        # deploy
        tx1 = self._make_deploy_tx("test_deploy_scores/install", "test_dict_params_score", self._addr_array[0],
                                   ZERO_SCORE_ADDRESS, deploy_params={"init_supply": hex(1000), "decimal": "0x12"})

        prev_block, tx_results = self._make_and_req_block([tx1])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(False))
        self.assertEqual(tx_results[0].failure.code, 32000)
        self.assertTrue(tx_results[0].failure.message.find("'Unsupported type for 'dict_param: <class 'dict'>'") != -1)
