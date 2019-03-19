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

from iconservice.base.address import ZERO_SCORE_ADDRESS, GOVERNANCE_SCORE_ADDRESS
from iconservice.base.exception import ExceptionCode
from tests import raise_exception_start_tag, raise_exception_end_tag
from tests.integrate_test.test_integrate_base import TestIntegrateBase

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from iconservice.base.address import Address


class TestIntegrateDeployUpdate(TestIntegrateBase):

    def _update_governance(self):
        tx = self._make_deploy_tx("test_builtin",
                                  "latest_version/governance",
                                  self._admin,
                                  GOVERNANCE_SCORE_ADDRESS)
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)

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

    def _deploy_score(self, score_path: str, value: int, update_score_addr: 'Address' = None) -> Any:
        address = ZERO_SCORE_ADDRESS
        if update_score_addr:
            address = update_score_addr

        tx = self._make_deploy_tx("test_deploy_scores",
                                  score_path,
                                  self._addr_array[0],
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

    def _install_normal_score(self, value: int):
        # 1. deploy

        tx_result = self._deploy_score("install/test_score", value)
        self.assertEqual(tx_result.status, int(True))
        score_addr1 = tx_result.score_address
        tx_hash1 = tx_result.tx_hash
        return score_addr1, tx_hash1

    def test_score(self):
        self._update_governance()

        # 1. install done
        value1 = 1 * self._icx_factor
        score_addr1, tx_hash1 = self._install_normal_score(value1)

        # 2. assert get value: value1
        self._assert_get_value(self._addr_array[0], score_addr1, "get_value", value1)

        # 3. deploy update
        """
        def on_update(self, value: int) -> None:
            super().on_update()
            var = self._value.get()
            self._value.set(var + value)

        def set_value(self, value: int):
            self._value.set(value * 2)
            self.Changed(value)
        """
        value2 = 2 * self._icx_factor
        tx_result = self._deploy_score("update/test_score", value2, score_addr1)
        self.assertEqual(tx_result.status, int(True))

        # 4. assert get value: value1 + value2
        self._assert_get_value(self._addr_array[0], score_addr1, "get_value", value1 + value2)

        # 5. set value: value2
        self._set_value(self._addr_array[0], score_addr1, "set_value", {"value": hex(value2)})

        # 6. assert get value: 2 * value2
        self._assert_get_value(self._addr_array[0], score_addr1, "get_value", 2 * value2)

    def test_invalid_owner(self):
        self._update_governance()

        # 1. install done
        value1 = 1 * self._icx_factor
        score_addr1, tx_hash1 = self._install_normal_score(value1)

        # 2. deploy update
        value2 = 2 * self._icx_factor
        tx1 = self._make_deploy_tx("test_deploy_scores",
                                   "update/test_score",
                                   self._addr_array[1],
                                   score_addr1,
                                   deploy_params={'value': hex(value2)})

        raise_exception_start_tag("test_invalid_owner1")
        prev_block, tx_results = self._make_and_req_block([tx1])
        raise_exception_end_tag("test_invalid_owner1")
        self._write_precommit_state(prev_block)

        self.assertEqual(tx_results[0].status, int(False))
        self.assertEqual(tx_results[0].failure.code, ExceptionCode.ACCESS_DENIED)
        self.assertEqual(tx_results[0].failure.message,
                         f'Invalid owner: {str(self._addr_array[0])} != {str(self._addr_array[1])}')

        # 3. assert get value: value1
        self._assert_get_value(self._addr_array[0], score_addr1, "get_value", value1)

        # 4. set value: value3
        value3 = 3 * self._icx_factor
        self._set_value(self._addr_array[0], score_addr1, "set_value", {"value": hex(value3)})

        # 5. assert get value: value3
        self._assert_get_value(self._addr_array[0], score_addr1, "get_value", value3)

    def test_score_no_zip(self):
        self._update_governance()

        # 1. install done
        value1 = 1 * self._icx_factor
        score_addr1, tx_hash1 = self._install_normal_score(value1)

        # 2. deploy update
        value2 = 2 * self._icx_factor
        tx1 = self._make_deploy_tx("test_deploy_scores",
                                   "update/test_score",
                                   self._addr_array[0],
                                   score_addr1,
                                   data=b'invalid',
                                   deploy_params={'value': hex(value2)})

        raise_exception_start_tag("test_score_no_zip")
        prev_block, tx_results = self._make_and_req_block([tx1])
        raise_exception_end_tag("test_score_no_zip")

        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(False))
        self.assertEqual(tx_results[0].failure.code, ExceptionCode.INVALID_PACKAGE)
        self.assertEqual(tx_results[0].failure.message, f'Bad zip file.')

        # 3. assert get value: value1
        self._assert_get_value(self._addr_array[0], score_addr1, "get_value", value1)

        # 4. set value: value3
        value3 = 3 * self._icx_factor
        self._set_value(self._addr_array[0], score_addr1, "set_value", {"value": hex(value3)})

        # 5. assert get value: value3
        self._assert_get_value(self._addr_array[0], score_addr1, "get_value", value3)

    def test_score_no_scorebase(self):
        self._update_governance()

        # 1. install done
        value1 = 1 * self._icx_factor
        score_addr1, tx_hash1 = self._install_normal_score(value1)

        # 2. deploy update
        value2 = 2 * self._icx_factor
        tx1 = self._make_deploy_tx("test_deploy_scores",
                                   "install/test_score_no_scorebase",
                                   self._addr_array[0],
                                   score_addr1,
                                   deploy_params={'value': hex(value2)})

        raise_exception_start_tag("test_score_no_scorebase")
        prev_block, tx_results = self._make_and_req_block([tx1])
        raise_exception_end_tag("test_score_no_scorebase")

        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(False))
        self.assertEqual(tx_results[0].failure.code, ExceptionCode.SYSTEM_ERROR)
        self.assertEqual(tx_results[0].failure.message, "'TestScore' object has no attribute 'owner'")

        # 3. assert get value: value1
        self._assert_get_value(self._addr_array[0], score_addr1, "get_value", value1)

        # 4. set value: value3
        value3 = 3 * self._icx_factor
        self._set_value(self._addr_array[0], score_addr1, "set_value", {"value": hex(value3)})

        # 5. assert get value: value3
        self._assert_get_value(self._addr_array[0], score_addr1, "get_value", value3)

    def test_score_on_update_error(self):
        self._update_governance()

        # 1. install done
        value1 = 1 * self._icx_factor
        score_addr1, tx_hash1 = self._install_normal_score(value1)

        # 2. deploy update
        value2 = 2 * self._icx_factor
        tx1 = self._make_deploy_tx("test_deploy_scores",
                                   "update/test_score_on_update_error",
                                   self._addr_array[0],
                                   score_addr1,
                                   deploy_params={'value': hex(value2)})

        raise_exception_start_tag("test_score_on_update_error")
        prev_block, tx_results = self._make_and_req_block([tx1])
        raise_exception_end_tag("test_score_on_update_error")

        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(False))
        self.assertEqual(tx_results[0].failure.code, ExceptionCode.SCORE_ERROR)
        self.assertEqual(tx_results[0].failure.message, "raise exception!")

        # 3. assert get value: value1
        self._assert_get_value(self._addr_array[0], score_addr1, "get_value", value1)

        # 4. set value: value3
        value3 = 3 * self._icx_factor
        self._set_value(self._addr_array[0], score_addr1, "set_value", {"value": hex(value3)})

        # 5. assert get value: value3
        self._assert_get_value(self._addr_array[0], score_addr1, "get_value", value3)

    def test_score_no_external_func(self):
        self._update_governance()

        # 1. install done
        value1 = 1 * self._icx_factor
        score_addr1, tx_hash1 = self._install_normal_score(value1)

        # 2. deploy update
        value2 = 2 * self._icx_factor
        tx1 = self._make_deploy_tx("test_deploy_scores",
                                   "install/test_score_no_external_func",
                                   self._addr_array[0],
                                   score_addr1,
                                   deploy_params={'value': hex(value2)})

        raise_exception_start_tag("test_score_no_external_func")
        prev_block, tx_results = self._make_and_req_block([tx1])
        raise_exception_end_tag("test_score_no_external_func")

        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(False))
        self.assertEqual(tx_results[0].failure.code, ExceptionCode.ILLEGAL_FORMAT)
        self.assertEqual(tx_results[0].failure.message, "There is no external method in the SCORE")

        # 3. assert get value: value1
        self._assert_get_value(self._addr_array[0], score_addr1, "get_value", value1)

        # 4. set value: value3
        value3 = 3 * self._icx_factor
        self._set_value(self._addr_array[0], score_addr1, "set_value", {"value": hex(value3)})

        # 5. assert get value: value3
        self._assert_get_value(self._addr_array[0], score_addr1, "get_value", value3)

    def test_score_with_korean_comments(self):
        self._update_governance()

        # 1. install done
        value1 = 1 * self._icx_factor
        score_addr1, tx_hash1 = self._install_normal_score(value1)

        # 2. deploy update
        value2 = 2 * self._icx_factor
        tx1 = self._make_deploy_tx("test_deploy_scores",
                                   "install/test_score_with_korean_comments",
                                   self._addr_array[0],
                                   score_addr1,
                                   deploy_params={'value': hex(value2)})

        raise_exception_start_tag("test_score_with_korean_comments")
        prev_block, tx_results = self._make_and_req_block([tx1])
        raise_exception_end_tag("test_score_with_korean_comments")

        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(False))
        self.assertEqual(tx_results[0].failure.code, ExceptionCode.SYSTEM_ERROR)

        # 3. assert get value: value1
        self._assert_get_value(self._addr_array[0], score_addr1, "get_value", value1)

        # 4. set value: value3
        value3 = 3 * self._icx_factor
        self._set_value(self._addr_array[0], score_addr1, "set_value", {"value": hex(value3)})

        # 5. assert get value: value3
        self._assert_get_value(self._addr_array[0], score_addr1, "get_value", value3)

    def test_score_no_python(self):
        self._update_governance()

        # 1. install done
        value1 = 1 * self._icx_factor
        score_addr1, tx_hash1 = self._install_normal_score(value1)

        # 2. deploy update
        value2 = 2 * self._icx_factor
        tx1 = self._make_deploy_tx("test_deploy_scores",
                                   "install/test_score_no_python",
                                   self._addr_array[0],
                                   score_addr1,
                                   deploy_params={'value': hex(value2)})

        raise_exception_start_tag("test_score_no_python")
        prev_block, tx_results = self._make_and_req_block([tx1])
        raise_exception_end_tag("test_score_no_python")

        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(False))
        self.assertEqual(tx_results[0].failure.code, ExceptionCode.SYSTEM_ERROR)

        # 3. assert get value: value1
        self._assert_get_value(self._addr_array[0], score_addr1, "get_value", value1)

        # 4. set value: value3
        value3 = 3 * self._icx_factor
        self._set_value(self._addr_array[0], score_addr1, "set_value", {"value": hex(value3)})

        # 5. assert get value: value3
        self._assert_get_value(self._addr_array[0], score_addr1, "get_value", value3)

    def test_score_tbears_mode(self):
        self._update_governance()

        # 1. install done
        value1 = 1 * self._icx_factor
        score_addr1, _ = self._install_normal_score(value1)

        # 2. deploy update
        value2 = 2 * self._icx_factor
        tx1 = self._make_deploy_tx("test_deploy_scores",
                                   "install/test_score",
                                   self._addr_array[0],
                                   score_addr1,
                                   deploy_params={'value': hex(value2)},
                                   is_sys=True)

        raise_exception_start_tag("test_score_tbears_mode")
        prev_block, tx_results = self._make_and_req_block([tx1])
        raise_exception_end_tag("test_score_tbears_mode")

        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(False))
        self.assertEqual(tx_results[0].failure.code, ExceptionCode.INVALID_PARAMETER)


if __name__ == '__main__':
    unittest.main()
