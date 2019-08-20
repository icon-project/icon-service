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

from typing import TYPE_CHECKING, List, Optional, Tuple

from iconservice.base.address import ZERO_SCORE_ADDRESS, GOVERNANCE_SCORE_ADDRESS
from iconservice.base.exception import ExceptionCode
from iconservice.icon_constant import ConfigKey, ICX_IN_LOOP
from tests import raise_exception_start_tag, raise_exception_end_tag
from tests.integrate_test.test_integrate_base import TestIntegrateBase

if TYPE_CHECKING:
    from iconservice.iconscore.icon_score_result import TransactionResult
    from iconservice.base.address import Address


class TestIntegrateDeployAuditUpdate(TestIntegrateBase):

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

    def _install_normal_score(self, value: int) -> Tuple['Address', bytes, bytes]:
        # 1. deploy (wait audit)

        tx_results: List['TransactionResult'] = self.deploy_score(score_root="sample_deploy_scores",
                                                                  score_name="install/sample_score",
                                                                  from_=self._accounts[0],
                                                                  deploy_params={'value': hex(value * ICX_IN_LOOP)})
        score_addr1: 'Address' = tx_results[0].score_address
        tx_hash1: bytes = tx_results[0].tx_hash

        # 2. accept SCORE : tx_hash1
        tx_results: List['TransactionResult'] = self.accept_score(tx_hash=tx_hash1)
        tx_hash2: bytes = tx_results[0].tx_hash

        return score_addr1, tx_hash1, tx_hash2

    def _deploy_score(self,
                      score_name: str,
                      value: int,
                      expected_status: bool = True,
                      to_: Optional['Address'] = ZERO_SCORE_ADDRESS,
                      data: bytes = None) -> List['TransactionResult']:
        return self.deploy_score(score_root="sample_deploy_scores",
                                 score_name=score_name,
                                 from_=self._accounts[0],
                                 deploy_params={'value': hex(value * ICX_IN_LOOP)},
                                 expected_status=expected_status,
                                 to_=to_,
                                 data=data)

    def test_score(self):
        self._update_governance_score()

        # 1. install done
        value1 = 1
        score_addr1, tx_hash1, tx_hash2 = self._install_normal_score(value1)

        # 2. deploy update (wait audit)
        """
        def on_update(self, value: int) -> None:
            super().on_update()
            var = self._value.get()
            self._value.set(var + value)
        
        def set_value(self, value: int):
            self._value.set(value * 2)
            self.Changed(value)
        """
        value2 = 2
        tx_results: List['TransactionResult'] = self.deploy_score(score_root="sample_deploy_scores",
                                                                  score_name="update/sample_score",
                                                                  from_=self._accounts[0],
                                                                  deploy_params={'value': hex(value2 * ICX_IN_LOOP)},
                                                                  to_=score_addr1)
        tx_hash3 = tx_results[0].tx_hash

        # 3. assert get value: value1
        self._assert_get_value(self._accounts[0], score_addr1, "get_value", value1)

        # 4. accept SCORE : tx_hash3
        self.accept_score(tx_hash=tx_hash3)

        # 5. assert get value: value1 + value2
        self._assert_get_value(self._accounts[0], score_addr1, "get_value", value1 + value2)

        # 6. set value: value2
        self.score_call(from_=self._accounts[0],
                        to_=score_addr1,
                        func_name="set_value",
                        params={"value": hex(value2 * ICX_IN_LOOP)})

        # 7. assert get value: 2 * value2
        self._assert_get_value(self._accounts[0], score_addr1, "get_value", 2 * value2)

    def test_invalid_owner(self):
        # 1. install done
        value1 = 1
        score_addr1, tx_hash1, tx_hash2 = self._install_normal_score(value1)

        # 2. deploy update (wait audit)
        value2 = 2
        raise_exception_start_tag("test_invalid_owner -1")
        tx_results: List['TransactionResult'] = self.deploy_score(score_root="sample_deploy_scores",
                                                                  score_name="update/sample_score",
                                                                  from_=self._accounts[1],
                                                                  deploy_params={'value': hex(value2 * ICX_IN_LOOP)},
                                                                  to_=score_addr1,
                                                                  expected_status=False)
        raise_exception_end_tag("test_invalid_owner -1")
        tx_hash3 = tx_results[0].tx_hash
        self.assertEqual(tx_results[0].failure.code, ExceptionCode.ACCESS_DENIED)
        self.assertEqual(tx_results[0].failure.message,
                         f'Invalid owner: {str(self._accounts[0].address)} '
                         f'!= {str(self._accounts[1].address)}')

        # 3. accept SCORE : tx_hash3
        raise_exception_start_tag("test_invalid_owner2")
        tx_results: List['TransactionResult'] = self.accept_score(tx_hash=tx_hash3,
                                                                  expected_status=False)
        raise_exception_end_tag("test_invalid_owner2")
        self.assertEqual(tx_results[0].failure.code, ExceptionCode.SCORE_ERROR)
        self.assertEqual(tx_results[0].failure.message, "Invalid txHash")

        # 4. assert get value: value1
        self._assert_get_value(self._accounts[0], score_addr1, "get_value", value1)

        # 5. set value: value3
        value3 = 3
        self.score_call(from_=self._accounts[0],
                        to_=score_addr1,
                        func_name="set_value",
                        params={"value": hex(value3 * ICX_IN_LOOP)})

        # 6. assert get value: value3
        self._assert_get_value(self._accounts[0], score_addr1, "get_value", value3)

    def test_invalid_owner_update_governance(self):
        self._update_governance_score()

        # 1. install done
        value1 = 1
        score_addr1, tx_hash1, tx_hash2 = self._install_normal_score(value1)

        # 2. deploy update (wait audit)
        value2 = 2
        tx_results: List['TransactionResult'] = self.deploy_score(score_root="sample_deploy_scores",
                                                                  score_name="update/sample_score",
                                                                  from_=self._accounts[1],
                                                                  deploy_params={'value': hex(value2 * ICX_IN_LOOP)},
                                                                  to_=score_addr1,
                                                                  expected_status=False)
        tx_hash3 = tx_results[0].tx_hash
        self.assertEqual(tx_results[0].failure.code, ExceptionCode.ACCESS_DENIED)
        self.assertEqual(tx_results[0].failure.message,
                         f'Invalid owner: {str(self._accounts[0].address)} '
                         f'!= {str(self._accounts[1].address)}')

        # 3. accept SCORE : tx_hash3
        raise_exception_start_tag("test_invalid_owner -2")
        tx_results: List['TransactionResult'] = self.accept_score(tx_hash=tx_hash3,
                                                                  expected_status=False)
        raise_exception_end_tag("test_invalid_owner -2")
        self.assertEqual(tx_results[0].failure.code, ExceptionCode.SCORE_ERROR)
        self.assertEqual(tx_results[0].failure.message, "Invalid txHash: None")

        # 4. assert get value: value1
        self._assert_get_value(self._accounts[0], score_addr1, "get_value", value1)

        # 5. set value: value3
        value3 = 3
        self.score_call(from_=self._accounts[0],
                        to_=score_addr1,
                        func_name="set_value",
                        params={"value": hex(value3 * ICX_IN_LOOP)})

        # 6. assert get value: value3
        self._assert_get_value(self._accounts[0], score_addr1, "get_value", value3)

    def test_score_no_zip(self):
        self._update_governance_score()

        # 1. install done
        value1 = 1
        score_addr1, tx_hash1, tx_hash2 = self._install_normal_score(value1)

        # 2. deploy update (wait audit)
        value2 = 2
        tx_results: List['TransactionResult'] = self._deploy_score(score_name="install/update",
                                                                   value=value2,
                                                                   data=b'invalid',
                                                                   to_=score_addr1)
        tx_hash3 = tx_results[0].tx_hash

        # 3. accept SCORE : tx_hash3
        raise_exception_start_tag("test_score_no_zip")
        tx_results: List['TransactionResult'] = self.accept_score(tx_hash=tx_hash3,
                                                                  expected_status=False)
        raise_exception_end_tag("test_score_no_zip")

        self.assertEqual(tx_results[0].failure.code, ExceptionCode.INVALID_PACKAGE)
        self.assertEqual(tx_results[0].failure.message, f'Bad zip file.')

        # 4. assert get value: value1
        self._assert_get_value(self._accounts[0], score_addr1, "get_value", value1)

        # 5. set value: value3
        value3 = 3
        self.score_call(from_=self._accounts[0],
                        to_=score_addr1,
                        func_name="set_value",
                        params={"value": hex(value3 * ICX_IN_LOOP)})

        # 6. assert get value: value3
        self._assert_get_value(self._accounts[0], score_addr1, "get_value", value3)

    def test_score_no_scorebase(self):
        self._update_governance_score()

        # 1. install done
        value1 = 1
        score_addr1, tx_hash1, tx_hash2 = self._install_normal_score(value1)

        # 2. deploy update (wait audit)
        value2 = 2
        tx_results: List['TransactionResult'] = self._deploy_score(score_name="install/sample_score_no_scorebase",
                                                                   value=value2,
                                                                   to_=score_addr1)
        tx_hash3 = tx_results[0].tx_hash

        # 3. accept SCORE : tx_hash3
        raise_exception_start_tag("test_score_no_scorebase")
        tx_results: List['TransactionResult'] = self.accept_score(tx_hash=tx_hash3,
                                                                  expected_status=False)
        raise_exception_end_tag("test_score_no_scorebase")

        self.assertEqual(tx_results[0].failure.code, ExceptionCode.SYSTEM_ERROR)
        self.assertEqual(tx_results[0].failure.message, "'SampleScore' object has no attribute 'owner'")

        # 4. assert get value: value1
        self._assert_get_value(self._accounts[0], score_addr1, "get_value", value1)

        # 5. set value: value3
        value3 = 3
        self.score_call(from_=self._accounts[0],
                        to_=score_addr1,
                        func_name="set_value",
                        params={"value": hex(value3 * ICX_IN_LOOP)})

        # 6. assert get value: value3
        self._assert_get_value(self._accounts[0], score_addr1, "get_value", value3)

    def test_score_on_update_error(self):
        self._update_governance_score()

        # 1. install done
        value1 = 1 * ICX_IN_LOOP
        score_addr1, tx_hash1, tx_hash2 = self._install_normal_score(value1)

        # 2. deploy update (wait audit)
        value2 = 2
        tx_results: List['TransactionResult'] = self._deploy_score(score_name="update/sample_score_on_update_error",
                                                                   value=value2,
                                                                   to_=score_addr1)
        tx_hash3 = tx_results[0].tx_hash

        # 3. accept SCORE : tx_hash3
        raise_exception_start_tag("test_score_on_update_error")
        tx_results: List['TransactionResult'] = self.accept_score(tx_hash=tx_hash3,
                                                                  expected_status=False)
        raise_exception_end_tag("test_score_on_update_error")

        self.assertEqual(tx_results[0].failure.code, ExceptionCode.SCORE_ERROR)
        self.assertEqual(tx_results[0].failure.message, "raise exception!")

        # 4. assert get value: value1
        self._assert_get_value(self._accounts[0], score_addr1, "get_value", value1)

        # 5. set value: value3
        value3 = 3
        self.score_call(from_=self._accounts[0],
                        to_=score_addr1,
                        func_name="set_value",
                        params={"value": hex(value3 * ICX_IN_LOOP)})

        # 6. assert get value: value3
        self._assert_get_value(self._accounts[0], score_addr1, "get_value", value3)

    def test_score_no_external_func(self):
        self._update_governance_score()

        # 1. install done
        value1 = 1
        score_addr1, tx_hash1, tx_hash2 = self._install_normal_score(value1)

        # 2. deploy update (wait audit)
        value2 = 2
        tx_results: List['TransactionResult'] = self._deploy_score(score_name="install/sample_score_no_external_func",
                                                                   value=value2,
                                                                   to_=score_addr1)
        tx_hash3 = tx_results[0].tx_hash

        # 3. accept SCORE : tx_hash3
        raise_exception_start_tag("test_score_no_external_func")
        tx_results: List['TransactionResult'] = self.accept_score(tx_hash=tx_hash3,
                                                                  expected_status=False)
        raise_exception_end_tag("test_score_no_external_func")

        self.assertEqual(tx_results[0].failure.code, ExceptionCode.ILLEGAL_FORMAT)
        self.assertEqual(tx_results[0].failure.message, "There is no external method in the SCORE")

        # 4. assert get value: value1
        self._assert_get_value(self._accounts[0], score_addr1, "get_value", value1)

        # 5. set value: value3
        value3 = 3
        self.score_call(from_=self._accounts[0],
                        to_=score_addr1,
                        func_name="set_value",
                        params={"value": hex(value3 * ICX_IN_LOOP)})

        # 6. assert get value: value3
        self._assert_get_value(self._accounts[0], score_addr1, "get_value", value3)

    def test_score_with_korean_comments(self):
        self._update_governance_score()

        # 1. install done
        value1 = 1
        score_addr1, tx_hash1, tx_hash2 = self._install_normal_score(value1)

        # 2. deploy update (wait audit)
        value2 = 2
        tx_results: List['TransactionResult'] = self._deploy_score(
            score_name="install/sample_score_with_korean_comments",
            value=value2,
            to_=score_addr1)
        tx_hash3 = tx_results[0].tx_hash

        # 3. accept SCORE : tx_hash3
        raise_exception_start_tag("test_score_with_korean_comments")
        tx_results: List['TransactionResult'] = self.accept_score(tx_hash=tx_hash3,
                                                                  expected_status=False)
        raise_exception_end_tag("test_score_with_korean_comments")

        self.assertEqual(tx_results[0].failure.code, ExceptionCode.SYSTEM_ERROR)

        # 4. assert get value: value1
        self._assert_get_value(self._accounts[0], score_addr1, "get_value", value1)

        # 5. set value: value3
        value3 = 3
        self.score_call(from_=self._accounts[0],
                        to_=score_addr1,
                        func_name="set_value",
                        params={"value": hex(value3 * ICX_IN_LOOP)})

        # 6. assert get value: value3
        self._assert_get_value(self._accounts[0], score_addr1, "get_value", value3)

    def test_score_no_python(self):
        self._update_governance_score()

        # 1. install done
        value1 = 1
        score_addr1, tx_hash1, tx_hash2 = self._install_normal_score(value1)

        # 2. deploy update (wait audit)
        value2 = 2
        tx_results: List['TransactionResult'] = self._deploy_score(
            score_name="install/sample_score_no_python",
            value=value2,
            to_=score_addr1)
        tx_hash3 = tx_results[0].tx_hash

        # 3. accept SCORE : tx_hash3
        raise_exception_start_tag("test_score_no_python")
        tx_results: List['TransactionResult'] = self.accept_score(tx_hash=tx_hash3,
                                                                  expected_status=False)
        raise_exception_end_tag("test_score_no_python")

        self.assertEqual(tx_results[0].failure.code, ExceptionCode.SYSTEM_ERROR)

        # 4. assert get value: value1
        self._assert_get_value(self._accounts[0], score_addr1, "get_value", value1)

        # 5. set value: value3
        value3 = 3
        self.score_call(from_=self._accounts[0],
                        to_=score_addr1,
                        func_name="set_value",
                        params={"value": hex(value3 * ICX_IN_LOOP)})

        # 6. assert get value: value3
        self._assert_get_value(self._accounts[0], score_addr1, "get_value", value3)

    def test_prev_deploy_reject(self):
        self._update_governance_score()

        # 1. install done
        value1 = 1
        score_addr1, tx_hash1, tx_hash2 = self._install_normal_score(value1)

        # 2. deploy update (wait audit)
        """
        def on_update(self, value: int) -> None:
            super().on_update()
            var = self._value.get()
            self._value.set(var + value)
        
        def set_value(self, value: int):
            self._value.set(value * 2)
            self.Changed(value)
        """
        value2 = 2
        tx_results: List['TransactionResult'] = self._deploy_score(score_name="update/sample_score",
                                                                   value=value2,
                                                                   to_=score_addr1)
        tx_hash3 = tx_results[0].tx_hash

        # new update deploy
        value3 = 3
        tx_results: List['TransactionResult'] = self._deploy_score(score_name="update/sample_score",
                                                                   value=value3,
                                                                   to_=score_addr1)
        tx_hash4 = tx_results[0].tx_hash

        # 3. assert get value: value1
        self._assert_get_value(self._accounts[0], score_addr1, "get_value", value1)

        # 4. accept SCORE : tx_hash3 (Fail)
        raise_exception_start_tag("test_prev_deploy_reject")
        self.reject_score(tx_hash=tx_hash3,
                          expected_status=False)
        raise_exception_end_tag("test_prev_deploy_reject")

        # 5. accept SCORE : tx_hash4
        self.accept_score(tx_hash=tx_hash4)

        # 6. assert get value: value1 + value3
        self._assert_get_value(self._accounts[0], score_addr1, "get_value", value1 + value3)

        # 7. set value: value3
        self.score_call(from_=self._accounts[0],
                        to_=score_addr1,
                        func_name="set_value",
                        params={"value": hex(value3 * ICX_IN_LOOP)})

        # 8. assert get value: 2 * value3
        self._assert_get_value(self._accounts[0], score_addr1, "get_value", 3 * value2)

    def test_prev_deploy_accept(self):
        self._update_governance_score()

        # 1. install done
        value1 = 1
        score_addr1, tx_hash1, tx_hash2 = self._install_normal_score(value1)

        # 2. deploy update (wait audit)
        """
        def on_update(self, value: int) -> None:
            super().on_update()
            var = self._value.get()
            self._value.set(var + value)
        
        def set_value(self, value: int):
            self._value.set(value * 2)
            self.Changed(value)
        """
        value2 = 2
        tx_results: List['TransactionResult'] = self._deploy_score(score_name="update/sample_score",
                                                                   value=value2,
                                                                   to_=score_addr1)
        tx_hash3 = tx_results[0].tx_hash

        # new update deploy
        value3 = 3
        tx_results: List['TransactionResult'] = self._deploy_score(score_name="update/sample_score",
                                                                   value=value3,
                                                                   to_=score_addr1)
        tx_hash4 = tx_results[0].tx_hash

        # 3. assert get value: value1
        self._assert_get_value(self._accounts[0], score_addr1, "get_value", value1)

        # 4. accept SCORE : tx_hash3 (Fail)
        raise_exception_start_tag("test_prev_deploy_accept")
        self.accept_score(tx_hash=tx_hash3,
                          expected_status=False)
        raise_exception_end_tag("test_prev_deploy_accept")

        # 5. accept SCORE : tx_hash4
        self.accept_score(tx_hash=tx_hash4)

        # 6. assert get value: value1 + value3
        self._assert_get_value(self._accounts[0], score_addr1, "get_value", value1 + value3)

        # 7. set value: value3
        self.score_call(from_=self._accounts[0],
                        to_=score_addr1,
                        func_name="set_value",
                        params={"value": hex(value3 * ICX_IN_LOOP)})

        # 8. assert get value: 2 * value3
        self._assert_get_value(self._accounts[0], score_addr1, "get_value", 3 * value2)

