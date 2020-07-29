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

from copy import deepcopy
from math import ceil
from typing import TYPE_CHECKING, Any, List

from iconservice.base.address import SYSTEM_SCORE_ADDRESS, GOVERNANCE_SCORE_ADDRESS
from iconservice.icon_constant import ICX_IN_LOOP
from tests.integrate_test.test_integrate_base import TestIntegrateBase, DEFAULT_BIG_STEP_LIMIT

if TYPE_CHECKING:
    from iconservice.iconscore.icon_score_result import TransactionResult
    from iconservice.base.address import Address


class TestIntegrateEstimateStep(TestIntegrateBase):

    @staticmethod
    def _make_tx_for_estimating_step_from_origin_tx(tx: dict) -> dict:
        tx = deepcopy(tx)
        tx["method"] = "debug_estimateStep"
        del tx["params"]["nonce"]
        del tx["params"]["stepLimit"]
        del tx["params"]["timestamp"]
        del tx["params"]["txHash"]
        del tx["params"]["signature"]
        return tx

    def _assert_get_score_status(self, target_addr: 'Address', expect_status: dict):
        query_request = {
            "version": self._version,
            "from": self._accounts[0],
            "to": GOVERNANCE_SCORE_ADDRESS,
            "dataType": "call",
            "data": {
                "method": "getScoreStatus",
                "params": {"address": str(target_addr)}
            }
        }
        response = self._query(query_request)
        self.assertEqual(response, expect_status)

    def _assert_get_value(self, from_addr: 'Address', score_addr: 'Address', func_name: str, value: Any):
        query_request = {
            "version": self._version,
            "from": from_addr,
            "to": score_addr,
            "dataType": "call",
            "data": {
                "method": func_name,
                "params": {}
            }
        }
        response = self._query(query_request)
        self.assertEqual(response, value)

    def _query_step_costs(self):
        query_request = {
            "version": self._version,
            "from": self._accounts[0],
            "to": GOVERNANCE_SCORE_ADDRESS,
            "dataType": "call",
            "data": {
                "method": "getStepCosts",
                "params": {}
            }
        }
        return self._query(query_request)

    @staticmethod
    def _get_expected_step_count(step_costs, input_size, content_size):
        return step_costs['default'] + \
               step_costs['input'] * input_size + \
               step_costs['contractSet'] * content_size + \
               step_costs['contractCreate']

    @staticmethod
    def _get_str_size(data):
        return len(data.encode('utf-8'))

    @staticmethod
    def _get_bin_size(data):
        index_of_hex_body = 2 if data[:2] == '0x' else 3 if data[:3] == '-0x' else 0
        return ceil(len(data[index_of_hex_body:]) / 2)

    def test_estimate_step_when_transfer_coin_to_eoa(self):
        value1 = 3 * ICX_IN_LOOP
        tx: dict = self.create_transfer_icx_tx(from_=self._admin,
                                               to_=self._accounts[0],
                                               value=value1)

        prev_block, hash_list = self.make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        tx_results: List['TransactionResult'] = self.get_tx_results(hash_list)
        self.assertEqual(tx_results[0].status, int(True))

        # Compares estimate to the real step_used
        converted_tx = self._make_tx_for_estimating_step_from_origin_tx(tx)
        estimate = self.icon_service_engine.estimate_step(request=converted_tx)
        self.assertEqual(estimate, tx_results[0].step_used)

        value2 = 2 * ICX_IN_LOOP
        tx: dict = self.create_transfer_icx_tx(from_=self._accounts[0],
                                               to_=self._accounts[1],
                                               value=value2)

        prev_block, hash_list = self.make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        tx_results: List['TransactionResult'] = self.get_tx_results(hash_list)
        self.assertEqual(tx_results[0].status, int(True))

        # Compares estimate to the real step_used
        converted_tx = self._make_tx_for_estimating_step_from_origin_tx(tx)
        estimate = self.icon_service_engine.estimate_step(request=converted_tx)
        self.assertEqual(estimate, tx_results[0].step_used)

    def test_estimate_step_when_transfer_coin_to_score(self):
        tx = self.create_deploy_score_tx(score_root="sample_fallback_call_scores",
                                         score_name="sample_score_pass",
                                         from_=self._accounts[0],
                                         to_=SYSTEM_SCORE_ADDRESS)
        prev_block, hash_list = self.make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        tx_results: List['TransactionResult'] = self.get_tx_results(hash_list)
        self.assertEqual(tx_results[0].status, int(True))
        score_addr1 = tx_results[0].score_address

        # Compares estimate to the real step_used
        converted_tx = self._make_tx_for_estimating_step_from_origin_tx(tx)
        estimate = self.icon_service_engine.estimate_step(request=converted_tx)
        self.assertEqual(estimate, tx_results[0].step_used)

        value = 1 * ICX_IN_LOOP
        tx = self.create_transfer_icx_tx(from_=self._admin,
                                         to_=score_addr1,
                                         value=value,
                                         step_limit=DEFAULT_BIG_STEP_LIMIT)
        prev_block, hash_list = self.make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        tx_results: List['TransactionResult'] = self.get_tx_results(hash_list)

        # Compares estimate to the real step_used
        converted_tx = self._make_tx_for_estimating_step_from_origin_tx(tx)
        estimate = self.icon_service_engine.estimate_step(request=converted_tx)
        self.assertEqual(estimate, tx_results[0].step_used)

        query_request = {
            "address": score_addr1
        }

        response = self._query(query_request, 'icx_getBalance')
        self.assertEqual(response, value)

        # Compares estimate to the real step_used
        converted_tx = self._make_tx_for_estimating_step_from_origin_tx(tx)
        estimate = self.icon_service_engine.estimate_step(request=converted_tx)
        self.assertEqual(estimate, tx_results[0].step_used)

    def test_estimate_step_when_transfer_coin_to_score_2(self):
        tx_results: List['TransactionResult'] = self.deploy_score(score_root="sample_fallback_call_scores",
                                                                  score_name="sample_score_to_eoa",
                                                                  from_=self._accounts[0],
                                                                  to_=SYSTEM_SCORE_ADDRESS)
        score_addr1 = tx_results[0].score_address

        self.score_call(from_=self._accounts[0],
                        to_=score_addr1,
                        func_name="set_addr_func",
                        params={"addr": str(self._accounts[1].address)})

        value = 1 * ICX_IN_LOOP
        tx = self.create_transfer_icx_tx(from_=self._admin,
                                         to_=score_addr1,
                                         value=value)
        prev_block, hash_list = self.make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        tx_results: List['TransactionResult'] = self.get_tx_results(hash_list)
        self.assertEqual(tx_results[0].status, int(True))

        response: int = self.get_balance(self._accounts[1])
        self.assertEqual(response, value)

        # Compares estimate to the real step_used
        converted_tx = self._make_tx_for_estimating_step_from_origin_tx(tx)
        estimate = self.icon_service_engine.estimate_step(request=converted_tx)
        self.assertEqual(estimate, tx_results[0].step_used)

    def test_estimate_step_when_call_score_function(self):
        value1 = 1 * ICX_IN_LOOP
        tx_results: List['TransactionResult'] = self.deploy_score(score_root="sample_deploy_scores",
                                                                  score_name="install/sample_score",
                                                                  from_=self._accounts[0],
                                                                  deploy_params={"value": hex(value1)})
        score_addr1 = tx_results[0].score_address

        value2 = 2 * ICX_IN_LOOP
        tx = self.create_score_call_tx(from_=self._accounts[0],
                                       to_=score_addr1,
                                       func_name="set_value",
                                       params={"value": hex(value2)})
        prev_block, hash_list = self.make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        tx_results: List['TransactionResult'] = self.get_tx_results(hash_list)
        self.assertEqual(tx_results[0].status, int(True))

        # Compares estimate to the real step_used
        converted_tx = self._make_tx_for_estimating_step_from_origin_tx(tx)
        estimate = self.icon_service_engine.estimate_step(request=converted_tx)
        self.assertEqual(tx_results[0].step_used, estimate)

    def test_estimate_step_when_install_score(self):
        tx = self.create_deploy_score_tx(score_root="get_api",
                                         score_name="get_api1",
                                         from_=self._accounts[0],
                                         to_=SYSTEM_SCORE_ADDRESS)
        prev_block, hash_list = self.make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        tx_results: List['TransactionResult'] = self.get_tx_results(hash_list)
        self.assertEqual(tx_results[0].status, int(True))

        # Compares estimate to the real step_used
        converted_tx = self._make_tx_for_estimating_step_from_origin_tx(tx)
        estimate = self.icon_service_engine.estimate_step(request=converted_tx)
        self.assertEqual(tx_results[0].step_used, estimate)

    def test_estimate_step_when_update_score(self):
        tx = self.create_deploy_score_tx(score_root="get_api",
                                         score_name="get_api1",
                                         from_=self._accounts[0],
                                         to_=SYSTEM_SCORE_ADDRESS)
        prev_block, hash_list = self.make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        tx_results: List['TransactionResult'] = self.get_tx_results(hash_list)
        self.assertEqual(tx_results[0].status, int(True))
        score_addr = tx_results[0].score_address

        tx = self.create_deploy_score_tx(score_root="get_api",
                                         score_name="get_api1_update",
                                         from_=self._accounts[0],
                                         to_=score_addr)
        prev_block, hash_list = self.make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        tx_results: List['TransactionResult'] = self.get_tx_results(hash_list)
        self.assertEqual(tx_results[0].status, int(True))

        # Compares estimate to the real step_used
        converted_tx = self._make_tx_for_estimating_step_from_origin_tx(tx)
        estimate = self.icon_service_engine.estimate_step(request=converted_tx)
        self.assertEqual(tx_results[0].step_used, estimate)

    def test_estimate_step_when_transfer_message_without_sending_coin_to_eoa(self):
        tx = self.create_message_tx(from_=self._accounts[1],
                                    to_=self._accounts[0],
                                    data=b'testtesttesttesttesttesttest')
        converted_tx = self._make_tx_for_estimating_step_from_origin_tx(tx)
        estimate = self.icon_service_engine.estimate_step(request=converted_tx)

        # Compares estimate to the real step_used
        prev_block, hash_list = self.make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        tx_results: List['TransactionResult'] = self.get_tx_results(hash_list)
        self.assertEqual(tx_results[0].status, int(True))
        self.assertEqual(estimate, tx_results[0].step_used)

    def test_estimate_step_when_transfer_message_without_sending_coin_to_score(self):
        value1 = 1 * ICX_IN_LOOP
        tx_results: List['TransactionResult'] = self.deploy_score(score_root="sample_deploy_scores",
                                                                  score_name="install/sample_score",
                                                                  from_=self._accounts[0],
                                                                  to_=SYSTEM_SCORE_ADDRESS,
                                                                  deploy_params={"value": hex(value1)})
        score_addr1 = tx_results[0].score_address

        tx = self.create_message_tx(from_=self._admin,
                                    to_=score_addr1,
                                    data=b'testtesttesttesttesttesttest')
        converted_tx = self._make_tx_for_estimating_step_from_origin_tx(tx)
        estimate = self.icon_service_engine.estimate_step(request=converted_tx)

        # Compares estimate to the real step_used
        prev_block, hash_list = self.make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        tx_results: List['TransactionResult'] = self.get_tx_results(hash_list)
        self.assertEqual(tx_results[0].status, int(True))
        self.assertEqual(estimate, tx_results[0].step_used)

    def test_estimate_step_when_transfer_message_with_sending_coin_to_eoa(self):
        tx = self.create_message_tx(from_=self._admin,
                                    to_=self._accounts[0],
                                    data=b'testtesttesttesttesttesttest',
                                    value=1_000_000)
        converted_tx = self._make_tx_for_estimating_step_from_origin_tx(tx)
        estimate = self.icon_service_engine.estimate_step(request=converted_tx)

        # Compares estimate to the real step_used
        prev_block, hash_list = self.make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        tx_results: List['TransactionResult'] = self.get_tx_results(hash_list)
        self.assertEqual(tx_results[0].status, int(True))
        self.assertEqual(estimate, tx_results[0].step_used)

    def test_estimate_step_when_transfer_message_with_sending_coin_to_score(self):
        tx_results: List['TransactionResult'] = self.deploy_score(score_root="sample_fallback_call_scores",
                                                                  score_name="sample_score_pass",
                                                                  from_=self._accounts[0],
                                                                  to_=SYSTEM_SCORE_ADDRESS)
        score_addr1 = tx_results[0].score_address

        tx = self.create_message_tx(from_=self._admin,
                                    to_=score_addr1,
                                    data=b'testtesttesttesttesttesttest',
                                    value=1_000_000)
        converted_tx = self._make_tx_for_estimating_step_from_origin_tx(tx)
        estimate = self.icon_service_engine.estimate_step(request=converted_tx)

        # Compares estimate to the real step_used
        prev_block, hash_list = self.make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        tx_results: List['TransactionResult'] = self.get_tx_results(hash_list)
        self.assertEqual(tx_results[0].status, int(True))
        self.assertEqual(estimate, tx_results[0].step_used)

    def test_minus_step(self):
        tx_results: List['TransactionResult'] = self.deploy_score(score_root="sample_scores",
                                                                  score_name="minus_step",
                                                                  from_=self._accounts[0],
                                                                  to_=SYSTEM_SCORE_ADDRESS)
        score_addr1 = tx_results[0].score_address

        tx = self.create_score_call_tx(from_=self._accounts[0],
                                       to_=score_addr1,
                                       func_name="func",
                                       params={})

        converted_tx = self._make_tx_for_estimating_step_from_origin_tx(tx)
        estimate = self.icon_service_engine.estimate_step(request=converted_tx)

        # step * input_length = used_step
        # used_step * count = total_step
        # 150 * 9 = 1_350
        # 1350 * 100 = 135_000
        minus_step: int = 135_000
        # Compares estimate to the real step_used
        prev_block, hash_list = self.make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        tx_results: List['TransactionResult'] = self.get_tx_results(hash_list)
        self.assertEqual(tx_results[0].status, int(True))
        self.assertEqual(estimate - minus_step, tx_results[0].step_used)

    def test_migration_input_step(self):
        self.update_governance("0_0_4")

        step_costs = self._query_step_costs()

        key_content_type = 'contentType'
        key_content = 'content'
        key_data_params = 'params'
        content_type = 'application/zip'
        content = '0xabcde12345'

        data_param_keys = [
            'upper_case_hex',
            'lower_case_hex',
            'no_prefix_hex',
            'korean',
            'negative_integer'
        ]

        data_param_values = [
            '0xabcDe12345',
            '0xabcde12345',
            'abcde12345',
            '한국어',
            '-0x1a2b3c'
        ]

        request = self._generate_mock_request(
            key_content, content,
            key_content_type, content_type,
            key_data_params,
            data_param_keys, data_param_values)

        estimated_steps = self.icon_service_engine.estimate_step(request)

        content_size = self._get_bin_size(content)

        input_size_rev2 = \
            self._get_str_size(content_type) + \
            self._get_bin_size(content) + \
            self._get_str_size(data_param_values[0]) + \
            self._get_bin_size(data_param_values[1]) + \
            self._get_bin_size(data_param_values[2]) + \
            self._get_str_size(data_param_values[3]) + \
            self._get_str_size(data_param_values[4])

        expected_steps = self._get_expected_step_count(step_costs, input_size_rev2, content_size)
        self.assertEqual(expected_steps, estimated_steps)

        # Update revision
        self.set_revision(3)

        estimated_steps = self.icon_service_engine.estimate_step(request)

        input_size_rev3 = len(
            '{'
            f'"{key_content_type}":"{content_type}",'
            f'"{key_content}":"{content}",'
            f'"{key_data_params}":'
            '{'
            f'"{data_param_keys[0]}":"{data_param_values[0]}",'
            f'"{data_param_keys[1]}":"{data_param_values[1]}",'
            f'"{data_param_keys[2]}":"{data_param_values[2]}",'
            f'"{data_param_keys[3]}":"{data_param_values[3]}",'
            f'"{data_param_keys[4]}":"{data_param_values[4]}"'
            '}'
            '}'.encode())

        expected_steps = self._get_expected_step_count(step_costs, input_size_rev3, content_size)
        self.assertEqual(expected_steps, estimated_steps)

    def _generate_mock_request(self,
                               key_content, content,
                               key_content_type, content_type,
                               key_data_params,
                               data_param_keys, data_param_values):
        return {
            'method': 'icx_sendTransaction',
            'params': {
                'version': 3,
                'from': self._genesis,
                'to': SYSTEM_SCORE_ADDRESS,
                'stepLimit': 1_000_000_000_000,
                'timestamp': 1541753667870296,
                'nonce': 0,
                'dataType': 'deploy',
                'data': {
                    key_content_type: content_type,
                    key_content: content,
                    key_data_params: {
                        data_param_keys[0]: data_param_values[0],
                        data_param_keys[1]: data_param_values[1],
                        data_param_keys[2]: data_param_values[2],
                        data_param_keys[3]: data_param_values[3],
                        data_param_keys[4]: data_param_values[4]
                    }
                }
            }
        }
