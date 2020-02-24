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
from typing import TYPE_CHECKING, List

from iconservice import Address
from iconservice.base.exception import InvalidParamsException, ExceptionCode
from iconservice.icon_constant import ICX_IN_LOOP
from tests.integrate_test.test_integrate_base import TestIntegrateBase

if TYPE_CHECKING:
    from iconservice.iconscore.icon_score_result import TransactionResult


class TestIntegrateMethodParamters(TestIntegrateBase):

    def init_deploy_sample_token(self, init_supply: int, decimal: int) -> 'Address':
        tx_results: List['TransactionResult'] = self.deploy_score(
            score_root="sample_deploy_scores",
            score_name="install/sample_token",
            from_=self._accounts[0],
            deploy_params={"init_supply": hex(init_supply), "decimal": hex(decimal)})
        return tx_results[0].score_address

    def test_parameters_success_cases(self):
        init_supply: int = 1000
        decimal: int = 18
        score_address: 'Address' = self.init_deploy_sample_token(init_supply, decimal)

        # balance_of test
        query_request = {
            "from": self._admin,
            "to": score_address,
            "dataType": "call",
            "data": {
                "method": "balance_of",
                "params": {
                    "addr_from": str(self._accounts[0].address)
                }
            }
        }
        response = self._query(query_request)
        init_balance: int = init_supply * ICX_IN_LOOP
        self.assertEqual(response, init_balance)

        # transfer test
        value = 100 * ICX_IN_LOOP
        self.score_call(from_=self._accounts[0],
                        to_=score_address,
                        func_name="transfer",
                        params={"addr_to": str(self._accounts[1].address), "value": hex(value)})

        # balance_of test
        query_request = {
            "from": self._admin,
            "to": score_address,
            "dataType": "call",
            "data": {
                "method": "balance_of",
                "params": {
                    "addr_from": str(self._accounts[0].address)
                }
            }
        }
        response = self._query(query_request)
        self.assertEqual(response, init_balance - value)

        query_request = {
            "from": self._admin,
            "to": score_address,
            "dataType": "call",
            "data": {
                "method": "balance_of",
                "params": {
                    "addr_from": str(self._accounts[1].address)
                }
            }
        }
        response = self._query(query_request)
        self.assertEqual(response, value)

    def test_more_parameters_query(self):
        init_supply: int = 1000
        decimal: int = 18
        score_address: 'Address' = self.init_deploy_sample_token(init_supply, decimal)

        # balance_of test
        query_request = {
            "from": self._admin,
            "to": score_address,
            "dataType": "call",
            "data": {
                "method": "balance_of",
                "params": {
                    "addr_from": str(self._accounts[0].address),
                    "more_param": hex(1)
                }
            }
        }
        self.assertRaises(InvalidParamsException, self._query, query_request)

    def test_less_parameters_query(self):
        init_supply: int = 1000
        decimal: int = 18
        score_address: 'Address' = self.init_deploy_sample_token(init_supply, decimal)

        # balance_of test
        query_request = {
            "from": self._admin,
            "to": score_address,
            "dataType": "call",
            "data": {
                "method": "balance_of",
                "params": {}
            }
        }

        self.assertRaises(TypeError, self._query, query_request)

    def test_invalid_paramter_value_query(self):
        init_supply: int = 1000
        decimal: int = 18
        score_address: 'Address' = self.init_deploy_sample_token(init_supply, decimal)

        # balance_of test
        query_request = {
            "from": self._admin,
            "to": score_address,
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
        init_supply: int = 1000
        decimal: int = 18
        score_address: 'Address' = self.init_deploy_sample_token(init_supply, decimal)

        # balance_of test
        query_request = {
            "from": self._admin,
            "to": score_address,
            "dataType": "call",
            "data": {
                "method": "balance_of",
                "params": {
                    "addr_from": str(self._accounts[0])[:20]
                }
            }
        }

        self.assertRaises(InvalidParamsException, self._query, query_request)

    def test_more_parameters_invoke(self):
        init_supply: int = 1000
        decimal: int = 18
        score_address: 'Address' = self.init_deploy_sample_token(init_supply, decimal)

        # transfer test
        init_balance: int = init_supply * ICX_IN_LOOP
        value = 100 * ICX_IN_LOOP
        tx_results: List['TransactionResult'] = self.score_call(from_=self._accounts[0],
                                                                to_=score_address,
                                                                func_name="transfer",
                                                                params={"addr_to": str(self._accounts[1].address),
                                                                        "value": hex(value),
                                                                        "additional_param": hex(1)},
                                                                expected_status=False)
        self.assertEqual(tx_results[0].failure.code, ExceptionCode.INVALID_PARAMETER)

        query_request = {
            "from": self._admin,
            "to": score_address,
            "dataType": "call",
            "data": {
                "method": "balance_of",
                "params": {
                    "addr_from": str(self._accounts[0].address)
                }
            }
        }
        response = self._query(query_request)
        self.assertEqual(response, init_balance)

    def test_less_parameters_invoke(self):
        init_supply: int = 1000
        decimal: int = 18
        score_address: 'Address' = self.init_deploy_sample_token(init_supply, decimal)

        # transfer test
        init_balance: int = init_supply * ICX_IN_LOOP
        value = 100 * ICX_IN_LOOP
        tx_results: List['TransactionResult'] = self.score_call(from_=self._accounts[0],
                                                                to_=score_address,
                                                                func_name="transfer",
                                                                params={"value": hex(value)},
                                                                expected_status=False)
        self.assertEqual(tx_results[0].failure.code, ExceptionCode.SYSTEM_ERROR)
        self.assertTrue(tx_results[0].failure.message.find("missing 1 required positional argument") != -1)

        query_request = {
            "from": self._admin,
            "to": score_address,
            "dataType": "call",
            "data": {
                "method": "balance_of",
                "params": {
                    "addr_from": str(self._accounts[0].address)
                }
            }
        }
        response = self._query(query_request)
        self.assertEqual(response, init_balance)

    def test_invalid_paramters_invoke(self):
        init_supply: int = 1000
        decimal: int = 18
        score_address: 'Address' = self.init_deploy_sample_token(init_supply, decimal)

        # transfer test
        init_balance: int = init_supply * ICX_IN_LOOP
        tx_results: List['TransactionResult'] = self.score_call(from_=self._accounts[0],
                                                                to_=score_address,
                                                                func_name="transfer",
                                                                params={"addr_to": str(self._accounts[1].address),
                                                                        "value": str(self._accounts[0].address)},
                                                                expected_status=False)
        self.assertEqual(tx_results[0].failure.code, ExceptionCode.SYSTEM_ERROR)
        self.assertTrue(tx_results[0].failure.message.find("invalid literal for int()") != -1)

        # check balance
        query_request = {
            "from": self._admin,
            "to": score_address,
            "dataType": "call",
            "data": {
                "method": "balance_of",
                "params": {
                    "addr_from": str(self._accounts[0].address)
                }
            }
        }
        response = self._query(query_request)
        self.assertEqual(response, init_balance)

    def test_invalid_address_invoke(self):
        init_supply: int = 1000
        decimal: int = 18
        score_address: 'Address' = self.init_deploy_sample_token(init_supply, decimal)

        # transfer test
        init_balance: int = init_supply * ICX_IN_LOOP
        tx_results: List['TransactionResult'] = self.score_call(
            from_=self._accounts[0],
            to_=score_address,
            func_name="transfer",
            params={"addr_to": str(self._accounts[1].address)[:20],
                    "value": str(self._accounts[0].address)},
            expected_status=False)
        self.assertEqual(tx_results[0].failure.code, ExceptionCode.INVALID_PARAMETER)

        # check balance
        query_request = {
            "from": self._admin,
            "to": score_address,
            "dataType": "call",
            "data": {
                "method": "balance_of",
                "params": {
                    "addr_from": str(self._accounts[0].address)
                }
            }
        }
        response = self._query(query_request)
        self.assertEqual(response, init_balance)

    def test_default_parameters(self):
        tx_results: List['TransactionResult'] = self.deploy_score(
            score_root="sample_scores",
            score_name="sample_db_returns_default_value",
            from_=self._accounts[0],
            deploy_params={})
        score_address: 'Address' = tx_results[0].score_address

        val1 = 3
        val2 = "string"
        val3 = b'bytestring'
        val4 = Address.from_string(f"hx{'0' * 40}")
        val5 = False
        val6 = Address.from_string(f"hx{'abcd1234' * 5}")

        query_request = {
            "from": self._admin,
            "to": score_address,
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
        tx_results: List['TransactionResult'] = self.deploy_score(
            score_root="sample_scores",
            score_name="sample_db_returns",
            from_=self._accounts[0],
            deploy_params={"value": str(self._accounts[1].address),
                           "value1": str(self._accounts[1].address)})
        score_address: 'Address' = tx_results[0].score_address

        query_request = {
            "from": self._admin,
            "to": score_address,
            "dataType": "call",
            "data": {
                "method": "get_value1",
                "params": {}
            }
        }
        response = self._query(query_request)
        self.assertEqual(response, 0)

        value = 1 * ICX_IN_LOOP
        self.score_call(
            from_=self._accounts[0],
            to_=score_address,
            func_name="set_value1",
            params={"value": hex(value)})

        response = self._query(query_request)
        self.assertEqual(response, value)

        query_request['data']['method'] = "get_value2"
        response = self._query(query_request)
        self.assertEqual(response, "")

        value = "a"
        self.score_call(
            from_=self._accounts[0],
            to_=score_address,
            func_name="set_value2",
            params={"value": value})

        response = self._query(query_request)
        self.assertEqual(response, value)

        query_request['data']['method'] = "get_value3"
        response = self._query(query_request)
        self.assertEqual(response, None)

        value = self._prev_block_hash
        self.score_call(
            from_=self._accounts[0],
            to_=score_address,
            func_name="set_value3",
            params={"value": bytes.hex(value)})

        response = self._query(query_request)
        self.assertEqual(response, value)

        query_request['data']['method'] = "get_value4"
        response = self._query(query_request)
        self.assertEqual(response, self._accounts[1].address)

        value = self._genesis
        self.score_call(
            from_=self._accounts[0],
            to_=score_address,
            func_name="set_value4",
            params={"value": str(value)})

        response = self._query(query_request)
        self.assertEqual(response, value)

        query_request['data']['method'] = "get_value5"
        response = self._query(query_request)
        self.assertEqual(response, False)

        value = True
        self.score_call(
            from_=self._accounts[0],
            to_=score_address,
            func_name="set_value5",
            params={"value": hex(int(value))})

        response = self._query(query_request)
        self.assertEqual(response, value)

        query_request['data']['method'] = "get_value6"
        response = self._query(query_request)
        self.assertEqual(response, self._accounts[1].address)

        value = self._genesis
        self.score_call(
            from_=self._accounts[0],
            to_=score_address,
            func_name="set_value6",
            params={"value": str(value)})

        response = self._query(query_request)
        self.assertEqual(response, value)

        # test if dict type param can be passed
        value = {"a": 123}
        self.score_call(
            from_=self._accounts[0],
            to_=score_address,
            func_name="set_value6",
            params={"value": str(value)},
            expected_status=False)

    # test for empty parameter invoke method
    def test_empty_parameter_invoke(self):
        tx_results: List['TransactionResult'] = self.deploy_score(
            score_root="sample_deploy_scores",
            score_name="install/sample_score",
            from_=self._accounts[0],
            deploy_params={"value": hex(1000)})
        score_address: 'Address' = tx_results[0].score_address

        query_request = {
            "from": self._admin,
            "to": score_address,
            "dataType": "call",
            "data": {
                "method": "get_value",
                "params": {}
            }
        }
        response = self._query(query_request)
        self.assertEqual(response, 1000)

        self.score_call(
            from_=self._accounts[0],
            to_=score_address,
            func_name="set_value",
            params={"value": hex(18)})

        response = self._query(query_request)
        self.assertEqual(response, 18)

        # token test
        init_supply: int = 1000
        decimal: int = 18
        tx_results: List['TransactionResult'] = self.deploy_score(
            score_root="sample_deploy_scores",
            score_name="install/sample_token",
            from_=self._accounts[0],
            deploy_params={"init_supply": hex(init_supply), "decimal": hex(decimal)})
        score_address: 'Address' = tx_results[0].score_address

        query_request = {
            "from": self._admin,
            "to": score_address,
            "dataType": "call",
            "data": {
                "method": "total_supply",
                "params": {}
            }
        }
        response = self._query(query_request)
        self.assertEqual(response, init_supply * 10 ** decimal)
        self.score_call(
            from_=self._accounts[0],
            to_=score_address,
            func_name="mint",
            params={})

        response = self._query(query_request)
        self.assertEqual(response, init_supply * 10 ** decimal + 1)

    # unsupported parameter type testcase
    # def test_kwargs_parameter_method(self):
    #     tx_results: List['TransactionResult'] = self.deploy_score(
    #         score_root="sample_deploy_scores",
    #         score_name="install/sample_kwargs_score",
    #         from_=self._accounts[0],
    #         deploy_params={"value": str(self._accounts[1].address),
    #                        "value1": str(self._accounts[1].address)},
    #         expected_status=False)
    #     self.assertEqual(tx_results[0].failure.code, ExceptionCode.ILLEGAL_FORMAT)
    #
    # unsupported parameter type testcase
    # def test_list_parameters_query(self):
    #     # deploy
    #     tx_results: List['TransactionResult'] = self.deploy_score(
    #         score_root="sample_deploy_scores",
    #         score_name="install/sample_list_params_score",
    #         from_=self._accounts[0],
    #         deploy_params={"init_supply": hex(1000), "decimal": "0x12"},
    #         expected_status=False)
    #
    #     self.assertEqual(tx_results[0].failure.code, ExceptionCode.ILLEGAL_FORMAT)
    #     self.assertTrue(tx_results[0].failure.message.find("Unsupported type for 'list_param: <class 'list'>'") != -1)
    #
    # def test_dict_parameters_query(self):
    #     # deploy
    #     tx_results: List['TransactionResult'] = self.deploy_score(
    #         score_root="sample_deploy_scores",
    #         score_name="install/sample_dict_params_score",
    #         from_=self._accounts[0],
    #         deploy_params={"init_supply": hex(1000), "decimal": "0x12"},
    #         expected_status=False)
    #
    #     self.assertEqual(tx_results[0].failure.code, ExceptionCode.ILLEGAL_FORMAT)
    #     self.assertTrue(tx_results[0].failure.message.find("Unsupported type for 'dict_param: <class 'dict'>'") != -1)
