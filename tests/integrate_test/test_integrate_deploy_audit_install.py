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
from typing import TYPE_CHECKING, List, Optional

from iconservice.base.address import SYSTEM_SCORE_ADDRESS, GOVERNANCE_SCORE_ADDRESS
from iconservice.base.exception import ExceptionCode
from iconservice.icon_constant import ConfigKey, ICX_IN_LOOP
from tests import raise_exception_start_tag, raise_exception_end_tag
from tests.integrate_test.test_integrate_base import TestIntegrateBase

if TYPE_CHECKING:
    from iconservice.base.address import Address
    from iconservice.iconscore.icon_score_result import TransactionResult


class TestIntegrateDeployAuditInstall(TestIntegrateBase):

    def _make_init_config(self) -> dict:
        return {ConfigKey.SERVICE: {ConfigKey.SERVICE_AUDIT: True}}

    def _update_governance_score(self, version: str = "latest_version"):
        tx_results: List['TransactionResult'] = self.update_governance(version=version)
        self.accept_score(tx_results[0].tx_hash)

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

    def _deploy_score(self,
                      score_name: str,
                      value: int,
                      expected_status: bool = True,
                      to_: Optional['Address'] = SYSTEM_SCORE_ADDRESS,
                      data: bytes = None) -> List['TransactionResult']:
        return self.deploy_score(score_root="sample_deploy_scores",
                                 score_name=score_name,
                                 from_=self._accounts[0],
                                 deploy_params={'value': hex(value * ICX_IN_LOOP)},
                                 expected_status=expected_status,
                                 to_=to_,
                                 data=data)

    def _create_deploy_score_tx_with_timestamp(self, timestamp: int, value: int) -> dict:
        return self.create_deploy_score_tx(score_root="sample_deploy_scores",
                                           score_name="install/sample_score",
                                           from_=self._accounts[0],
                                           to_=SYSTEM_SCORE_ADDRESS,
                                           timestamp_us=timestamp,
                                           deploy_params={'value': hex(value * ICX_IN_LOOP)})

    def _assert_get_value(self, from_addr: 'Address', score_addr: 'Address', func_name: str, value: int):
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
        self.assertEqual(response, value * ICX_IN_LOOP)

    def test_score(self):
        self._update_governance_score()

        # 1. deploy (wait audit)
        value1: int = 1
        tx_results: List['TransactionResult'] = self._deploy_score(score_name="install/sample_score",
                                                                   value=value1)
        score_addr1: 'Address' = tx_results[0].score_address
        tx_hash1: bytes = tx_results[0].tx_hash

        # 2. accept SCORE : tx_hash1
        tx_results: List['TransactionResult'] = self.accept_score(tx_hash=tx_hash1)
        tx_hash2 = tx_results[0].tx_hash

        # assert SCORE status
        expect_ret = {
            'current': {
                'status': 'active',
                'deployTxHash': tx_hash1,
                'auditTxHash': tx_hash2}}
        self._assert_get_score_status(score_addr1, expect_ret)

        # 3. assert get value: value1
        self._assert_get_value(self._accounts[0], score_addr1, "get_value", value1)

        # 4. set value: value2
        value2 = 2
        self.score_call(from_=self._accounts[0],
                        to_=score_addr1,
                        func_name="set_value",
                        params={"value": hex(value2 * ICX_IN_LOOP)})

        # 5. assert get value: value2
        self._assert_get_value(self._accounts[0], score_addr1, "get_value", value2)

    def test_accept_score_with_warning_message_update_0_0_5(self):
        # inputting message when accepting score is available as of governance version 0.0.6
        # previous version(below 0.0.5) raise error when trying this test
        self._update_governance_score("0_0_5")

        # 1. deploy (wait audit)
        value1: int = 1
        tx_results: List['TransactionResult'] = self._deploy_score(score_name="install/sample_score",
                                                                   value=value1)
        tx_hash1: bytes = tx_results[0].tx_hash

        # 2. accept SCORE : tx_hash1
        tx_results: List['TransactionResult'] = self.accept_score(tx_hash=tx_hash1)
        # check warning message(as not input warning argument when call acceptScore, "" should be recorded)
        self.assertEqual(tx_results[0].event_logs[0].data, [])

        # 1. deploy (wait audit)
        tx_results: List['TransactionResult'] = self._deploy_score(score_name="install/sample_score",
                                                                   value=value1)
        tx_hash1: bytes = tx_results[0].tx_hash

        # 2. accept SCORE with warning message: tx_hash1
        expected_warning_message = "test_warning_message"
        tx_results: List['TransactionResult'] = self.accept_score(tx_hash=tx_hash1,
                                                                  warning_message=expected_warning_message,
                                                                  expected_status=False)
        self.assertEqual(tx_results[0].failure.code, ExceptionCode.INVALID_PARAMETER)

    @unittest.skip('This issue (IS-243) has been cancelled.')
    def test_accept_score_with_warning_message(self):
        # inputting message when accepting score is available as of governance version 0.0.6
        # previous version(below 0.0.5) raise error when trying this test
        self._update_governance_score()

        # 1. deploy (wait audit)
        value1 = 1 * ICX_IN_LOOP
        tx_results: List['TransactionResult'] = self._deploy_score(score_name="install/sample_score",
                                                                   value=value1)
        tx_hash1: bytes = tx_results[0].tx_hash

        # 2. accept SCORE : tx_hash1
        tx_results: List['TransactionResult'] = self.accept_score(tx_hash=tx_hash1)

        # check warning message(as not input warning argument when call acceptScore, "" should be recorded)
        expected_warning_message = ""
        self.assertEqual(tx_results[0].event_logs[0].data[0], expected_warning_message)

        # 1. deploy (wait audit)
        value1 = 1 * ICX_IN_LOOP
        tx_results: List['TransactionResult'] = self._deploy_score(score_name="install/sample_score",
                                                                   value=value1)
        tx_hash1: bytes = tx_results[0].tx_hash

        # 2. accept SCORE with warning message: tx_hash1
        expected_warning_message = "test_warning_message"
        tx_results: List['TransactionResult'] = self.accept_score(tx_hash=tx_hash1,
                                                                  warning_message=expected_warning_message)
        self.assertEqual(tx_results[0].event_logs[0].data[0], expected_warning_message)

    def test_accept_score_without_warning_message_update_0_0_5(self):
        # inputting message when accepting score is available as of governance version 0.0.6
        # previous version(below 0.0.5) raise error when trying this test
        self._update_governance_score("0_0_5")

        # 1. deploy (wait audit)
        value1 = 1 * ICX_IN_LOOP
        tx_results: List['TransactionResult'] = self._deploy_score(score_name="install/sample_score",
                                                                   value=value1)
        tx_hash1: bytes = tx_results[0].tx_hash

        # 2. accept SCORE : tx_hash1
        tx_results: List['TransactionResult'] = self.accept_score(tx_hash=tx_hash1)

        # check warning message(as not input warning argument when call acceptScore,
        # "" should be recorded)
        self.assertEqual(tx_results[0].event_logs[0].data, [])

    @unittest.skip('This issue (IS-243) has been cancelled.')
    def test_accept_score_without_warning_message(self):
        # inputting message when accepting score is available as of governance version 0.0.6
        # previous version(below 0.0.5) raise error when trying this test
        self._update_governance_score()

        # 1. deploy (wait audit)
        value1 = 1 * ICX_IN_LOOP
        tx_results: List['TransactionResult'] = self._deploy_score(score_name="install/sample_score",
                                                                   value=value1)
        tx_hash1: bytes = tx_results[0].tx_hash

        # 2. accept SCORE : tx_hash1
        tx_results: List['TransactionResult'] = self.accept_score(tx_hash=tx_hash1)

        # check warning message(as not input warning argument when call acceptScore, "" should be recorded)
        warning_message = ""
        self.assertEqual(tx_results[0].event_logs[0].data[0], warning_message)

    def test_score_address_already_in_use(self):
        # 1. deploy same SCORE address (wait audit)
        timestamp = 1
        value1 = 1
        tx1: dict = self._create_deploy_score_tx_with_timestamp(timestamp=timestamp,
                                                                value=value1)
        tx2: dict = self._create_deploy_score_tx_with_timestamp(timestamp=timestamp,
                                                                value=value1)

        raise_exception_start_tag("test_score_address_already_in_use -1")
        prev_block, hash_list = self.make_and_req_block([tx1, tx2])
        raise_exception_end_tag("test_score_address_already_in_use -1")

        self._write_precommit_state(prev_block)

        tx_results: List['TransactionResult'] = self.get_tx_results(hash_list)
        self.assertEqual(tx_results[0].status, int(True))
        score_addr1: 'Address' = tx_results[0].score_address
        tx_hash1: bytes = tx_results[0].tx_hash

        self.assertEqual(tx_results[1].status, int(False))
        self.assertEqual(tx_results[1].failure.code, ExceptionCode.ACCESS_DENIED)
        self.assertEqual(tx_results[1].failure.message, f'SCORE address already in use: {str(score_addr1)}')
        tx_hash2: bytes = tx_results[1].tx_hash

        # 2. accept SCORE : tx_hash1, tx_hash2
        tx3: dict = self.create_score_call_tx(self._admin,
                                              GOVERNANCE_SCORE_ADDRESS,
                                              'acceptScore',
                                              {"txHash": f'0x{bytes.hex(tx_hash1)}'})
        tx4: dict = self.create_score_call_tx(self._admin,
                                              GOVERNANCE_SCORE_ADDRESS,
                                              'acceptScore',
                                              {"txHash": f'0x{bytes.hex(tx_hash2)}'})

        raise_exception_start_tag("test_score_address_already_in_use -2")
        prev_block, hash_list = self.make_and_req_block([tx3, tx4])
        raise_exception_end_tag("test_score_address_already_in_use -2")

        tx_results: List['TransactionResult'] = self.get_tx_results(hash_list)
        self._write_precommit_state(prev_block)

        self.assertEqual(tx_results[0].status, int(True))

        self.assertEqual(tx_results[1].status, int(False))
        self.assertEqual(tx_results[1].failure.code, ExceptionCode.SCORE_ERROR)
        self.assertEqual(tx_results[1].failure.message, 'Invalid txHash')

        # 3. assert get value: value1
        self._assert_get_value(self._accounts[0], score_addr1, "get_value", value1)

        # 4. set value: value2
        value2 = 2
        self.score_call(from_=self._accounts[0],
                        to_=score_addr1,
                        func_name="set_value",
                        params={"value": hex(value2 * ICX_IN_LOOP)})

        # 5. assert get value: value2
        self._assert_get_value(self._accounts[0], score_addr1, "get_value", value2)

    def test_score_address_already_in_use_update_governance(self):
        self._update_governance_score()

        # 1. deploy same SCORE address (wait audit)
        timestamp = 1
        value1 = 1
        tx1: dict = self._create_deploy_score_tx_with_timestamp(timestamp=timestamp,
                                                                value=value1)
        tx2: dict = self._create_deploy_score_tx_with_timestamp(timestamp=timestamp,
                                                                value=value1)

        raise_exception_start_tag("test_score_address_already_in_use_update_governance -1")
        prev_block, hash_list = self.make_and_req_block([tx1, tx2])
        raise_exception_end_tag("test_score_address_already_in_use_update_governance -1")

        self._write_precommit_state(prev_block)

        tx_results: List['TransactionResult'] = self.get_tx_results(hash_list)
        self.assertEqual(tx_results[0].status, int(True))
        score_addr1: 'Address' = tx_results[0].score_address
        tx_hash1: bytes = tx_results[0].tx_hash

        self.assertEqual(tx_results[1].status, int(False))
        self.assertEqual(tx_results[1].failure.code, ExceptionCode.ACCESS_DENIED)
        self.assertEqual(tx_results[1].failure.message, f'SCORE address already in use: {str(score_addr1)}')
        tx_hash2: bytes = tx_results[1].tx_hash

        # 2. accept SCORE : tx_hash1, tx_hash2
        tx3 = self.create_score_call_tx(self._admin,
                                        GOVERNANCE_SCORE_ADDRESS,
                                        'acceptScore',
                                        {"txHash": f'0x{bytes.hex(tx_hash1)}'})

        tx4 = self.create_score_call_tx(self._admin,
                                        GOVERNANCE_SCORE_ADDRESS,
                                        'acceptScore',
                                        {"txHash": f'0x{bytes.hex(tx_hash2)}'})

        raise_exception_start_tag("test_score_address_already_in_use2")
        prev_block, hash_list = self.make_and_req_block([tx3, tx4])
        raise_exception_end_tag("test_score_address_already_in_use2")

        tx_results: List['TransactionResult'] = self.get_tx_results(hash_list)
        self._write_precommit_state(prev_block)

        self.assertEqual(tx_results[0].status, int(True))

        self.assertEqual(tx_results[1].status, int(False))
        self.assertEqual(tx_results[1].failure.code, ExceptionCode.SCORE_ERROR)
        self.assertEqual(tx_results[1].failure.message, 'Invalid txHash: None')

        # 3. assert get value: value1
        self._assert_get_value(self._accounts[0], score_addr1, "get_value", value1)

        # 4. set value: value2
        value2 = 2
        self.score_call(from_=self._accounts[0],
                        to_=score_addr1,
                        func_name="set_value",
                        params={"value": hex(value2 * ICX_IN_LOOP)})

        # 5. assert get value: value2
        self._assert_get_value(self._accounts[0], score_addr1, "get_value", value2)

    def test_score_no_zip(self):
        self._update_governance_score()

        # 1. deploy same SCORE address (wait audit)
        value1 = 1
        tx_results: List['TransactionResult'] = self._deploy_score(score_name="install/sample_score",
                                                                   value=value1,
                                                                   data=b'invalid')
        tx_hash1 = tx_results[0].tx_hash

        # 2. accept SCORE : tx_hash1
        raise_exception_start_tag("test_score_no_zip")
        tx_results: List['TransactionResult'] = self.accept_score(tx_hash=tx_hash1,
                                                                  expected_status=False)
        raise_exception_end_tag("test_score_no_zip")
        self.assertEqual(tx_results[0].failure.code, ExceptionCode.INVALID_PACKAGE)
        self.assertEqual(tx_results[0].failure.message, f'Bad zip file.')

    def test_score_no_scorebase(self):
        self._update_governance_score()

        # 1. deploy same SCORE address (wait audit)
        value1 = 1
        tx_results: List['TransactionResult'] = self._deploy_score(score_name="install/sample_score_no_scorebase",
                                                                   value=value1)
        tx_hash1 = tx_results[0].tx_hash

        # 2. accept SCORE : tx_hash1
        raise_exception_start_tag("sample_score_no_scorebase")
        tx_results: List['TransactionResult'] = self.accept_score(tx_hash=tx_hash1,
                                                                  expected_status=False)
        raise_exception_end_tag("sample_score_no_scorebase")

        self.assertEqual(tx_results[0].failure.code, ExceptionCode.SYSTEM_ERROR)
        self.assertEqual(tx_results[0].failure.message, "'SampleScore' object has no attribute 'owner'")

    def test_score_on_install_error(self):
        self._update_governance_score()

        # 1. deploy same SCORE address (wait audit)
        value1 = 1
        tx_results: List['TransactionResult'] = self._deploy_score(score_name="install/sample_score_on_install_error",
                                                                   value=value1)
        tx_hash1 = tx_results[0].tx_hash

        # 2. accept SCORE : tx_hash1
        raise_exception_start_tag("sample_score_on_install_error")
        tx_results: List['TransactionResult'] = self.accept_score(tx_hash=tx_hash1,
                                                                  expected_status=False)
        raise_exception_end_tag("sample_score_on_install_error")

        self.assertEqual(tx_results[0].failure.code, ExceptionCode.SCORE_ERROR)
        self.assertEqual(tx_results[0].failure.message, "raise exception!")

    def test_score_no_external_func(self):
        self._update_governance_score()

        # 1. deploy same SCORE address (wait audit)
        value1 = 1
        tx_results: List['TransactionResult'] = self._deploy_score(score_name="install/sample_score_no_external_func",
                                                                   value=value1)
        tx_hash1 = tx_results[0].tx_hash

        # 2. accept SCORE : tx_hash1
        raise_exception_start_tag("sample_score_no_external_func")
        tx_results: List['TransactionResult'] = self.accept_score(tx_hash=tx_hash1,
                                                                  expected_status=False)
        raise_exception_end_tag("sample_score_no_external_func")

        self.assertEqual(tx_results[0].failure.code, ExceptionCode.ILLEGAL_FORMAT)
        self.assertEqual(tx_results[0].failure.message, "There is no external method in the SCORE")

    def test_score_with_korean_comments(self):
        self._update_governance_score()

        # 1. deploy same SCORE address (wait audit)
        value1 = 1
        tx_results: List['TransactionResult'] = self._deploy_score(
            score_name="install/sample_score_with_korean_comments",
            value=value1)
        tx_hash1 = tx_results[0].tx_hash

        # 2. accept SCORE : tx_hash1
        raise_exception_start_tag("sample_score_with_korean_comments")
        tx_results: List['TransactionResult'] = self.accept_score(tx_hash=tx_hash1,
                                                                  expected_status=False)
        raise_exception_end_tag("sample_score_with_korean_comments")

        self.assertEqual(tx_results[0].failure.code, ExceptionCode.SYSTEM_ERROR)

    def test_score_no_python(self):
        self._update_governance_score()

        # 1. deploy same SCORE address (wait audit)
        value1 = 1
        tx_results: List['TransactionResult'] = self._deploy_score(score_name="install/sample_score_no_python",
                                                                   value=value1)
        tx_hash1 = tx_results[0].tx_hash

        # 2. accept SCORE : tx_hash1
        raise_exception_start_tag("sample_score_no_python")
        tx_results: List['TransactionResult'] = self.accept_score(tx_hash=tx_hash1,
                                                                  expected_status=False)
        raise_exception_end_tag("sample_score_no_python")

        self.assertEqual(tx_results[0].failure.code, ExceptionCode.SYSTEM_ERROR)
