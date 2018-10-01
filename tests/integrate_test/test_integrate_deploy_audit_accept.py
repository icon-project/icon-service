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
from tests import create_tx_hash


class TestIntegrateDeployAuditAccept(TestIntegrateBase):

    def _make_init_config(self) -> dict:
        return {ConfigKey.SERVICE: {ConfigKey.SERVICE_AUDIT: True}}

    def update_0_0_3_governance(self):
        tx1 = self._make_deploy_tx("test_builtin",
                                   "0_0_3/governance",
                                   self._admin,
                                   GOVERNANCE_SCORE_ADDRESS)
        prev_block, tx_results = self._make_and_req_block([tx1])
        self._write_precommit_state(prev_block)

    def test_builtin_score(self):
        self.update_0_0_3_governance()

        query_request = {
            "version": self._version,
            "from": self._addr_array[0],
            "to": GOVERNANCE_SCORE_ADDRESS,
            "dataType": "call",
            "data": {
                "method": "getScoreStatus",
                "params": {"address": str(GOVERNANCE_SCORE_ADDRESS)}
            }
        }
        response = self._query(query_request)
        expect_ret = {
            'current': {
                'status': 'active'}
        }
        self.assertEqual(response, expect_ret)

    def test_normal_score(self):
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

        query_request = {
            "version": self._version,
            "from": self._addr_array[0],
            "to": GOVERNANCE_SCORE_ADDRESS,
            "dataType": "call",
            "data": {
                "method": "getScoreStatus",
                "params": {"address": str(score_addr1)}
            }
        }
        response = self._query(query_request)
        expect_ret = {
            'next': {
                'status': 'pending',
                'deployTxHash': tx_hash1}}
        self.assertEqual(response, expect_ret)

        tx2 = self._make_score_call_tx(self._admin,
                                       GOVERNANCE_SCORE_ADDRESS,
                                       'acceptScore',
                                       {"txHash": f'0x{bytes.hex(tx_hash1)}'})

        prev_block, tx_results = self._make_and_req_block([tx2])

        self._write_precommit_state(prev_block)

        self.assertEqual(tx_results[0].status, int(True))
        tx_hash2 = tx_results[0].tx_hash

        query_request = {
            "version": self._version,
            "from": self._addr_array[0],
            "to": GOVERNANCE_SCORE_ADDRESS,
            "dataType": "call",
            "data": {
                "method": "getScoreStatus",
                "params": {"address": str(score_addr1)}
            }
        }
        response = self._query(query_request)
        expect_ret = {
            'current': {
                'status': 'active',
                'deployTxHash': tx_hash1,
                'auditTxHash': tx_hash2}}
        self.assertEqual(response, expect_ret)

    def test_normal_score_non_exist_deploy_tx(self):
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

        query_request = {
            "version": self._version,
            "from": self._addr_array[0],
            "to": GOVERNANCE_SCORE_ADDRESS,
            "dataType": "call",
            "data": {
                "method": "getScoreStatus",
                "params": {"address": str(score_addr1)}
            }
        }
        response = self._query(query_request)
        expect_ret = {
            'next': {
                'status': 'pending',
                'deployTxHash': tx_hash1}}
        self.assertEqual(response, expect_ret)

        tx2 = self._make_score_call_tx(self._admin,
                                       GOVERNANCE_SCORE_ADDRESS,
                                       'acceptScore',
                                       {"txHash": ""})

        prev_block, tx_results = self._make_and_req_block([tx2])

        self._write_precommit_state(prev_block)

        self.assertEqual(tx_results[0].status, int(False))

    def test_normal_score_second_latest_pending_deploy_tx(self):
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

        query_request = {
            "version": self._version,
            "from": self._addr_array[0],
            "to": GOVERNANCE_SCORE_ADDRESS,
            "dataType": "call",
            "data": {
                "method": "getScoreStatus",
                "params": {"address": str(score_addr1)}
            }
        }
        response = self._query(query_request)
        expect_ret = {
            'next': {
                'status': 'pending',
                'deployTxHash': tx_hash1}}
        self.assertEqual(response, expect_ret)

        tx2 = self._make_score_call_tx(self._admin,
                                       GOVERNANCE_SCORE_ADDRESS,
                                       'acceptScore',
                                       {"txHash": f'0x{bytes.hex(tx_hash1)}'})

        prev_block, tx_results = self._make_and_req_block([tx2])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))
        tx_hash2 = tx_results[0].tx_hash

        query_request = {
            "version": self._version,
            "from": self._addr_array[0],
            "to": GOVERNANCE_SCORE_ADDRESS,
            "dataType": "call",
            "data": {
                "method": "getScoreStatus",
                "params": {"address": str(score_addr1)}
            }
        }
        response = self._query(query_request)
        expect_ret = {
            'current': {
                'status': 'active',
                'deployTxHash': tx_hash1,
                'auditTxHash': tx_hash2}}
        self.assertEqual(response, expect_ret)

        # update
        value2 = 2 * self._icx_factor
        tx3 = self._make_deploy_tx("test_deploy_scores",
                                   "update/test_score",
                                   self._addr_array[0],
                                   score_addr1,
                                   deploy_params={'value': hex(value2)})

        prev_block, tx_results = self._make_and_req_block([tx3])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))
        tx_hash3 = tx_results[0].tx_hash

        query_request = {
            "version": self._version,
            "from": self._addr_array[0],
            "to": GOVERNANCE_SCORE_ADDRESS,
            "dataType": "call",
            "data": {
                "method": "getScoreStatus",
                "params": {"address": str(score_addr1)}
            }
        }
        response = self._query(query_request)
        expect_ret = {
            'current': {
                'status': 'active',
                'deployTxHash': tx_hash1,
                'auditTxHash': tx_hash2},
            'next': {
                'status': 'pending',
                'deployTxHash': tx_hash3}
        }
        self.assertEqual(response, expect_ret)

        # overwrite
        value3 = 3 * self._icx_factor
        tx4 = self._make_deploy_tx("test_deploy_scores",
                                   "update/test_score",
                                   self._addr_array[0],
                                   score_addr1,
                                   deploy_params={'value': hex(value3)})

        prev_block, tx_results = self._make_and_req_block([tx4])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))
        tx_hash4 = tx_results[0].tx_hash

        query_request = {
            "version": self._version,
            "from": self._addr_array[0],
            "to": GOVERNANCE_SCORE_ADDRESS,
            "dataType": "call",
            "data": {
                "method": "getScoreStatus",
                "params": {"address": str(score_addr1)}
            }
        }
        response = self._query(query_request)
        expect_ret = {
            'current': {
                'status': 'active',
                'deployTxHash': tx_hash1,
                'auditTxHash': tx_hash2},
            'next': {
                'status': 'pending',
                'deployTxHash': tx_hash4}
        }
        self.assertEqual(response, expect_ret)

        # wrong pass! -> Bug!!
        # tx5 = self._make_score_call_tx(self._admin,
        #                                GOVERNANCE_SCORE_ADDRESS,
        #                                'acceptScore',
        #                                {"txHash": f'0x{bytes.hex(tx_hash1)}'})
        # prev_block, tx_results = self._make_and_req_block([tx5])
        # self._write_precommit_state(prev_block)

        tx5 = self._make_score_call_tx(self._admin,
                                       GOVERNANCE_SCORE_ADDRESS,
                                       'acceptScore',
                                       {"txHash": f'0x{bytes.hex(tx_hash2)}'})
        tx6 = self._make_score_call_tx(self._admin,
                                       GOVERNANCE_SCORE_ADDRESS,
                                       'acceptScore',
                                       {"txHash": f'0x{bytes.hex(tx_hash3)}'})

        raise_exception_start_tag("test_normal_score_second_latest_pending_deploy_tx")
        prev_block, tx_results = self._make_and_req_block([tx5, tx6])
        raise_exception_end_tag("test_normal_score_second_latest_pending_deploy_tx")
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(False))
        self.assertEqual(tx_results[1].status, int(False))

        tx7 = self._make_score_call_tx(self._admin,
                                       GOVERNANCE_SCORE_ADDRESS,
                                       'rejectScore',
                                       {"txHash": f'0x{bytes.hex(tx_hash4)}',
                                        "reason": "hello"})

        prev_block, tx_results = self._make_and_req_block([tx7])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))
        tx_hash5 = tx_results[0].tx_hash

        query_request = {
            "version": self._version,
            "from": self._addr_array[0],
            "to": GOVERNANCE_SCORE_ADDRESS,
            "dataType": "call",
            "data": {
                "method": "getScoreStatus",
                "params": {"address": str(score_addr1)}
            }
        }
        response = self._query(query_request)
        expect_ret = {
            'current': {
                'status': 'active',
                'deployTxHash': tx_hash1,
                'auditTxHash': tx_hash2},
            'next': {
                'status': 'rejected',
                'deployTxHash': tx_hash4,
                'auditTxHash': tx_hash5}
        }
        self.assertEqual(response, expect_ret)

        tx8 = self._make_score_call_tx(self._admin,
                                       GOVERNANCE_SCORE_ADDRESS,
                                       'acceptScore',
                                       {"txHash": f'0x{bytes.hex(tx_hash4)}'})

        prev_block, tx_results = self._make_and_req_block([tx8])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))

    def test_normal_score_non_exist_deploy_tx_0_0_3_governance(self):
        self.update_0_0_3_governance()

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

        query_request = {
            "version": self._version,
            "from": self._addr_array[0],
            "to": GOVERNANCE_SCORE_ADDRESS,
            "dataType": "call",
            "data": {
                "method": "getScoreStatus",
                "params": {"address": str(score_addr1)}
            }
        }
        response = self._query(query_request)
        expect_ret = {
            'next': {
                'status': 'pending',
                'deployTxHash': tx_hash1}}
        self.assertEqual(response, expect_ret)

        tx2 = self._make_score_call_tx(self._admin,
                                       GOVERNANCE_SCORE_ADDRESS,
                                       'acceptScore',
                                       {"txHash": ""})

        prev_block, tx_results = self._make_and_req_block([tx2])

        self._write_precommit_state(prev_block)

        self.assertEqual(tx_results[0].status, int(False))

    def test_normal_score_second_latest_pending_deploy_tx_0_0_3_governance(self):
        self.update_0_0_3_governance()
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

        query_request = {
            "version": self._version,
            "from": self._addr_array[0],
            "to": GOVERNANCE_SCORE_ADDRESS,
            "dataType": "call",
            "data": {
                "method": "getScoreStatus",
                "params": {"address": str(score_addr1)}
            }
        }
        response = self._query(query_request)
        expect_ret = {
            'next': {
                'status': 'pending',
                'deployTxHash': tx_hash1}}
        self.assertEqual(response, expect_ret)

        tx2 = self._make_score_call_tx(self._admin,
                                       GOVERNANCE_SCORE_ADDRESS,
                                       'acceptScore',
                                       {"txHash": f'0x{bytes.hex(tx_hash1)}'})

        prev_block, tx_results = self._make_and_req_block([tx2])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))
        tx_hash2 = tx_results[0].tx_hash

        query_request = {
            "version": self._version,
            "from": self._addr_array[0],
            "to": GOVERNANCE_SCORE_ADDRESS,
            "dataType": "call",
            "data": {
                "method": "getScoreStatus",
                "params": {"address": str(score_addr1)}
            }
        }
        response = self._query(query_request)
        expect_ret = {
            'current': {
                'status': 'active',
                'deployTxHash': tx_hash1,
                'auditTxHash': tx_hash2}}
        self.assertEqual(response, expect_ret)

        # update
        value2 = 2 * self._icx_factor
        tx3 = self._make_deploy_tx("test_deploy_scores",
                                   "update/test_score",
                                   self._addr_array[0],
                                   score_addr1,
                                   deploy_params={'value': hex(value2)})

        prev_block, tx_results = self._make_and_req_block([tx3])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))
        tx_hash3 = tx_results[0].tx_hash

        query_request = {
            "version": self._version,
            "from": self._addr_array[0],
            "to": GOVERNANCE_SCORE_ADDRESS,
            "dataType": "call",
            "data": {
                "method": "getScoreStatus",
                "params": {"address": str(score_addr1)}
            }
        }
        response = self._query(query_request)
        expect_ret = {
            'current': {
                'status': 'active',
                'deployTxHash': tx_hash1,
                'auditTxHash': tx_hash2},
            'next': {
                'status': 'pending',
                'deployTxHash': tx_hash3}
        }
        self.assertEqual(response, expect_ret)

        # overwrite
        value3 = 3 * self._icx_factor
        tx4 = self._make_deploy_tx("test_deploy_scores",
                                   "update/test_score",
                                   self._addr_array[0],
                                   score_addr1,
                                   deploy_params={'value': hex(value3)})

        prev_block, tx_results = self._make_and_req_block([tx4])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))
        tx_hash4 = tx_results[0].tx_hash

        query_request = {
            "version": self._version,
            "from": self._addr_array[0],
            "to": GOVERNANCE_SCORE_ADDRESS,
            "dataType": "call",
            "data": {
                "method": "getScoreStatus",
                "params": {"address": str(score_addr1)}
            }
        }
        response = self._query(query_request)
        expect_ret = {
            'current': {
                'status': 'active',
                'deployTxHash': tx_hash1,
                'auditTxHash': tx_hash2},
            'next': {
                'status': 'pending',
                'deployTxHash': tx_hash4}
        }
        self.assertEqual(response, expect_ret)

        # wrong pass! -> Bug Fix!!
        tx5 = self._make_score_call_tx(self._admin,
                                       GOVERNANCE_SCORE_ADDRESS,
                                       'acceptScore',
                                       {"txHash": f'0x{bytes.hex(tx_hash1)}'})
        prev_block, tx_results = self._make_and_req_block([tx5])
        self._write_precommit_state(prev_block)

        tx6 = self._make_score_call_tx(self._admin,
                                       GOVERNANCE_SCORE_ADDRESS,
                                       'acceptScore',
                                       {"txHash": f'0x{bytes.hex(tx_hash2)}'})
        tx7 = self._make_score_call_tx(self._admin,
                                       GOVERNANCE_SCORE_ADDRESS,
                                       'acceptScore',
                                       {"txHash": f'0x{bytes.hex(tx_hash3)}'})

        raise_exception_start_tag("test_normal_score_second_latest_pending_deploy_tx")
        prev_block, tx_results = self._make_and_req_block([tx5, tx6, tx7])
        raise_exception_end_tag("test_normal_score_second_latest_pending_deploy_tx")
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(False))
        self.assertEqual(tx_results[1].status, int(False))
        self.assertEqual(tx_results[2].status, int(False))

        tx8 = self._make_score_call_tx(self._admin,
                                       GOVERNANCE_SCORE_ADDRESS,
                                       'rejectScore',
                                       {"txHash": f'0x{bytes.hex(tx_hash4)}',
                                        "reason": "hello"})

        prev_block, tx_results = self._make_and_req_block([tx8])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))
        tx_hash5 = tx_results[0].tx_hash

        query_request = {
            "version": self._version,
            "from": self._addr_array[0],
            "to": GOVERNANCE_SCORE_ADDRESS,
            "dataType": "call",
            "data": {
                "method": "getScoreStatus",
                "params": {"address": str(score_addr1)}
            }
        }
        response = self._query(query_request)
        expect_ret = {
            'current': {
                'status': 'active',
                'deployTxHash': tx_hash1,
                'auditTxHash': tx_hash2},
            'next': {
                'status': 'rejected',
                'deployTxHash': tx_hash4,
                'auditTxHash': tx_hash5}
        }
        self.assertEqual(response, expect_ret)

        tx9 = self._make_score_call_tx(self._admin,
                                       GOVERNANCE_SCORE_ADDRESS,
                                       'acceptScore',
                                       {"txHash": f'0x{bytes.hex(tx_hash4)}'})

        prev_block, tx_results = self._make_and_req_block([tx9])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))


if __name__ == '__main__':
    unittest.main()
