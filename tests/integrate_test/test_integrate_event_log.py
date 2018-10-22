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

from typing import TYPE_CHECKING, Any

from iconservice.base.address import ZERO_SCORE_ADDRESS, GOVERNANCE_SCORE_ADDRESS
from tests.integrate_test.test_integrate_base import TestIntegrateBase

if TYPE_CHECKING:
    from iconservice.base.address import Address


class TestIntegrateEventLog(TestIntegrateBase):
    def setUp(self):
        super().setUp()
        self._update_governance()

    def _update_governance(self):
        tx = self._make_deploy_tx("test_builtin",
                                  "0_0_6/governance",
                                  self._admin,
                                  GOVERNANCE_SCORE_ADDRESS)
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)

    def _deploy_score(self, score_path: str, update_score_addr: 'Address' = None) -> Any:
        address = ZERO_SCORE_ADDRESS
        if update_score_addr:
            address = update_score_addr

        tx = self._make_deploy_tx("test_event_log_scores",
                                  score_path,
                                  self._addr_array[0],
                                  address,
                                  deploy_params={})

        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        return tx_results[0]

    def _query_score(self, target_addr: 'Address', method: str, params: dict=None):
        query_request = {
            "version": self._version,
            "from": self._addr_array[0],
            "to": target_addr,
            "dataType": "call",
            "data": {
                "method": method,
                "params": {} if params is None else params
            }
        }
        return self._query(query_request)

    def _call_score(self, score_addr: 'Address', method: str, params: dict):
        tx = self._make_score_call_tx(self._addr_array[0],
                                      score_addr,
                                      method,
                                      params)

        prev_block, tx_results = self._make_and_req_block([tx])

        self._write_precommit_state(prev_block)

        return tx_results

    def test_valid_event_log(self):
        tx_result = self._deploy_score("test_event_log_score")
        self.assertEqual(tx_result.status, int(True))
        score_addr = tx_result.score_address

        # success case: call valid event log and check log data
        # event log which defined parameter's number is zero also treat as valid event log
        method_params = {"value1": "test1", "value2": "test2", "value3": "test3"}
        tx_results = self._call_score(score_addr, "call_valid_event_log", method_params)
        self.assertEqual(tx_results[0].status, int(True))

        # indexed params and non_indexed params should be separately stored in txresult(indexed, data)
        event_log = tx_results[0].event_logs[0]
        self.assertEqual(event_log.indexed[0], "NormalEventLog(str,str,str)")
        self.assertEqual(event_log.indexed[1], "test1")
        self.assertEqual(event_log.indexed[2], "test2")
        self.assertEqual(event_log.data[0], "test3")

        # success case: call valid event log with None
        # event log which defined parameter's number is zero also treat as valid event log
        tx_results = self._call_score(score_addr, "call_valid_event_log_with_none", {})
        self.assertEqual(tx_results[0].status, int(True))

        # indexed params and non_indexed params should be separately stored in txresult(indexed, data)
        event_log = tx_results[0].event_logs[0]
        self.assertEqual(event_log.indexed[0], "NormalEventLog(str,str,str)")
        self.assertEqual(event_log.indexed[1], None)
        self.assertEqual(event_log.indexed[2], None)
        self.assertEqual(event_log.data[0], None)

        # success case: event log which params are not defined also treat as valid event log
        tx_results = self._call_score(score_addr, "call_event_log_params_are_not_defined", {})
        self.assertEqual(tx_results[0].status, int(True))

        event_log = tx_results[0].event_logs[0]
        self.assertEqual(event_log.data, [])
        self.assertEqual(event_log.indexed[0], "EventLogWithOutParams()")

        # success case: input keyword arguments to event log
        method_params = {"value1": "positional1", "value2": "keyword2", "value3": "keyword3"}
        tx_results = self._call_score(score_addr, "call_valid_event_log_keyword", method_params)
        self.assertEqual(tx_results[0].status, int(True))
        event_log = tx_results[0].event_logs[0]
        self.assertEqual(event_log.indexed[0], "NormalEventLog(str,str,str)")
        self.assertEqual(event_log.indexed[1], "positional1")
        self.assertEqual(event_log.indexed[2], "keyword2")
        self.assertEqual(event_log.data[0], "keyword3")

        # success case: call event log which's parameters are set default value
        tx_results = self._call_score(score_addr, "call_valid_event_log_with_default", {"value1": "non_default"})
        self.assertEqual(tx_results[0].status, int(True))
        event_log = tx_results[0].event_logs[0]
        self.assertEqual(event_log.indexed[0], "NormalEventLogWithDefault(str,str,str)")
        self.assertEqual(event_log.indexed[1], "non_default")
        self.assertEqual(event_log.indexed[2], "default2")
        self.assertEqual(event_log.data[0], "default3")

        # success case: input empty string("") and empty bytes(b'') as event log's parameter
        tx_results = self._call_score(score_addr,
                                      "call_event_log_input_empty_bytes_and_string_data",
                                      {})
        self.assertEqual(tx_results[0].status, int(True))
        event_log = tx_results[0].event_logs[0]
        self.assertEqual(event_log.data[0], "")
        self.assertEqual(event_log.data[1], b'')

    def test_call_event_log_in_read_only_method(self):
        # failure case: if call event log on read_only method, should raise error
        tx_result = self._deploy_score("test_event_log_score")
        self.assertEqual(int(True), tx_result.status)
        score_address: 'Address' = tx_result.score_address

        tx_results = self._call_score(score_address, "call_even_log_in_read_only_method", {})
        self.assertEqual(1, len(tx_results))

        tx_result: 'TransactionResult' = tx_results[0]
        self.assertEqual(int(False), tx_result.status)
        self.assertEqual("The event log can not be recorded on readonly context", tx_result.failure.message)
        self.assertEqual(0, len(tx_result.event_logs))

    def test_event_log_self_is_not_defined(self):
        # failure case: event log which self is not defined treat as invalid event log
        tx_result = self._deploy_score("test_self_is_not_defined_event_log_score")
        self.assertEqual(tx_result.status, int(False))
        self.assertEqual(tx_result.failure.message, "define 'self' as the first parameter in the event log")

    def test_event_log_when_error(self):
        tx_result = self._deploy_score("test_event_log_score")
        self.assertEqual(tx_result.status, int(True))
        score_addr = tx_result.score_address

        # failure case: the case of raising an error when call event log, the state should be revert
        tx_results = self._call_score(score_addr, "call_event_log_raising_error", {})
        self.assertEqual(tx_results[0].status, int(False))

        expected = "default"
        actual = self._query_score(score_addr, "get_value")
        self.assertEqual(expected, actual)

    def test_event_log_having_body(self):
        tx_result = self._deploy_score("test_event_log_score")
        self.assertEqual(tx_result.status, int(True))
        score_addr = tx_result.score_address

        # success case: even though the event log has body, body should be ignored
        tx_results = self._call_score(score_addr, "call_event_log_having_body", {})
        self.assertEqual(tx_results[0].status, int(True))

        expected = "default"
        actual = self._query_score(score_addr, "get_value")
        self.assertEqual(expected, actual)

    def test_event_log_index_on_deploy(self):
        tx_result = self._deploy_score("test_event_log_score")
        self.assertEqual(tx_result.status, int(True))
        score_addr = tx_result.score_address

        # success case: set index under 0(index number should be treated as 0)
        tx_results = self._call_score(score_addr, "call_event_log_index_under_zero", {})
        self.assertEqual(tx_results[0].status, int(True))
        event_log = tx_results[0].event_logs[0]

        # params should be stored in data list
        self.assertEqual(event_log.data[0], "test")
        # index length should be 1(including event log method name)
        self.assertEqual(len(event_log.indexed), 1)

        # failure case: setting index more than 4(should raise an error)
        tx_result = self._deploy_score("test_exceed_max_index_event_log_score")
        self.assertEqual(tx_result.status, int(False))
        self.assertEqual(tx_result.failure.message, "indexed arguments are overflow: limit=3")

        # failure case: setting index more than event log's parameter total count(should raise an error)
        tx_result = self._deploy_score("test_index_exceed_params_event_log_score")
        self.assertEqual(tx_result.status, int(False))
        self.assertEqual(tx_result.failure.message, "index exceeds the number of parameters")

    def test_event_log_index_on_execute(self):
        pass

    def test_event_log_parameters_on_deploy(self):
        # failure case: define dict type parameter
        tx_result = self._deploy_score("test_invalid_params_type_event_log_score_dict")
        self.assertEqual(tx_result.failure.message, "Unsupported type for 'value: <class 'dict'>'")

        # failure case: define list type parameter
        tx_result = self._deploy_score("test_invalid_params_type_event_log_score_array")
        self.assertEqual(tx_result.failure.message, "Unsupported type for 'value: <class 'list'>'")

        # failure case: omit type hint
        tx_result = self._deploy_score("test_invalid_params_type_hint_event_log_score")
        self.assertEqual(tx_result.failure.message, "Missing argument hint for 'EventLogInvalidParamsType': 'value'")

    def test_event_log_parameters_on_execute(self):
        tx_result = self._deploy_score("test_event_log_score")
        self.assertEqual(tx_result.status, int(True))
        score_addr = tx_result.score_address

        # failure case: input less parameter to event log(raise error)
        tx_results = self._call_score(score_addr, "call_event_log_input_less_number_of_params", {})
        self.assertEqual(tx_results[0].status, int(False))

        # failure case: input exceed parameter to event log(raise error)
        tx_results = self._call_score(score_addr, "call_event_log_input_exceed_number_of_params", {})
        self.assertEqual(tx_results[0].status, int(False))

        tx_results = self._call_score(score_addr, "call_event_log_input_exceed_number_of_params2", {})
        self.assertEqual(tx_results[0].status, int(False))

        # failure case: input non-matching type parameter to event log(raise error)
        type_list = ["integer", "string", "boolean", "bytes", "address"]

        # case1: defined parameter=integer
        for params_type in type_list:
            if params_type == "integer" or params_type == "boolean":
                continue
            tx_params = {"test_type": "integer", "input_params_type": params_type}
            tx_results = self._call_score(score_addr, "call_event_log_for_checking_params_type", tx_params)
            self.assertEqual(tx_results[0].status, int(False))

        # case2: defined parameter=string
        for params_type in type_list:
            if params_type == "string":
                continue
            tx_params = {"test_type": "string", "input_params_type": params_type}
            tx_results = self._call_score(score_addr, "call_event_log_for_checking_params_type", tx_params)
            self.assertEqual(tx_results[0].status, int(False))

        # case3: defined parameter=boolean
        for params_type in type_list:
            if params_type == "boolean":
                continue
            tx_params = {"test_type": "boolean", "input_params_type": params_type}
            tx_results = self._call_score(score_addr, "call_event_log_for_checking_params_type", tx_params)
            self.assertEqual(tx_results[0].status, int(False))

        # case4: defined parameter=bytes
        for params_type in type_list:
            if params_type == "bytes":
                continue
            tx_params = {"test_type": "bytes", "input_params_type": params_type}
            tx_results = self._call_score(score_addr, "call_event_log_for_checking_params_type", tx_params)
            self.assertEqual(tx_results[0].status, int(False))

        # case5: defined parameter=address
        for params_type in type_list:
            if params_type == "address":
                continue
            tx_params = {"test_type": "address", "input_params_type": params_type}
            tx_results = self._call_score(score_addr, "call_event_log_for_checking_params_type", tx_params)
            self.assertEqual(tx_results[0].status, int(False))

        # Success case: event_log's parameters default is none(None value is supported)
        type_list = ["integer", "string", "boolean", "bytes", "address"]

        for params_type in type_list:
            tx_params = {"test_type": params_type}
            tx_results = self._call_score(score_addr, "call_event_log_default_is_none", tx_params)
            self.assertEqual(tx_results[0].status, int(True))

    def test_event_log_internal_call(self):
        tx_result = self._deploy_score("test_internal_call_event_log_scores/test_event_log_score_a")
        self.assertEqual(tx_result.status, int(True))
        score_addr_a = tx_result.score_address

        tx_result = self._deploy_score("test_internal_call_event_log_scores/test_event_log_score_b")
        self.assertEqual(tx_result.status, int(True))
        score_addr_b = tx_result.score_address

        tx_result = self._deploy_score("test_internal_call_event_log_scores/test_event_log_score_c")
        self.assertEqual(tx_result.status, int(True))
        score_addr_c = tx_result.score_address

        # success case: score A(emit) -> score B(emit): both A and B's eventlog should be recorded
        # call score B method using interface
        tx_results = self._call_score(
            score_addr_a, "call_score_b_event_log_interface_call", {"addr": str(score_addr_b)})
        self.assertEqual(tx_results[0].status, int(True))
        event_log = tx_results[0].event_logs
        self.assertEqual(event_log[0].data[0], "A")
        self.assertEqual(event_log[1].data[0], "B")

        # call score B method using 'call' method
        tx_results = self._call_score(score_addr_a, "call_score_b_event_log_call", {"addr": str(score_addr_b)})
        self.assertEqual(tx_results[0].status, int(True))
        event_log = tx_results[0].event_logs
        self.assertEqual(event_log[0].data[0], "A")
        self.assertEqual(event_log[1].data[0], "B")

        # failure case: A(emit) -> B(read only, emit): if score B method is read only, should raise error
        tx_results = self._call_score(score_addr_a, "call_score_b_read_only_method", {"addr": str(score_addr_b)})
        self.assertEqual(tx_results[0].status, int(False))
        self.assertEqual(tx_results[0].failure.message, "The event log can not be recorded on readonly context")

        # success case: A(emit) -> B(read only) -> C(emit): both A and C's eventlog should be recorded
        tx_results = self._call_score(score_addr_a,
                                      "call_score_b_to_score_c_event_log",
                                      {"score_addr_b": str(score_addr_b), "score_addr_c": str(score_addr_c)})
        self.assertEqual(tx_results[0].status, int(True))
        event_log = tx_results[0].event_logs
        self.assertEqual(event_log[0].data[0], "A")
        self.assertEqual(event_log[1].data[0], "C")
