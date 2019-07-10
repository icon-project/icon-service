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
from math import ceil

from iconservice.icon_constant import ICX_IN_LOOP
from tests.integrate_test.test_integrate_base import TestIntegrateBase
from iconservice.base.address import ZERO_SCORE_ADDRESS, GOVERNANCE_SCORE_ADDRESS
from tests.integrate_test import create_timestamp
from tests import create_tx_hash

from typing import TYPE_CHECKING, Any, Union
from copy import deepcopy

if TYPE_CHECKING:
    from iconservice.base.address import Address


class TestIntegrateEstimateStep(TestIntegrateBase):

    def _make_message_tx(self,
                         addr_from: Union['Address', None],
                         addr_to: 'Address',
                         data: bytes = None,
                         value: int = 0):
        timestamp_us = create_timestamp()
        nonce = 0

        request_params = {
            "version": self._version,
            "from": addr_from,
            "to": addr_to,
            "value": value,
            "stepLimit": self._step_limit,
            "timestamp": timestamp_us,
            "nonce": nonce,
            "signature": self._signature,
            "dataType": "message",
            "data": '0x' + data.hex(),
        }

        method = 'icx_sendTransaction'
        # Inserts txHash into request params
        request_params['txHash'] = create_tx_hash()
        tx = {
            'method': method,
            'params': request_params
        }

        self.icon_service_engine.validate_transaction(tx)
        return tx

    @staticmethod
    def _make_tx_for_estimating_step_from_origin_tx(tx: dict):
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
            "from": self._addr_array[0],
            "to": GOVERNANCE_SCORE_ADDRESS,
            "dataType": "call",
            "data": {
                "method": "getScoreStatus",
                "params": {"address": str(target_addr)}
            }
        }
        response = self._query(query_request)
        self.assertEqual(response, expect_status)

    def _deploy_score(self, score_path: str,
                      value: int,
                      from_addr: 'Address',
                      update_score_addr: 'Address' = None) -> Any:
        address = ZERO_SCORE_ADDRESS
        if update_score_addr:
            address = update_score_addr

        tx = self._make_deploy_tx("sample_deploy_scores",
                                  score_path,
                                  from_addr,
                                  address,
                                  deploy_params={'value': hex(value)})

        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        return tx_results[0]

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

    def _set_value(self, from_addr: 'Address', score_addr: 'Address', func_name: str, params: dict):
        tx = self._make_score_call_tx(from_addr,
                                      score_addr,
                                      func_name,
                                      params)
        prev_block, tx_results = self._make_and_req_block([tx])
        self.assertEqual(tx_results[0].status, int(True))
        self._write_precommit_state(prev_block)

    def test_score(self):
        # 1. deploy
        value1 = 1 * ICX_IN_LOOP
        tx_result = self._deploy_score("install/sample_score", value1, self._addr_array[0])
        self.assertEqual(tx_result.status, int(True))
        score_addr1 = tx_result.score_address

        # 2. assert get value: value1
        self._assert_get_value(self._addr_array[0], score_addr1, "get_value", value1)

        # 3. set value: value2
        value2 = 2 * ICX_IN_LOOP
        self._set_value(self._addr_array[0], score_addr1, "set_value", {"value": hex(value2)})

        # 4. assert get value: 2 * value2
        self._assert_get_value(self._addr_array[0], score_addr1, "get_value", value2)

        expect_ret = {}
        self._assert_get_score_status(score_addr1, expect_ret)

    def test_estimate_step_when_transfer_coin_to_eoa(self):
        value1 = 3 * ICX_IN_LOOP
        tx1 = self._make_icx_send_tx(self._genesis, self._addr_array[0], value1)

        prev_block, tx_results = self._make_and_req_block([tx1])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))

        # Compares estimate to the real step_used
        converted_tx = self._make_tx_for_estimating_step_from_origin_tx(tx1)
        estimate = self.icon_service_engine.estimate_step(request=converted_tx)
        self.assertEqual(estimate, tx_results[0].step_used)

        value2 = 2 * ICX_IN_LOOP
        tx2 = self._make_icx_send_tx(self._addr_array[0], self._addr_array[1], value2)

        prev_block, tx_results = self._make_and_req_block([tx2])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))

        # Compares estimate to the real step_used
        converted_tx = self._make_tx_for_estimating_step_from_origin_tx(tx2)
        estimate = self.icon_service_engine.estimate_step(request=converted_tx)
        self.assertEqual(estimate, tx_results[0].step_used)

    def test_estimate_step_when_transfer_coin_to_score(self):
        tx1 = self._make_deploy_tx("sample_fallback_call_scores",
                                   "sample_score_pass",
                                   self._addr_array[0],
                                   ZERO_SCORE_ADDRESS)
        prev_block, tx_results = self._make_and_req_block([tx1])
        self._write_precommit_state(prev_block)

        self.assertEqual(tx_results[0].status, int(True))
        score_addr1 = tx_results[0].score_address

        # Compares estimate to the real step_used
        converted_tx = self._make_tx_for_estimating_step_from_origin_tx(tx1)
        estimate = self.icon_service_engine.estimate_step(request=converted_tx)
        self.assertEqual(estimate, tx_results[0].step_used)

        value = 1 * ICX_IN_LOOP
        tx2 = self._make_icx_send_tx(self._genesis, score_addr1, value)
        prev_block, tx_results = self._make_and_req_block([tx2])
        self._write_precommit_state(prev_block)

        # Compares estimate to the real step_used
        converted_tx = self._make_tx_for_estimating_step_from_origin_tx(tx2)
        estimate = self.icon_service_engine.estimate_step(request=converted_tx)
        self.assertEqual(estimate, tx_results[0].step_used)

        query_request = {
            "address": score_addr1
        }

        response = self._query(query_request, 'icx_getBalance')
        self.assertEqual(response, value)

        # Compares estimate to the real step_used
        converted_tx = self._make_tx_for_estimating_step_from_origin_tx(tx2)
        estimate = self.icon_service_engine.estimate_step(request=converted_tx)
        self.assertEqual(estimate, tx_results[0].step_used)

    def test_estimate_step_when_transfer_coin_to_score_2(self):
        tx1 = self._make_deploy_tx("sample_fallback_call_scores",
                                   "sample_score_to_eoa",
                                   self._addr_array[0],
                                   ZERO_SCORE_ADDRESS)
        prev_block, tx_results = self._make_and_req_block([tx1])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))
        score_addr1 = tx_results[0].score_address

        tx2 = self._make_score_call_tx(self._addr_array[0],
                                       score_addr1,
                                       'set_addr_func',
                                       {"addr": str(self._addr_array[1])})

        prev_block, tx_results = self._make_and_req_block([tx2])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))

        value = 1 * ICX_IN_LOOP
        tx3 = self._make_icx_send_tx(self._genesis, score_addr1, value)
        prev_block, tx_results = self._make_and_req_block([tx3])
        self._write_precommit_state(prev_block)

        query_request = {
            "address": self._addr_array[1]
        }
        response = self._query(query_request, 'icx_getBalance')
        self.assertEqual(response, value)

        # Compares estimate to the real step_used
        converted_tx = self._make_tx_for_estimating_step_from_origin_tx(tx3)
        estimate = self.icon_service_engine.estimate_step(request=converted_tx)
        self.assertEqual(estimate, tx_results[0].step_used)

    def test_estimate_step_when_call_score_function(self):
        value1 = 1 * ICX_IN_LOOP
        tx_result = self._deploy_score("install/sample_score", value1, self._addr_array[0])
        self.assertEqual(tx_result.status, int(True))
        score_addr1 = tx_result.score_address

        value2 = 2 * ICX_IN_LOOP
        tx1 = self._make_score_call_tx(addr_from=self._addr_array[0], addr_to=score_addr1, method="set_value",
                                                     params={"value": hex(value2)})
        prev_block, tx_results = self._make_and_req_block([tx1])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))

        # Compares estimate to the real step_used
        converted_tx = self._make_tx_for_estimating_step_from_origin_tx(tx1)
        estimate = self.icon_service_engine.estimate_step(request=converted_tx)
        self.assertEqual(tx_results[0].step_used, estimate)

    def test_estimate_step_when_install_score(self):
        tx1 = self._make_deploy_tx("get_api", "get_api1", self._addr_array[0], ZERO_SCORE_ADDRESS)
        prev_block, tx_results = self._make_and_req_block([tx1])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))

        # Compares estimate to the real step_used
        converted_tx = self._make_tx_for_estimating_step_from_origin_tx(tx1)
        estimate = self.icon_service_engine.estimate_step(request=converted_tx)
        self.assertEqual(tx_results[0].step_used, estimate)

    def test_estimate_step_when_update_score(self):
        tx1 = self._make_deploy_tx("get_api", "get_api1", self._addr_array[0], ZERO_SCORE_ADDRESS)
        prev_block, tx_results = self._make_and_req_block([tx1])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))
        score_addr = tx_results[0].score_address

        tx1 = self._make_deploy_tx("get_api", "get_api1_update", self._addr_array[0], score_addr)
        prev_block, tx_results = self._make_and_req_block([tx1])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))

        # Compares estimate to the real step_used
        converted_tx = self._make_tx_for_estimating_step_from_origin_tx(tx1)
        estimate = self.icon_service_engine.estimate_step(request=converted_tx)
        self.assertEqual(tx_results[0].step_used, estimate)

    def test_estimate_step_when_transfer_message_without_sending_coin_to_eoa(self):
        tx1 = self._make_message_tx(addr_to=self._addr_array[0],
                                    addr_from=self._addr_array[1],
                                    data=b'testtesttesttesttesttesttest')
        converted_tx = self._make_tx_for_estimating_step_from_origin_tx(tx1)
        estimate = self.icon_service_engine.estimate_step(request=converted_tx)

        # Compares estimate to the real step_used
        prev_block, tx_results = self._make_and_req_block([tx1])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))
        self.assertEqual(estimate, tx_results[0].step_used)

    def test_estimate_step_when_transfer_message_without_sending_coin_to_score(self):
        value1 = 1 * ICX_IN_LOOP
        tx_result = self._deploy_score("install/sample_score", value1, self._addr_array[0])
        self.assertEqual(tx_result.status, int(True))
        score_addr1 = tx_result.score_address

        tx1 = self._make_message_tx(addr_to=score_addr1,
                                    addr_from=self._genesis,
                                    data=b'testtesttesttesttesttesttest')
        converted_tx = self._make_tx_for_estimating_step_from_origin_tx(tx1)
        estimate = self.icon_service_engine.estimate_step(request=converted_tx)

        # Compares estimate to the real step_used
        prev_block, tx_results = self._make_and_req_block([tx1])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))
        self.assertEqual(estimate, tx_results[0].step_used)

    def test_estimate_step_when_transfer_message_with_sending_coin_to_eoa(self):
        tx1 = self._make_message_tx(addr_to=self._addr_array[0],
                                    addr_from=self._genesis,
                                    data=b'testtesttesttesttesttesttest',
                                    value=1000000)
        converted_tx = self._make_tx_for_estimating_step_from_origin_tx(tx1)
        estimate = self.icon_service_engine.estimate_step(request=converted_tx)

        # Compares estimate to the real step_used
        prev_block, tx_results = self._make_and_req_block([tx1])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))
        self.assertEqual(estimate, tx_results[0].step_used)

    def test_estimate_step_when_transfer_message_with_sending_coin_to_score(self):
        tx1 = self._make_deploy_tx("sample_fallback_call_scores",
                                   "sample_score_pass",
                                   self._addr_array[0],
                                   ZERO_SCORE_ADDRESS)
        prev_block, tx_results = self._make_and_req_block([tx1])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))
        score_addr1 = tx_results[0].score_address

        tx1 = self._make_message_tx(addr_to=score_addr1,
                                    addr_from=self._genesis,
                                    data=b'testtesttesttesttesttesttest',
                                    value=1000000)
        converted_tx = self._make_tx_for_estimating_step_from_origin_tx(tx1)
        estimate = self.icon_service_engine.estimate_step(request=converted_tx)

        # Compares estimate to the real step_used
        prev_block, tx_results = self._make_and_req_block([tx1])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))
        self.assertEqual(estimate, tx_results[0].step_used)

    def test_migration_input_step(self):
        self._update_governance_0_0_4()
        self.assertEqual(2, self._query_revision())

        step_costs = self._query_step_costs()

        key_content_type = 'contentType'
        key_content = 'content'
        key_data_params = 'params'
        content_type = 'application/zip'
        content = '0xabcde12345'

        data_param_keys = ['upper_case_hex',
                           'lower_case_hex',
                           'no_prefix_hex',
                           'korean',
                           'negative_integer']

        data_param_values = ['0xabcDe12345',
                             '0xabcde12345',
                             'abcde12345',
                             '한국어',
                             '-0x1a2b3c']

        request = self.generate_mock_request(
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
        prev_block, tx_results = self._make_and_req_block([
            self._make_score_call_tx(
                self._admin,
                GOVERNANCE_SCORE_ADDRESS,
                'setRevision',
                {"code": hex(3), "name": "1.1.1"},
            )
        ])
        self._write_precommit_state(prev_block)
        self.assertEqual(3, self._query_revision())

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

    def generate_mock_request(self,
                              key_content, content,
                              key_content_type, content_type,
                              key_data_params,
                              data_param_keys, data_param_values):
        return {
            'method': 'icx_sendTransaction',
            'params': {
                'version': 3,
                'from': self._genesis,
                'to': ZERO_SCORE_ADDRESS,
                'stepLimit': 1000000000000,
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

    def _update_governance_0_0_4(self):
        tx = self._make_deploy_tx("sample_builtin",
                                  "0_0_4/governance",
                                  self._admin,
                                  GOVERNANCE_SCORE_ADDRESS)
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))

    def _query_revision(self):
        query_request = {
            "version": self._version,
            "from": self._addr_array[0],
            "to": GOVERNANCE_SCORE_ADDRESS,
            "dataType": "call",
            "data": {
                "method": "getRevision",
                "params": {}
            }
        }
        return self._query(query_request)['code']

    def _query_step_costs(self):
        query_request = {
            "version": self._version,
            "from": self._addr_array[0],
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
