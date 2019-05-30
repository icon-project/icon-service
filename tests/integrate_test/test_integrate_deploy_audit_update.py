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
from typing import TYPE_CHECKING, Any, Union

from iconservice.base.address import ZERO_SCORE_ADDRESS, GOVERNANCE_SCORE_ADDRESS
from iconservice.base.exception import ExceptionCode
from iconservice.icon_constant import ConfigKey
from tests import raise_exception_start_tag, raise_exception_end_tag
from tests.integrate_test.test_integrate_base import TestIntegrateBase, LATEST_GOVERNANCE

if TYPE_CHECKING:
    from iconservice.base.address import Address


class TestIntegrateDeployAuditUpdate(TestIntegrateBase):

    def _make_init_config(self) -> dict:
        return {ConfigKey.SERVICE: {ConfigKey.SERVICE_AUDIT: True}}

    def _update_governance(self):
        tx = self._make_deploy_tx("sample_builtin",
                                  "latest_version/governance",
                                  self._admin,
                                  GOVERNANCE_SCORE_ADDRESS)
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        tx_hash1 = tx_results[0].tx_hash
        self._accept_score(tx_hash1)

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

        tx = self._make_deploy_tx("sample_deploy_scores",
                                  score_path,
                                  self._addr_array[0],
                                  address,
                                  deploy_params={'value': hex(value)})

        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        return tx_results[0]

    def _accept_score(self, tx_hash: Union[bytes, str]):
        if isinstance(tx_hash, bytes):
            tx_hash_str = f'0x{bytes.hex(tx_hash)}'
        else:
            tx_hash_str = tx_hash
        tx = self._make_score_call_tx(self._admin,
                                      GOVERNANCE_SCORE_ADDRESS,
                                      'acceptScore',
                                      {"txHash": tx_hash_str})
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        return tx_results[0]

    def _reject_score(self, tx_hash: Union[bytes, str]):
        if isinstance(tx_hash, bytes):
            tx_hash_str = f'0x{bytes.hex(tx_hash)}'
        else:
            tx_hash_str = tx_hash
        tx = self._make_score_call_tx(self._admin,
                                      GOVERNANCE_SCORE_ADDRESS,
                                      'rejectScore',
                                      {"txHash": tx_hash_str, "reason": ""})
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
        # 1. deploy (wait audit)

        tx_result = self._deploy_score("install/sample_score", value)
        self.assertEqual(tx_result.status, int(True))
        score_addr1 = tx_result.score_address
        tx_hash1 = tx_result.tx_hash

        # 2. accpt SCORE : tx_hash1
        tx_result = self._accept_score(tx_hash1)
        self.assertEqual(tx_result.status, int(True))
        tx_hash2 = tx_result.tx_hash

        return score_addr1, tx_hash1, tx_hash2

    def test_score(self):
        self._update_governance()

        # 1. install done
        value1 = 1 * self._icx_factor
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
        value2 = 2 * self._icx_factor
        tx_result = self._deploy_score("update/sample_score", value2, score_addr1)
        self.assertEqual(tx_result.status, int(True))
        tx_hash3 = tx_result.tx_hash

        # 3. assert get value: value1
        self._assert_get_value(self._addr_array[0], score_addr1, "get_value", value1)

        # 4. accept SCORE : tx_hash3
        tx_result = self._accept_score(tx_hash3)
        self.assertEqual(tx_result.status, int(True))

        # 5. assert get value: value1 + value2
        self._assert_get_value(self._addr_array[0], score_addr1, "get_value", value1 + value2)

        # 6. set value: value2
        self._set_value(self._addr_array[0], score_addr1, "set_value", {"value": hex(value2)})

        # 7. assert get value: 2 * value2
        self._assert_get_value(self._addr_array[0], score_addr1, "get_value", 2 * value2)

    def test_invalid_owner(self):

        # 1. install done
        value1 = 1 * self._icx_factor
        score_addr1, tx_hash1, tx_hash2 = self._install_normal_score(value1)

        # 2. deploy update (wait audit)
        value2 = 2 * self._icx_factor
        tx1 = self._make_deploy_tx("sample_deploy_scores",
                                   "update/sample_score",
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
        tx_hash2 = tx_results[0].tx_hash

        # 3. accept SCORE : tx_hash2
        raise_exception_start_tag("test_invalid_owner2")
        tx_result = self._accept_score(tx_hash2)
        raise_exception_end_tag("test_invalid_owner2")
        self.assertEqual(tx_result.status, int(False))
        self.assertEqual(tx_result.failure.code, ExceptionCode.SCORE_ERROR)
        self.assertEqual(tx_result.failure.message, "Invalid txHash")

        # 4. assert get value: value1
        self._assert_get_value(self._addr_array[0], score_addr1, "get_value", value1)

        # 5. set value: value3
        value3 = 3 * self._icx_factor
        self._set_value(self._addr_array[0], score_addr1, "set_value", {"value": hex(value3)})

        # 6. assert get value: value3
        self._assert_get_value(self._addr_array[0], score_addr1, "get_value", value3)

    def test_invalid_owner_update_governance(self):
        self._update_governance()

        # 1. install done
        value1 = 1 * self._icx_factor
        score_addr1, tx_hash1, tx_hash2 = self._install_normal_score(value1)

        # 2. deploy update (wait audit)
        value2 = 2 * self._icx_factor
        tx1 = self._make_deploy_tx("sample_deploy_scores",
                                   "update/sample_score",
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
        tx_hash2 = tx_results[0].tx_hash

        # 3. accept SCORE : tx_hash2
        raise_exception_start_tag("test_invalid_owner2")
        tx_result = self._accept_score(tx_hash2)
        raise_exception_end_tag("test_invalid_owner2")
        self.assertEqual(tx_result.status, int(False))
        self.assertEqual(tx_result.failure.code, ExceptionCode.SCORE_ERROR)
        self.assertEqual(tx_result.failure.message, "Invalid txHash: None")

        # 4. assert get value: value1
        self._assert_get_value(self._addr_array[0], score_addr1, "get_value", value1)

        # 5. set value: value3
        value3 = 3 * self._icx_factor
        self._set_value(self._addr_array[0], score_addr1, "set_value", {"value": hex(value3)})

        # 6. assert get value: value3
        self._assert_get_value(self._addr_array[0], score_addr1, "get_value", value3)

    def test_score_no_zip(self):
        self._update_governance()

        # 1. install done
        value1 = 1 * self._icx_factor
        score_addr1, tx_hash1, tx_hash2 = self._install_normal_score(value1)

        # 2. deploy update (wait audit)
        tx1 = self._make_deploy_tx("sample_deploy_scores",
                                   "update/sample_score",
                                   self._addr_array[0],
                                   score_addr1,
                                   data=b'invalid',
                                   deploy_params={'value': hex(value1)})

        prev_block, tx_results = self._make_and_req_block([tx1])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))
        tx_hash2 = tx_results[0].tx_hash

        # 3. accept SCORE : tx_hash2
        raise_exception_start_tag("test_score_no_zip")
        tx_result = self._accept_score(tx_hash2)
        raise_exception_end_tag("test_score_no_zip")

        self.assertEqual(tx_result.status, int(False))
        self.assertEqual(tx_result.failure.code, ExceptionCode.INVALID_PACKAGE)
        self.assertEqual(tx_result.failure.message, f'Bad zip file.')

        # 4. assert get value: value1
        self._assert_get_value(self._addr_array[0], score_addr1, "get_value", value1)

        # 5. set value: value3
        value3 = 3 * self._icx_factor
        self._set_value(self._addr_array[0], score_addr1,  "set_value", {"value": hex(value3)})

        # 6. assert get value: value3
        self._assert_get_value(self._addr_array[0], score_addr1, "get_value", value3)

    def test_score_no_scorebase(self):
        self._update_governance()

        # 1. install done
        value1 = 1 * self._icx_factor
        score_addr1, tx_hash1, tx_hash2 = self._install_normal_score(value1)

        # 2. deploy update (wait audit)
        tx1 = self._make_deploy_tx("sample_deploy_scores",
                                   "install/sample_score_no_scorebase",
                                   self._addr_array[0],
                                   score_addr1,
                                   deploy_params={'value': hex(value1)})

        prev_block, tx_results = self._make_and_req_block([tx1])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))
        tx_hash2 = tx_results[0].tx_hash

        # 3. accept SCORE : tx_hash2
        raise_exception_start_tag("test_score_no_scorebase")
        tx_result = self._accept_score(tx_hash2)
        raise_exception_end_tag("test_score_no_scorebase")

        self.assertEqual(tx_result.status, int(False))
        self.assertEqual(tx_result.failure.code, ExceptionCode.SYSTEM_ERROR)
        self.assertEqual(tx_result.failure.message, "'SampleScore' object has no attribute 'owner'")

        # 4. assert get value: value1
        self._assert_get_value(self._addr_array[0], score_addr1, "get_value", value1)

        # 5. set value: value3
        value3 = 3 * self._icx_factor
        self._set_value(self._addr_array[0], score_addr1, "set_value", {"value": hex(value3)})

        # 6. assert get value: value3
        self._assert_get_value(self._addr_array[0], score_addr1, "get_value", value3)

    def test_score_on_update_error(self):
        self._update_governance()

        # 1. install done
        value1 = 1 * self._icx_factor
        score_addr1, tx_hash1, tx_hash2 = self._install_normal_score(value1)

        # 2. deploy update (wait audit)
        tx1 = self._make_deploy_tx("sample_deploy_scores",
                                   "update/sample_score_on_update_error",
                                   self._addr_array[0],
                                   score_addr1,
                                   deploy_params={'value': hex(value1)})

        prev_block, tx_results = self._make_and_req_block([tx1])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))
        tx_hash2 = tx_results[0].tx_hash

        # 3. accept SCORE : tx_hash2
        raise_exception_start_tag("test_score_on_update_error")
        tx_result = self._accept_score(tx_hash2)
        raise_exception_end_tag("test_score_on_update_error")

        self.assertEqual(tx_result.status, int(False))
        self.assertEqual(tx_result.failure.code, ExceptionCode.SCORE_ERROR)
        self.assertEqual(tx_result.failure.message, "raise exception!")

        # 4. assert get value: value1
        self._assert_get_value(self._addr_array[0], score_addr1, "get_value", value1)

        # 5. set value: value3
        value3 = 3 * self._icx_factor
        self._set_value(self._addr_array[0], score_addr1, "set_value", {"value": hex(value3)})

        # 6. assert get value: value3
        self._assert_get_value(self._addr_array[0], score_addr1, "get_value", value3)

    def test_score_no_external_func(self):
        self._update_governance()

        # 1. install done
        value1 = 1 * self._icx_factor
        score_addr1, tx_hash1, tx_hash2 = self._install_normal_score(value1)
        print(f'tx_hash1: {tx_hash1.hex()}\ntx_hash2: {tx_hash2.hex()}')

        # 2. deploy update (wait audit)
        tx1 = self._make_deploy_tx("sample_deploy_scores",
                                   "install/sample_score_no_external_func",
                                   self._addr_array[0],
                                   score_addr1,
                                   deploy_params={'value': hex(value1)})

        prev_block, tx_results = self._make_and_req_block([tx1])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))
        tx_hash2 = tx_results[0].tx_hash
        print(f'tx_hash3: {tx_hash2.hex()}')

        # 3. accept SCORE : tx_hash2
        raise_exception_start_tag("test_score_no_external_func")
        tx_result = self._accept_score(tx_hash2)
        raise_exception_end_tag("test_score_no_external_func")

        self.assertEqual(tx_result.status, int(False))
        self.assertEqual(tx_result.failure.code, ExceptionCode.ILLEGAL_FORMAT)
        self.assertEqual(tx_result.failure.message, "There is no external method in the SCORE")

        # 4. assert get value: value1
        self._assert_get_value(self._addr_array[0], score_addr1, "get_value", value1)

        # 5. set value: value3
        value3 = 3 * self._icx_factor
        self._set_value(self._addr_array[0], score_addr1, "set_value", {"value": hex(value3)})

        # 6. assert get value: value3
        self._assert_get_value(self._addr_array[0], score_addr1, "get_value", value3)

    def test_score_with_korean_comments(self):
        self._update_governance()

        # 1. install done
        value1 = 1 * self._icx_factor
        score_addr1, tx_hash1, tx_hash2 = self._install_normal_score(value1)

        # 2. deploy update (wait audit)
        tx1 = self._make_deploy_tx("sample_deploy_scores",
                                   "install/sample_score_with_korean_comments",
                                   self._addr_array[0],
                                   score_addr1,
                                   deploy_params={'value': hex(value1)})

        prev_block, tx_results = self._make_and_req_block([tx1])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))
        tx_hash2 = tx_results[0].tx_hash

        # 3. accept SCORE : tx_hash2
        raise_exception_start_tag("test_score_with_korean_comments")
        tx_result = self._accept_score(tx_hash2)
        raise_exception_end_tag("test_score_with_korean_comments")

        self.assertEqual(tx_result.status, int(False))
        self.assertEqual(tx_result.failure.code, ExceptionCode.SYSTEM_ERROR)

        # 4. assert get value: value1
        self._assert_get_value(self._addr_array[0], score_addr1, "get_value", value1)

        # 5. set value: value3
        value3 = 3 * self._icx_factor
        self._set_value(self._addr_array[0], score_addr1, "set_value", {"value": hex(value3)})

        # 6. assert get value: value3
        self._assert_get_value(self._addr_array[0], score_addr1, "get_value", value3)

    def test_score_no_python(self):
        self._update_governance()

        # 1. install done
        value1 = 1 * self._icx_factor
        score_addr1, tx_hash1, tx_hash2 = self._install_normal_score(value1)

        # 2. deploy update (wait audit)
        tx1 = self._make_deploy_tx("sample_deploy_scores",
                                   "install/sample_score_no_python",
                                   self._addr_array[0],
                                   score_addr1,
                                   deploy_params={'value': hex(value1)})

        prev_block, tx_results = self._make_and_req_block([tx1])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))
        tx_hash2 = tx_results[0].tx_hash

        # 3. accept SCORE : tx_hash2
        raise_exception_start_tag("test_score_no_python")
        tx_result = self._accept_score(tx_hash2)
        raise_exception_end_tag("test_score_no_python")

        self.assertEqual(tx_result.status, int(False))
        self.assertEqual(tx_result.failure.code, ExceptionCode.SYSTEM_ERROR)

        # 4. assert get value: value1
        self._assert_get_value(self._addr_array[0], score_addr1, "get_value", value1)

        # 5. set value: value3
        value3 = 3 * self._icx_factor
        self._set_value(self._addr_array[0], score_addr1, "set_value", {"value": hex(value3)})

        # 6. assert get value: value3
        self._assert_get_value(self._addr_array[0], score_addr1, "get_value", value3)

    def test_prev_deploy_reject(self):
        self._update_governance()

        # 1. install done
        value1 = 1 * self._icx_factor
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
        value2 = 2 * self._icx_factor
        tx_result = self._deploy_score("update/sample_score", value2, score_addr1)
        self.assertEqual(tx_result.status, int(True))
        tx_hash3 = tx_result.tx_hash

        # new update deploy
        value3 = 3 * self._icx_factor
        tx_result = self._deploy_score("update/sample_score", value3, score_addr1)
        self.assertEqual(tx_result.status, int(True))
        tx_hash4 = tx_result.tx_hash

        # 3. assert get value: value1
        self._assert_get_value(self._addr_array[0], score_addr1, "get_value", value1)

        # 4. accept SCORE : tx_hash3 (Fail)
        raise_exception_start_tag("test_prev_deploy_reject")
        tx_result = self._reject_score(tx_hash3)
        raise_exception_start_tag("test_prev_deploy_reject")
        self.assertEqual(tx_result.status, int(False))

        # 5. accept SCORE : tx_hash4
        tx_result = self._accept_score(tx_hash4)
        self.assertEqual(tx_result.status, int(True))

        # 6. assert get value: value1 + value3
        self._assert_get_value(self._addr_array[0], score_addr1, "get_value", value1 + value3)

        # 7. set value: value3
        self._set_value(self._addr_array[0], score_addr1, "set_value", {"value": hex(value3)})

        # 8. assert get value: 2 * value3
        self._assert_get_value(self._addr_array[0], score_addr1, "get_value", 3 * value2)

    def test_prev_deploy_accept(self):
        self._update_governance()

        # 1. install done
        value1 = 1 * self._icx_factor
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
        value2 = 2 * self._icx_factor
        tx_result = self._deploy_score("update/sample_score", value2, score_addr1)
        self.assertEqual(tx_result.status, int(True))
        tx_hash3 = tx_result.tx_hash

        # new update deploy
        value3 = 3 * self._icx_factor
        tx_result = self._deploy_score("update/sample_score", value3, score_addr1)
        self.assertEqual(tx_result.status, int(True))
        tx_hash4 = tx_result.tx_hash

        # 3. assert get value: value1
        self._assert_get_value(self._addr_array[0], score_addr1, "get_value", value1)

        # 4. accept SCORE : tx_hash3 (Fail)
        raise_exception_start_tag("test_prev_deploy_accept")
        tx_result = self._accept_score(tx_hash3)
        raise_exception_start_tag("test_prev_deploy_accept")
        self.assertEqual(tx_result.status, int(False))

        # 5. accept SCORE : tx_hash4
        tx_result = self._accept_score(tx_hash4)
        self.assertEqual(tx_result.status, int(True))

        # 6. assert get value: value1 + value3
        self._assert_get_value(self._addr_array[0], score_addr1, "get_value", value1 + value3)

        # 7. set value: value3
        self._set_value(self._addr_array[0], score_addr1, "set_value", {"value": hex(value3)})

        # 8. assert get value: 2 * value3
        self._assert_get_value(self._addr_array[0], score_addr1, "get_value", 3 * value2)


if __name__ == '__main__':
    unittest.main()
