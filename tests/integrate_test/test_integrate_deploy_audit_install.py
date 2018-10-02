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
from iconservice.icon_constant import ConfigKey
from tests import raise_exception_start_tag, raise_exception_end_tag
from tests.integrate_test.test_integrate_base import TestIntegrateBase

from typing import TYPE_CHECKING, Any, Union

if TYPE_CHECKING:
    from iconservice.base.address import Address


class TestIntegrateDeployAuditInstall(TestIntegrateBase):

    def _make_init_config(self) -> dict:
        return {ConfigKey.SERVICE: {ConfigKey.SERVICE_AUDIT: True}}

    def _update_0_0_3_governance(self):
        tx = self._make_deploy_tx("test_builtin",
                                  "0_0_3/governance",
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
        self._update_0_0_3_governance()

        # 1. deploy (wait audit)
        value1 = 1 * self._icx_factor
        tx_result = self._deploy_score("install/test_score", value1)
        self.assertEqual(tx_result.status, int(True))
        score_addr1 = tx_result.score_address
        tx_hash1 = tx_result.tx_hash

        # 2. accpt SCORE : tx_hash1
        tx_result = self._accept_score(tx_hash1)
        self.assertEqual(tx_result.status, int(True))
        tx_hash2 = tx_result.tx_hash

        # assert SCORE status
        expect_ret = {
            'current': {
                'status': 'active',
                'deployTxHash': tx_hash1,
                'auditTxHash': tx_hash2}}
        self._assert_get_score_status(score_addr1, expect_ret)

        # 3. assert get value: value1
        self._assert_get_value(self._addr_array[0], score_addr1, "get_value", value1)

        # 4. set value: value2
        value2 = 2 * self._icx_factor
        self._set_value(self._addr_array[0], score_addr1, "set_value", {"value": hex(value2)})

        # 5. assert get value: value2
        self._assert_get_value(self._addr_array[0], score_addr1, "get_value", value2)

    def test_score_address_already_in_use(self):
        # 1. deploy same SCORE address (wait audit)
        timestamp = 1
        value1 = 1 * self._icx_factor
        tx1 = self._make_deploy_tx("test_deploy_scores",
                                   "install/test_score",
                                   self._addr_array[0],
                                   ZERO_SCORE_ADDRESS,
                                   timestamp_us=timestamp,
                                   deploy_params={'value': hex(value1)})
        tx2 = self._make_deploy_tx("test_deploy_scores",
                                   "install/test_score",
                                   self._addr_array[0],
                                   ZERO_SCORE_ADDRESS,
                                   timestamp_us=timestamp,
                                   deploy_params={'value': hex(value1)})

        raise_exception_start_tag("test_score_address_already_in_use1")
        prev_block, tx_results = self._make_and_req_block([tx1, tx2])
        raise_exception_end_tag("test_score_address_already_in_use1")

        self._write_precommit_state(prev_block)

        self.assertEqual(tx_results[0].status, int(True))
        score_addr1 = tx_results[0].score_address
        tx_hash1 = tx_results[0].tx_hash

        self.assertEqual(tx_results[1].status, int(False))
        self.assertEqual(tx_results[1].failure.code, ExceptionCode.SERVER_ERROR)
        self.assertEqual(tx_results[1].failure.message, f'SCORE address already in use: {str(score_addr1)}')
        tx_hash2 = tx_results[1].tx_hash

        # 2. accept SCORE : tx_hash1, tx_hash2
        tx3 = self._make_score_call_tx(self._admin,
                                       GOVERNANCE_SCORE_ADDRESS,
                                       'acceptScore',
                                       {"txHash": f'0x{bytes.hex(tx_hash1)}'})

        tx4 = self._make_score_call_tx(self._admin,
                                       GOVERNANCE_SCORE_ADDRESS,
                                       'acceptScore',
                                       {"txHash": f'0x{bytes.hex(tx_hash2)}'})

        raise_exception_start_tag("test_score_address_already_in_use2")
        prev_block, tx_results = self._make_and_req_block([tx3, tx4])
        raise_exception_end_tag("test_score_address_already_in_use2")

        self._write_precommit_state(prev_block)

        self.assertEqual(tx_results[0].status, int(True))

        self.assertEqual(tx_results[1].status, int(False))
        self.assertEqual(tx_results[1].failure.code, ExceptionCode.SCORE_ERROR)
        self.assertEqual(tx_results[1].failure.message, 'Invalid txHash')

        # 3. assert get value: value1
        self._assert_get_value(self._addr_array[0], score_addr1, "get_value", value1)

        # 4. set value: value2
        value2 = 2 * self._icx_factor
        self._set_value(self._addr_array[0], score_addr1, "set_value", {"value": hex(value2)})

        # 5. assert get value: value2
        self._assert_get_value(self._addr_array[0], score_addr1, "get_value", value2)

    def test_score_address_already_in_use_update_governance(self):
        self._update_0_0_3_governance()

        # 1. deploy same SCORE address (wait audit)
        timestamp = 1
        value1 = 1 * self._icx_factor
        tx1 = self._make_deploy_tx("test_deploy_scores",
                                   "install/test_score",
                                   self._addr_array[0],
                                   ZERO_SCORE_ADDRESS,
                                   timestamp_us=timestamp,
                                   deploy_params={'value': hex(value1)})
        tx2 = self._make_deploy_tx("test_deploy_scores",
                                   "install/test_score",
                                   self._addr_array[0],
                                   ZERO_SCORE_ADDRESS,
                                   timestamp_us=timestamp,
                                   deploy_params={'value': hex(value1)})

        raise_exception_start_tag("test_score_address_already_in_use1")
        prev_block, tx_results = self._make_and_req_block([tx1, tx2])
        raise_exception_end_tag("test_score_address_already_in_use1")

        self._write_precommit_state(prev_block)

        self.assertEqual(tx_results[0].status, int(True))
        score_addr1 = tx_results[0].score_address
        tx_hash1 = tx_results[0].tx_hash

        self.assertEqual(tx_results[1].status, int(False))
        self.assertEqual(tx_results[1].failure.code, ExceptionCode.SERVER_ERROR)
        self.assertEqual(tx_results[1].failure.message, f'SCORE address already in use: {str(score_addr1)}')
        tx_hash2 = tx_results[1].tx_hash

        # 2. accept SCORE : tx_hash1, tx_hash2
        tx3 = self._make_score_call_tx(self._admin,
                                       GOVERNANCE_SCORE_ADDRESS,
                                       'acceptScore',
                                       {"txHash": f'0x{bytes.hex(tx_hash1)}'})

        tx4 = self._make_score_call_tx(self._admin,
                                       GOVERNANCE_SCORE_ADDRESS,
                                       'acceptScore',
                                       {"txHash": f'0x{bytes.hex(tx_hash2)}'})

        raise_exception_start_tag("test_score_address_already_in_use2")
        prev_block, tx_results = self._make_and_req_block([tx3, tx4])
        raise_exception_end_tag("test_score_address_already_in_use2")

        self._write_precommit_state(prev_block)

        self.assertEqual(tx_results[0].status, int(True))

        self.assertEqual(tx_results[1].status, int(False))
        self.assertEqual(tx_results[1].failure.code, ExceptionCode.SCORE_ERROR)
        self.assertEqual(tx_results[1].failure.message, 'Invalid txHash: None')

        # 3. assert get value: value1
        self._assert_get_value(self._addr_array[0], score_addr1, "get_value", value1)

        # 4. set value: value2
        value2 = 2 * self._icx_factor
        self._set_value(self._addr_array[0], score_addr1, "set_value", {"value": hex(value2)})

        # 5. assert get value: value2
        self._assert_get_value(self._addr_array[0], score_addr1, "get_value", value2)

    def test_score_no_zip(self):
        self._update_0_0_3_governance()

        # 1. deploy same SCORE address (wait audit)
        value1 = 1 * self._icx_factor
        tx1 = self._make_deploy_tx("test_deploy_scores",
                                   "install/test_score",
                                   self._addr_array[0],
                                   ZERO_SCORE_ADDRESS,
                                   data=b'invalid',
                                   deploy_params={'value': hex(value1)})

        prev_block, tx_results = self._make_and_req_block([tx1])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))
        tx_hash1 = tx_results[0].tx_hash

        # 2. accept SCORE : tx_hash1
        raise_exception_start_tag("test_score_no_zip")
        tx_result = self._accept_score(tx_hash1)
        raise_exception_end_tag("test_score_no_zip")
        self.assertEqual(tx_result.status, int(False))
        self.assertEqual(tx_result.failure.code, ExceptionCode.INVALID_PARAMS)
        self.assertEqual(tx_result.failure.message, f'Bad zip file.')

    def test_score_no_scorebase(self):
        self._update_0_0_3_governance()

        # 1. deploy same SCORE address (wait audit)
        value1 = 1 * self._icx_factor
        tx_result = self._deploy_score("install/test_score_no_scorebase", value1)
        tx_hash1 = tx_result.tx_hash

        # 2. accept SCORE : tx_hash1
        raise_exception_start_tag("test_score_no_scorebase")
        tx_result = self._accept_score(tx_hash1)
        raise_exception_end_tag("test_score_no_scorebase")

        self.assertEqual(tx_result.status, int(False))
        self.assertEqual(tx_result.failure.code, ExceptionCode.SERVER_ERROR)
        self.assertEqual(tx_result.failure.message, "'TestScore' object has no attribute 'owner'")

    def test_score_on_install_error(self):
        self._update_0_0_3_governance()

        # 1. deploy same SCORE address (wait audit)
        value1 = 1 * self._icx_factor
        tx_result = self._deploy_score("install/test_score_on_install_error", value1)
        tx_hash1 = tx_result.tx_hash

        # 2. accept SCORE : tx_hash1
        raise_exception_start_tag("test_score_on_install_error")
        tx_result = self._accept_score(tx_hash1)
        raise_exception_end_tag("test_score_on_install_error")

        self.assertEqual(tx_result.status, int(False))
        self.assertEqual(tx_result.failure.code, ExceptionCode.SCORE_ERROR)
        self.assertEqual(tx_result.failure.message, "raise exception!")

    def test_score_no_external_func(self):
        self._update_0_0_3_governance()

        # 1. deploy same SCORE address (wait audit)
        value1 = 1 * self._icx_factor
        tx_result = self._deploy_score("install/test_score_no_external_func", value1)
        tx_hash1 = tx_result.tx_hash

        # 2. accept SCORE : tx_hash1
        raise_exception_start_tag("test_score_no_external_func")
        tx_result = self._accept_score(tx_hash1)
        raise_exception_end_tag("test_score_no_external_func")

        self.assertEqual(tx_result.status, int(False))
        self.assertEqual(tx_result.failure.code, ExceptionCode.SCORE_ERROR)
        self.assertEqual(tx_result.failure.message, "this score has no external functions")

    def test_score_with_korean_comments(self):
        self._update_0_0_3_governance()

        # 1. deploy same SCORE address (wait audit)
        value1 = 1 * self._icx_factor
        tx_result = self._deploy_score("install/test_score_with_korean_comments", value1)
        tx_hash1 = tx_result.tx_hash

        # 2. accept SCORE : tx_hash1
        raise_exception_start_tag("test_score_with_korean_comments")
        tx_result = self._accept_score(tx_hash1)
        raise_exception_end_tag("test_score_with_korean_comments")

        self.assertEqual(tx_result.status, int(False))
        self.assertEqual(tx_result.failure.code, ExceptionCode.SERVER_ERROR)

    def test_score_no_python(self):
        self._update_0_0_3_governance()

        # 1. deploy same SCORE address (wait audit)
        value1 = 1 * self._icx_factor
        tx_result = self._deploy_score("install/test_score_no_python", value1)
        tx_hash1 = tx_result.tx_hash

        # 2. accept SCORE : tx_hash1
        raise_exception_start_tag("test_score_no_python")
        tx_result = self._accept_score(tx_hash1)
        raise_exception_end_tag("test_score_no_python")

        self.assertEqual(tx_result.status, int(False))
        self.assertEqual(tx_result.failure.code, ExceptionCode.SERVER_ERROR)


if __name__ == '__main__':
    unittest.main()
