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

from typing import TYPE_CHECKING, List

from iconservice.base.address import SYSTEM_SCORE_ADDRESS
from tests.integrate_test.test_integrate_base import TestIntegrateBase

if TYPE_CHECKING:
    from iconservice.iconscore.icon_score_result import TransactionResult


class TestIntegrateEventLog(TestIntegrateBase):
    def setUp(self):
        super().setUp()
        self.update_governance()

    def test_valid_event_log(self):
        tx_results: List['TransactionResult'] = self.deploy_score(score_root="sample_event_log_scores",
                                                                  score_name="sample_event_log_score",
                                                                  from_=self._accounts[0],
                                                                  to_=SYSTEM_SCORE_ADDRESS)
        score_addr1 = tx_results[0].score_address

        # success case: call valid event log and check log data
        # event log which defined parameter's number is zero also treat as valid event log
        method_params = {"value1": "test1", "value2": "test2", "value3": "test3"}
        tx_results: List['TransactionResult'] = self.score_call(from_=self._accounts[0],
                                                                to_=score_addr1,
                                                                func_name="call_valid_event_log",
                                                                params=method_params)

        # indexed params and non_indexed params should be separately stored in txresult(indexed, data)
        event_log = tx_results[0].event_logs[0]
        self.assertEqual(event_log.indexed[0], "NormalEventLog(str,str,str)")
        self.assertEqual(event_log.indexed[1], "test1")
        self.assertEqual(event_log.indexed[2], "test2")
        self.assertEqual(event_log.data[0], "test3")

        # success case: call valid event log with None
        # event log which defined parameter's number is zero also treat as valid event log
        tx_results: List['TransactionResult'] = self.score_call(from_=self._accounts[0],
                                                                to_=score_addr1,
                                                                func_name="call_valid_event_log_with_none")

        # indexed params and non_indexed params should be separately stored in txresult(indexed, data)
        event_log = tx_results[0].event_logs[0]
        self.assertEqual(event_log.indexed[0], "NormalEventLog(str,str,str)")
        self.assertEqual(event_log.indexed[1], None)
        self.assertEqual(event_log.indexed[2], None)
        self.assertEqual(event_log.data[0], None)

        # success case: event log which params are not defined also treat as valid event log
        tx_results: List['TransactionResult'] = self.score_call(from_=self._accounts[0],
                                                                to_=score_addr1,
                                                                func_name="call_event_log_params_are_not_defined")

        event_log = tx_results[0].event_logs[0]
        self.assertEqual(event_log.data, [])
        self.assertEqual(event_log.indexed[0], "EventLogWithOutParams()")

        # success case: input keyword arguments to event log
        method_params = {"value1": "positional1", "value2": "keyword2", "value3": "keyword3"}
        tx_results: List['TransactionResult'] = self.score_call(from_=self._accounts[0],
                                                                to_=score_addr1,
                                                                func_name="call_valid_event_log_keyword",
                                                                params=method_params)

        event_log = tx_results[0].event_logs[0]
        self.assertEqual(event_log.indexed[0], "NormalEventLog(str,str,str)")
        self.assertEqual(event_log.indexed[1], "positional1")
        self.assertEqual(event_log.indexed[2], "keyword2")
        self.assertEqual(event_log.data[0], "keyword3")

        # success case: call event log which's parameters are set default value
        tx_results: List['TransactionResult'] = self.score_call(from_=self._accounts[0],
                                                                to_=score_addr1,
                                                                func_name="call_valid_event_log_with_default",
                                                                params={"value1": "non_default"})

        event_log = tx_results[0].event_logs[0]
        self.assertEqual(event_log.indexed[0], "NormalEventLogWithDefault(str,str,str)")
        self.assertEqual(event_log.indexed[1], "non_default")
        self.assertEqual(event_log.indexed[2], "default2")
        self.assertEqual(event_log.data[0], "default3")

        # success case: input empty string("") and empty bytes(b'') as event log's parameter
        tx_results: List['TransactionResult'] = self.score_call(
            from_=self._accounts[0],
            to_=score_addr1,
            func_name="call_event_log_input_empty_bytes_and_string_data")

        event_log = tx_results[0].event_logs[0]
        self.assertEqual(event_log.data[0], "")
        self.assertEqual(event_log.data[1], b'')

    def test_call_event_log_in_read_only_method(self):
        # failure case: if call event log on read_only method, should raise error
        tx_results: List['TransactionResult'] = self.deploy_score(score_root="sample_event_log_scores",
                                                                  score_name="sample_event_log_score",
                                                                  from_=self._accounts[0],
                                                                  to_=SYSTEM_SCORE_ADDRESS)
        score_addr1 = tx_results[0].score_address

        tx_results: List['TransactionResult'] = self.score_call(from_=self._accounts[0],
                                                                to_=score_addr1,
                                                                func_name="call_event_log_in_read_only_method",
                                                                expected_status=False)
        self.assertEqual(1, len(tx_results))

        self.assertEqual("The event log can not be recorded on readonly context", tx_results[0].failure.message)
        self.assertEqual(0, len(tx_results[0].event_logs))

    def test_event_log_self_is_not_defined(self):
        # failure case: event log which self is not defined treat as invalid event log
        tx_results: List['TransactionResult'] = self.deploy_score(
            score_root="sample_event_log_scores",
            score_name="sample_self_is_not_defined_event_log_score",
            from_=self._accounts[0],
            to_=SYSTEM_SCORE_ADDRESS,
            expected_status=False)

        self.assertEqual(tx_results[0].failure.message, "'self' is not declared as the first parameter")

    def test_event_log_when_error(self):
        tx_results: List['TransactionResult'] = self.deploy_score(score_root="sample_event_log_scores",
                                                                  score_name="sample_event_log_score",
                                                                  from_=self._accounts[0],
                                                                  to_=SYSTEM_SCORE_ADDRESS)
        score_addr1 = tx_results[0].score_address

        # failure case: the case of raising an error when call event log, the state should be revert
        self.score_call(from_=self._accounts[0],
                        to_=score_addr1,
                        func_name="call_event_log_raising_error",
                        expected_status=False)

        expected = "default"
        actual = self.query_score(from_=self._accounts[0],
                                  to_=score_addr1,
                                  func_name="get_value")
        self.assertEqual(expected, actual)

    def test_event_log_having_body(self):
        tx_results: List['TransactionResult'] = self.deploy_score(score_root="sample_event_log_scores",
                                                                  score_name="sample_event_log_score",
                                                                  from_=self._accounts[0],
                                                                  to_=SYSTEM_SCORE_ADDRESS)
        score_addr1 = tx_results[0].score_address

        # success case: even though the event log has body, body should be ignored
        self.score_call(from_=self._accounts[0],
                        to_=score_addr1,
                        func_name="call_event_log_having_body")

        expected = "default"
        actual = self.query_score(from_=self._accounts[0],
                                  to_=score_addr1,
                                  func_name="get_value")
        self.assertEqual(expected, actual)

    def test_event_log_index_on_deploy(self):
        tx_results: List['TransactionResult'] = self.deploy_score(score_root="sample_event_log_scores",
                                                                  score_name="sample_event_log_score",
                                                                  from_=self._accounts[0],
                                                                  to_=SYSTEM_SCORE_ADDRESS)
        score_addr1 = tx_results[0].score_address

        # success case: set index under 0(index number should be treated as 0)
        tx_results: List['TransactionResult'] = self.score_call(from_=self._accounts[0],
                                                                to_=score_addr1,
                                                                func_name="call_event_log_index_under_zero")
        event_log = tx_results[0].event_logs[0]

        # params should be stored in data list
        self.assertEqual(event_log.data[0], "test")
        # index length should be 1(including event log method name)
        self.assertEqual(len(event_log.indexed), 1)

        # failure case: setting index more than 4(should raise an error)
        tx_results: List['TransactionResult'] = self.deploy_score(score_root="sample_event_log_scores",
                                                                  score_name="sample_exceed_max_index_event_log_score",
                                                                  from_=self._accounts[0],
                                                                  to_=SYSTEM_SCORE_ADDRESS,
                                                                  expected_status=False)
        self.assertEqual(tx_results[0].failure.message, "Indexed arguments overflow: limit=3")

        # failure case: setting index more than event log's parameter total count(should raise an error)
        tx_results: List['TransactionResult'] = self.deploy_score(score_root="sample_event_log_scores",
                                                                  score_name="sample_index_exceed_params_event_log_score",
                                                                  from_=self._accounts[0],
                                                                  to_=SYSTEM_SCORE_ADDRESS,
                                                                  expected_status=False)
        self.assertEqual(tx_results[0].failure.message, "Index exceeds the number of parameters")

    def test_event_log_index_on_execute(self):
        pass

    def test_event_log_parameters_on_deploy(self):
        # failure case: omit type hint
        tx_results: List['TransactionResult'] = self.deploy_score(
            score_root="sample_event_log_scores",
            score_name="sample_invalid_params_type_hint_event_log_score",
            from_=self._accounts[0],
            to_=SYSTEM_SCORE_ADDRESS,
            expected_status=False)
        self.assertEqual(tx_results[0].failure.message,
                         "Missing argument hint for 'EventLogInvalidParamsType': 'value'")

    def test_event_log_parameters_on_execute(self):
        tx_results: List['TransactionResult'] = self.deploy_score(score_root="sample_event_log_scores",
                                                                  score_name="sample_event_log_score",
                                                                  from_=self._accounts[0],
                                                                  to_=SYSTEM_SCORE_ADDRESS)
        score_addr1 = tx_results[0].score_address

        # failure case: input less parameter to event log(raise error)
        self.score_call(from_=self._accounts[0],
                        to_=score_addr1,
                        func_name="call_event_log_input_less_number_of_params",
                        expected_status=False)

        # failure case: input exceed parameter to event log(raise error)
        self.score_call(from_=self._accounts[0],
                        to_=score_addr1,
                        func_name="call_event_log_input_exceed_number_of_params",
                        expected_status=False)

        self.score_call(from_=self._accounts[0],
                        to_=score_addr1,
                        func_name="call_event_log_input_exceed_number_of_params2",
                        expected_status=False)

        # failure case: input non-matching type parameter to event log(raise error)
        type_list = ["integer", "string", "boolean", "bytes", "address"]

        # case1: defined parameter=integer
        for params_type in type_list:
            if params_type == "integer" or params_type == "boolean":
                continue
            tx_params = {"test_type": "integer", "input_params_type": params_type}
            self.score_call(from_=self._accounts[0],
                            to_=score_addr1,
                            func_name="call_event_log_for_checking_params_type",
                            params=tx_params,
                            expected_status=False)

        # case2: defined parameter=string
        for params_type in type_list:
            if params_type == "string":
                continue
            tx_params = {"test_type": "string", "input_params_type": params_type}
            self.score_call(from_=self._accounts[0],
                            to_=score_addr1,
                            func_name="call_event_log_for_checking_params_type",
                            params=tx_params,
                            expected_status=False)

        # case3: defined parameter=boolean
        for params_type in type_list:
            if params_type == "boolean":
                continue
            tx_params = {"test_type": "boolean", "input_params_type": params_type}
            self.score_call(from_=self._accounts[0],
                            to_=score_addr1,
                            func_name="call_event_log_for_checking_params_type",
                            params=tx_params,
                            expected_status=False)

        # case4: defined parameter=bytes
        for params_type in type_list:
            if params_type == "bytes":
                continue
            tx_params = {"test_type": "bytes", "input_params_type": params_type}
            self.score_call(from_=self._accounts[0],
                            to_=score_addr1,
                            func_name="call_event_log_for_checking_params_type",
                            params=tx_params,
                            expected_status=False)

        # case5: defined parameter=address
        for params_type in type_list:
            if params_type == "address":
                continue
            tx_params = {"test_type": "address", "input_params_type": params_type}
            self.score_call(from_=self._accounts[0],
                            to_=score_addr1,
                            func_name="call_event_log_for_checking_params_type",
                            params=tx_params,
                            expected_status=False)

        # Success case: event_log's parameters default is none(None value is supported)
        type_list = ["integer", "string", "boolean", "bytes", "address"]

        for params_type in type_list:
            tx_params = {"test_type": params_type}
            self.score_call(from_=self._accounts[0],
                            to_=score_addr1,
                            func_name="call_event_log_default_is_none",
                            params=tx_params)

    def test_event_log_internal_call(self):
        tx_results: List['TransactionResult'] = self.deploy_score(
            score_root="sample_event_log_scores",
            score_name="sample_internal_call_event_log_scores/sample_event_log_score_a",
            from_=self._accounts[0],
            to_=SYSTEM_SCORE_ADDRESS)
        score_addr_a = tx_results[0].score_address

        tx_results: List['TransactionResult'] = self.deploy_score(
            score_root="sample_event_log_scores",
            score_name="sample_internal_call_event_log_scores/sample_event_log_score_b",
            from_=self._accounts[0],
            to_=SYSTEM_SCORE_ADDRESS)
        score_addr_b = tx_results[0].score_address

        tx_results: List['TransactionResult'] = self.deploy_score(
            score_root="sample_event_log_scores",
            score_name="sample_internal_call_event_log_scores/sample_event_log_score_c",
            from_=self._accounts[0],
            to_=SYSTEM_SCORE_ADDRESS)
        score_addr_c = tx_results[0].score_address

        # success case: score A(emit) -> score B(emit): both A and B's eventlog should be recorded
        # call score B method using interface
        tx_results: List['TransactionResult'] = self.score_call(from_=self._accounts[0],
                                                                to_=score_addr_a,
                                                                func_name="call_score_b_event_log_interface_call",
                                                                params={"addr": str(score_addr_b)})
        event_log = tx_results[0].event_logs
        self.assertEqual(event_log[0].data[0], "A")
        self.assertEqual(event_log[1].data[0], "B")

        # call score B method using 'call' method
        tx_results: List['TransactionResult'] = self.score_call(from_=self._accounts[0],
                                                                to_=score_addr_a,
                                                                func_name="call_score_b_event_log_call",
                                                                params={"addr": str(score_addr_b)})
        event_log = tx_results[0].event_logs
        self.assertEqual(event_log[0].data[0], "A")
        self.assertEqual(event_log[1].data[0], "B")

        # failure case: A(emit) -> B(read only, emit): if score B method is read only, should raise error
        tx_results: List['TransactionResult'] = self.score_call(from_=self._accounts[0],
                                                                to_=score_addr_a,
                                                                func_name="call_score_b_read_only_method",
                                                                params={"addr": str(score_addr_b)},
                                                                expected_status=False)
        self.assertEqual(tx_results[0].failure.message, "The event log can not be recorded on readonly context")

        # success case: A(emit) -> B(read only) -> C(emit): both A and C's eventlog should be recorded
        tx_results: List['TransactionResult'] = self.score_call(
            from_=self._accounts[0],
            to_=score_addr_a,
            func_name="call_score_b_to_score_c_event_log",
            params={"score_addr_b": str(score_addr_b), "score_addr_c": str(score_addr_c)})
        event_log = tx_results[0].event_logs
        self.assertEqual(event_log[0].data[0], "A")
        self.assertEqual(event_log[1].data[0], "C")
