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

from typing import TYPE_CHECKING, List, Any

from iconservice import IconServiceFlag
from iconservice.base.address import Address
from iconservice.base.address import ZERO_SCORE_ADDRESS, GOVERNANCE_SCORE_ADDRESS
from iconservice.base.exception import ExceptionCode, ScoreNotFoundException
from iconservice.icon_constant import ICX_IN_LOOP
from tests import raise_exception_start_tag, raise_exception_end_tag
from tests.integrate_test.test_integrate_base import TestIntegrateBase

if TYPE_CHECKING:
    from iconservice.iconscore.icon_score_result import TransactionResult


class TestIntegrateScores(TestIntegrateBase):
    def query_db_returns(self,
                         to_: 'Address',
                         index: int) -> Any:
        query_request = {
            "version": self._version,
            "from": self._admin,
            "to": to_,
            "dataType": "call",
            "data": {
                "method": f"get_value{index}",
                "params": {}
            }
        }
        return self._query(query_request)

    def test_db_returns(self):
        tx_results: List['TransactionResult'] = self.deploy_score(
            score_root="sample_scores",
            score_name="sample_db_returns",
            from_=self._accounts[0],
            deploy_params={"value": str(self._accounts[1].address),
                           "value1": str(self._accounts[1].address)})
        score_address: 'Address' = tx_results[0].score_address

        default_ret: list = [
            0,
            "",
            None,
            self._accounts[1].address,
            False,
            self._accounts[1].address
        ]
        inputs: list = [
            hex(1 * ICX_IN_LOOP),
            "a",
            bytes.hex(b'12345'),
            str(self._accounts[1].address),
            hex(int(True)),
            str(self._accounts[1].address)
        ]

        ret: list = [
            1 * ICX_IN_LOOP,
            "a",
            b'12345',
            self._accounts[1].address,
            int(True),
            self._accounts[1].address,
        ]

        for i in range(6):
            index: int = i + 1
            self.assertEqual(default_ret[i], self.query_db_returns(score_address, index))
            self.score_call(from_=self._accounts[0],
                            to_=score_address,
                            func_name=f"set_value{index}",
                            params={"value": inputs[i]})
            self.assertEqual(ret[i], self.query_db_returns(score_address, index))

    def test_default_value_fail_install(self):
        raise_exception_start_tag("sample_default_value_fail_install")
        self.deploy_score(
            score_root="sample_scores",
            score_name="sample_default_value_fail1",
            from_=self._accounts[0],
            expected_status=False)
        raise_exception_end_tag("sample_default_value_fail_install")

    def test_default_value_fail_update(self):
        raise_exception_start_tag("sample_default_value_fail_update")
        self.deploy_score(
            score_root="sample_scores",
            score_name="sample_default_value_fail2",
            from_=self._accounts[0],
            expected_status=False)
        raise_exception_end_tag("sample_default_value_fail_update")

    def test_default_value_fail_external(self):
        raise_exception_start_tag("sample_default_value_fail_external")
        self.deploy_score(
            score_root="sample_scores",
            score_name="sample_default_value_fail3",
            from_=self._accounts[0],
            expected_status=False)
        raise_exception_end_tag("sample_default_value_fail_external")

    def test_service_flag(self):
        self.update_governance()

        query_request = {
            "version": self._version,
            "from": self._admin,
            "to": GOVERNANCE_SCORE_ADDRESS,
            "dataType": "call",
            "data": {
                "method": "getServiceConfig",
                "params": {}
            }
        }
        response = self._query(query_request)

        table = {}
        for flag in IconServiceFlag:
            if flag.name is 'SCORE_PACKAGE_VALIDATOR':
                table[flag.name] = True
            else:
                table[flag.name] = False
        self.assertEqual(response, table)

        tx_results: List['TransactionResult'] = self.deploy_score(
            score_root="sample_deploy_scores",
            score_name="install/sample_score",
            from_=self._accounts[0])
        score_address1: 'Address' = tx_results[0].score_address

        self.score_call(from_=self._admin,
                        to_=GOVERNANCE_SCORE_ADDRESS,
                        func_name="updateServiceConfig",
                        params={"serviceFlag": hex(IconServiceFlag.AUDIT)})

        tx_results: List['TransactionResult'] = self.deploy_score(score_root="sample_deploy_scores",
                                                                  score_name="install/sample_score",
                                                                  from_=self._accounts[1])
        score_address2: 'Address' = tx_results[0].score_address

        target_flag = IconServiceFlag.AUDIT | IconServiceFlag.FEE

        tx1: dict = self.create_score_call_tx(from_=self._admin,
                                              to_=GOVERNANCE_SCORE_ADDRESS,
                                              func_name="updateServiceConfig",
                                              params={"serviceFlag": hex(target_flag)})

        tx2: dict = self.create_deploy_score_tx(score_root="sample_deploy_scores",
                                                score_name="install/sample_score",
                                                from_=self._accounts[1],
                                                to_=ZERO_SCORE_ADDRESS)

        prev_block, hash_list = self.make_and_req_block([tx1, tx2])
        self._write_precommit_state(prev_block)

        tx_results: List['TransactionResult'] = self.get_tx_results(hash_list)
        self.assertEqual(int(True), tx_results[0].status)
        self.assertEqual(int(False), tx_results[1].status)

        response = self._query(query_request)
        table = {}
        for flag in IconServiceFlag:
            if target_flag & flag == flag:
                table[flag.name] = True
            else:
                table[flag.name] = False
        self.assertEqual(response, table)

        self.get_score_api(score_address1)

        with self.assertRaises(ScoreNotFoundException) as e:
            self.get_score_api(score_address2)
        self.assertEqual(e.exception.args[0], f"SCORE not found: {score_address2}")

    def test_revert(self):
        tx_results: List['TransactionResult'] = self.deploy_score(score_root="sample_scores",
                                                                  score_name="sample_wrong_revert",
                                                                  from_=self._accounts[0])
        score_addr1 = tx_results[0].score_address

        tx_results: List['TransactionResult'] = self.score_call(from_=self._accounts[0],
                                                                to_=score_addr1,
                                                                func_name="set_value1",
                                                                params={"value": hex(100)},
                                                                expected_status=False)
        self.assertEqual(tx_results[0].failure.code, ExceptionCode.END)
        self.assertEqual(tx_results[0].failure.message, 'hello world')

        # Test call_revert_with_invalid_code
        tx_results: List['TransactionResult'] = self.score_call(from_=self._accounts[0],
                                                                to_=score_addr1,
                                                                func_name="call_revert_with_invalid_code",
                                                                params={},
                                                                expected_status=False)
        self.assertEqual(tx_results[0].failure.code, ExceptionCode.INVALID_PARAMETER)
        self.assertIsInstance(tx_results[0].failure.message, str)

        # Test call_revert_with_none_message
        tx_results: List['TransactionResult'] = self.score_call(from_=self._accounts[0],
                                                                to_=score_addr1,
                                                                func_name="call_revert_with_none_message",
                                                                params={},
                                                                expected_status=False)
        self.assertEqual(tx_results[0].failure.code, ExceptionCode.END)

        # Test call_revert_with_none_message_and_none_code()
        tx_results: List['TransactionResult'] = self.score_call(from_=self._accounts[0],
                                                                to_=score_addr1,
                                                                func_name="call_revert_with_none_message_and_none_code",
                                                                params={},
                                                                expected_status=False)
        self.assertEqual(tx_results[0].failure.code, ExceptionCode.INVALID_PARAMETER)
        self.assertIsInstance(tx_results[0].failure.message, str)

        # Test exception handling on call_exception()
        tx_results: List['TransactionResult'] = self.score_call(from_=self._accounts[0],
                                                                to_=score_addr1,
                                                                func_name="call_exception",
                                                                params={},
                                                                expected_status=False)
        self.assertIsInstance(tx_results[0].failure.code, int)
        self.assertIsInstance(tx_results[0].failure.message, str)
