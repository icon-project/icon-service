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


class TestIntegrateDeployAuditInstall(TestIntegrateBase):

    def _make_init_config(self) -> dict:
        return {ConfigKey.SERVICE: {ConfigKey.SERVICE_AUDIT: True}}

    def test_score(self):
        value1 = 1 * self._icx_factor
        tx1 = self._make_deploy_tx("test_deploy_scores",
                                   "install/test_score",
                                   self._addr_array[0],
                                   ZERO_SCORE_ADDRESS,
                                   deploy_params={'value': hex(value1)})

        prev_block, tx_results = self._make_and_req_block([tx1])

        self._write_precommit_state(prev_block)

        self.assertEqual(tx_results[0].status, int(True))
        score_addr1 = tx_results[0].score_address
        tx_hash1 = tx_results[0].tx_hash

        tx2 = self._make_score_call_tx(self._admin,
                                       GOVERNANCE_SCORE_ADDRESS,
                                       'acceptScore',
                                       {"txHash": f'0x{bytes.hex(tx_hash1)}'})

        prev_block, tx_results = self._make_and_req_block([tx2])

        self._write_precommit_state(prev_block)

        self.assertEqual(tx_results[0].status, int(True))

        query_request = {
            "version": self._version,
            "from": self._admin,
            "to": score_addr1,
            "dataType": "call",
            "data": {
                "method": "get_value",
                "params": {}
            }
        }
        response = self._query(query_request)
        self.assertEqual(response, value1)

        value2 = 2 * self._icx_factor
        tx3 = self._make_score_call_tx(self._addr_array[0],
                                       score_addr1,
                                       'set_value',
                                       {"value": hex(value2)})

        prev_block, tx_results = self._make_and_req_block([tx3])
        self.assertEqual(tx_results[0].status, int(True))

        self._write_precommit_state(prev_block)

        response = self._query(query_request)
        self.assertEqual(response, value2)

    def test_score_address_already_in_use(self):
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

        query_request = {
            "version": self._version,
            "from": self._admin,
            "to": score_addr1,
            "dataType": "call",
            "data": {
                "method": "get_value",
                "params": {}
            }
        }
        response = self._query(query_request)
        self.assertEqual(response, value1)

        value2 = 2 * self._icx_factor
        tx5 = self._make_score_call_tx(self._addr_array[0],
                                       score_addr1,
                                       'set_value',
                                       {"value": hex(value2)})

        prev_block, tx_results = self._make_and_req_block([tx5])

        self._write_precommit_state(prev_block)

        self.assertEqual(tx_results[0].status, int(True))

        response = self._query(query_request)
        self.assertEqual(response, value2)

    def test_score_no_zip(self):
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

        tx2 = self._make_score_call_tx(self._admin,
                                       GOVERNANCE_SCORE_ADDRESS,
                                       'acceptScore',
                                       {"txHash": f'0x{bytes.hex(tx_hash1)}'})

        raise_exception_start_tag("test_score_no_zip")
        prev_block, tx_results = self._make_and_req_block([tx2])
        raise_exception_end_tag("test_score_no_zip")

        self._write_precommit_state(prev_block)

        self.assertEqual(tx_results[0].status, int(False))
        self.assertEqual(tx_results[0].failure.code, ExceptionCode.INVALID_PARAMS)
        self.assertEqual(tx_results[0].failure.message, f'Bad zip file.')

    def test_score_no_scorebase(self):
        value1 = 1 * self._icx_factor

        tx1 = self._make_deploy_tx("test_deploy_scores",
                                   "install/test_score_no_scorebase",
                                   self._addr_array[0],
                                   ZERO_SCORE_ADDRESS,
                                   deploy_params={'value': hex(value1)})

        prev_block, tx_results = self._make_and_req_block([tx1])

        self._write_precommit_state(prev_block)

        self.assertEqual(tx_results[0].status, int(True))
        tx_hash1 = tx_results[0].tx_hash

        tx2 = self._make_score_call_tx(self._admin,
                                       GOVERNANCE_SCORE_ADDRESS,
                                       'acceptScore',
                                       {"txHash": f'0x{bytes.hex(tx_hash1)}'})

        raise_exception_start_tag("test_score_no_scorebase")
        prev_block, tx_results = self._make_and_req_block([tx2])
        raise_exception_end_tag("test_score_no_scorebase")

        self._write_precommit_state(prev_block)

        self.assertEqual(tx_results[0].status, int(False))
        self.assertEqual(tx_results[0].failure.code, ExceptionCode.SERVER_ERROR)
        self.assertEqual(tx_results[0].failure.message, "'TestScore' object has no attribute 'owner'")

    def test_score_on_install_error(self):
        value1 = 1 * self._icx_factor

        tx1 = self._make_deploy_tx("test_deploy_scores",
                                   "install/test_score_on_install_error",
                                   self._addr_array[0],
                                   ZERO_SCORE_ADDRESS,
                                   deploy_params={'value': hex(value1)})

        prev_block, tx_results = self._make_and_req_block([tx1])

        self._write_precommit_state(prev_block)

        self.assertEqual(tx_results[0].status, int(True))
        tx_hash1 = tx_results[0].tx_hash

        tx2 = self._make_score_call_tx(self._admin,
                                       GOVERNANCE_SCORE_ADDRESS,
                                       'acceptScore',
                                       {"txHash": f'0x{bytes.hex(tx_hash1)}'})

        raise_exception_start_tag("test_score_on_install_error")
        prev_block, tx_results = self._make_and_req_block([tx2])
        raise_exception_end_tag("test_score_on_install_error")

        self._write_precommit_state(prev_block)

        self.assertEqual(tx_results[0].status, int(False))
        self.assertEqual(tx_results[0].failure.code, ExceptionCode.SCORE_ERROR)
        self.assertEqual(tx_results[0].failure.message, "raise exception!")

    def test_score_no_external_func(self):
        value1 = 1 * self._icx_factor

        tx1 = self._make_deploy_tx("test_deploy_scores",
                                   "install/test_score_no_external_func",
                                   self._addr_array[0],
                                   ZERO_SCORE_ADDRESS,
                                   deploy_params={'value': hex(value1)})

        prev_block, tx_results = self._make_and_req_block([tx1])

        self._write_precommit_state(prev_block)

        self.assertEqual(tx_results[0].status, int(True))
        tx_hash1 = tx_results[0].tx_hash

        tx2 = self._make_score_call_tx(self._admin,
                                       GOVERNANCE_SCORE_ADDRESS,
                                       'acceptScore',
                                       {"txHash": f'0x{bytes.hex(tx_hash1)}'})

        raise_exception_start_tag("test_score_no_external_func")
        prev_block, tx_results = self._make_and_req_block([tx2])
        raise_exception_end_tag("test_score_no_external_func")

        self._write_precommit_state(prev_block)

        self.assertEqual(tx_results[0].status, int(False))
        self.assertEqual(tx_results[0].failure.code, ExceptionCode.SCORE_ERROR)
        self.assertEqual(tx_results[0].failure.message, "this score has no external functions")

    def test_score_with_korean_comments(self):
        value1 = 1 * self._icx_factor

        tx1 = self._make_deploy_tx("test_deploy_scores",
                                   "install/test_score_with_korean_comments",
                                   self._addr_array[0],
                                   ZERO_SCORE_ADDRESS,
                                   deploy_params={'value': hex(value1)})

        prev_block, tx_results = self._make_and_req_block([tx1])

        self._write_precommit_state(prev_block)

        self.assertEqual(tx_results[0].status, int(True))
        tx_hash1 = tx_results[0].tx_hash

        tx2 = self._make_score_call_tx(self._admin,
                                       GOVERNANCE_SCORE_ADDRESS,
                                       'acceptScore',
                                       {"txHash": f'0x{bytes.hex(tx_hash1)}'})

        raise_exception_start_tag("test_score_with_korean_comments")
        prev_block, tx_results = self._make_and_req_block([tx2])
        raise_exception_end_tag("test_score_with_korean_comments")

        self._write_precommit_state(prev_block)

        self.assertEqual(tx_results[0].status, int(False))
        self.assertEqual(tx_results[0].failure.code, ExceptionCode.SERVER_ERROR)

    def test_score_no_python(self):
        value1 = 1 * self._icx_factor

        tx1 = self._make_deploy_tx("test_deploy_scores",
                                   "install/test_score_no_python",
                                   self._addr_array[0],
                                   ZERO_SCORE_ADDRESS,
                                   deploy_params={'value': hex(value1)})

        prev_block, tx_results = self._make_and_req_block([tx1])

        self._write_precommit_state(prev_block)

        self.assertEqual(tx_results[0].status, int(True))
        tx_hash1 = tx_results[0].tx_hash

        tx2 = self._make_score_call_tx(self._admin,
                                       GOVERNANCE_SCORE_ADDRESS,
                                       'acceptScore',
                                       {"txHash": f'0x{bytes.hex(tx_hash1)}'})

        raise_exception_start_tag("test_score_no_python")
        prev_block, tx_results = self._make_and_req_block([tx2])
        raise_exception_end_tag("test_score_no_python")

        self._write_precommit_state(prev_block)

        self.assertEqual(tx_results[0].status, int(False))
        self.assertEqual(tx_results[0].failure.code, ExceptionCode.SERVER_ERROR)


if __name__ == '__main__':
    unittest.main()
