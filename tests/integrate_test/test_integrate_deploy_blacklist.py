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
from tests.integrate_test.test_integrate_base import TestIntegrateBase


class TestIntegrateDeployBlackList(TestIntegrateBase):

    def test_score_add_blacklist(self):
        value1 = 1 * self._icx_factor
        tx1 = self._make_deploy_tx("test_deploy_scores",
                                   "install/test_score",
                                   self._addr_array[0],
                                   ZERO_SCORE_ADDRESS,
                                   deploy_params={'value': hex(value1)})

        tx2 = self._make_deploy_tx("test_internal_call_scores",
                                   "test_link_score",
                                   self._addr_array[0],
                                   ZERO_SCORE_ADDRESS,
                                   deploy_params={'value': hex(value1)})

        prev_block, tx_results = self._make_and_req_block([tx1, tx2])

        self._write_precommit_state(prev_block)

        self.assertEqual(tx_results[0].status, int(True))
        score_addr1 = tx_results[0].score_address
        self.assertEqual(tx_results[1].status, int(True))
        score_addr2 = tx_results[1].score_address

        tx3 = self._make_score_call_tx(self._addr_array[0],
                                       score_addr2,
                                       'add_score_func',
                                       {"score_addr": str(score_addr1)})

        tx4 = self._make_score_call_tx(self._admin,
                                       GOVERNANCE_SCORE_ADDRESS,
                                       'addToScoreBlackList',
                                       {"address": str(score_addr1)})

        prev_block, tx_results = self._make_and_req_block([tx3, tx4])

        self._write_precommit_state(prev_block)

        self.assertEqual(tx_results[0].status, int(True))
        self.assertEqual(tx_results[1].status, int(True))

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

        with self.assertRaises(BaseException) as e:
            self._query(query_request)
        self.assertEqual(e.exception.code, ExceptionCode.SERVER_ERROR)

        value2 = 2 * self._icx_factor

        with self.assertRaises(BaseException) as e:
            self._make_score_call_tx(self._addr_array[0],
                                     score_addr1,
                                     'set_value',
                                     {"value": hex(value2)})
        self.assertEqual(e.exception.code, ExceptionCode.SERVER_ERROR)

        query_request = {
            "version": self._version,
            "from": self._admin,
            "to": score_addr2,
            "dataType": "call",
            "data": {
                "method": "get_value",
                "params": {}
            }
        }

        with self.assertRaises(BaseException) as e:
            self._query(query_request)
        self.assertEqual(e.exception.code, ExceptionCode.SERVER_ERROR)

    def test_score_add_blacklist_not_version_field(self):
        value1 = 1 * self._icx_factor
        tx1 = self._make_deploy_tx("test_deploy_scores",
                                   "install/test_score",
                                   self._addr_array[0],
                                   ZERO_SCORE_ADDRESS,
                                   deploy_params={'value': hex(value1)})

        tx2 = self._make_deploy_tx("test_internal_call_scores",
                                   "test_link_score",
                                   self._addr_array[0],
                                   ZERO_SCORE_ADDRESS,
                                   deploy_params={'value': hex(value1)})

        prev_block, tx_results = self._make_and_req_block([tx1, tx2])

        self._write_precommit_state(prev_block)

        self.assertEqual(tx_results[0].status, int(True))
        score_addr1 = tx_results[0].score_address
        self.assertEqual(tx_results[1].status, int(True))
        score_addr2 = tx_results[1].score_address

        tx3 = self._make_score_call_tx(self._addr_array[0],
                                       score_addr2,
                                       'add_score_func',
                                       {"score_addr": str(score_addr1)})

        tx4 = self._make_score_call_tx(self._admin,
                                       GOVERNANCE_SCORE_ADDRESS,
                                       'addToScoreBlackList',
                                       {"address": str(score_addr1)})

        prev_block, tx_results = self._make_and_req_block([tx3, tx4])

        self._write_precommit_state(prev_block)

        self.assertEqual(tx_results[0].status, int(True))
        self.assertEqual(tx_results[1].status, int(True))

        query_request = {
            "from": self._admin,
            "to": score_addr1,
            "dataType": "call",
            "data": {
                "method": "get_value",
                "params": {}
            }
        }

        with self.assertRaises(BaseException) as e:
            self._query(query_request)
        self.assertEqual(e.exception.code, ExceptionCode.SERVER_ERROR)

        value2 = 2 * self._icx_factor

        with self.assertRaises(BaseException) as e:
            self._make_score_call_tx(self._addr_array[0],
                                     score_addr1,
                                     'set_value',
                                     {"value": hex(value2)})
        self.assertEqual(e.exception.code, ExceptionCode.SERVER_ERROR)

        query_request = {
            "from": self._admin,
            "to": score_addr2,
            "dataType": "call",
            "data": {
                "method": "get_value",
                "params": {}
            }
        }

        with self.assertRaises(BaseException) as e:
            self._query(query_request)
        self.assertEqual(e.exception.code, ExceptionCode.SERVER_ERROR)

    def test_score_remove_deployer(self):
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

        tx2 = self._make_score_call_tx(self._admin,
                                       GOVERNANCE_SCORE_ADDRESS,
                                       'addToScoreBlackList',
                                       {"address": str(score_addr1)})

        tx3 = self._make_score_call_tx(self._admin,
                                       GOVERNANCE_SCORE_ADDRESS,
                                       'removeFromScoreBlackList',
                                       {"address": str(score_addr1)})

        prev_block, tx_results = self._make_and_req_block([tx2, tx3])

        self._write_precommit_state(prev_block)

        self.assertEqual(tx_results[0].status, int(True))
        self.assertEqual(tx_results[1].status, int(True))

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

        tx4 = self._make_score_call_tx(self._admin,
                                       score_addr1,
                                       'set_value',
                                       {"value": str(value1)})

        prev_block, tx_results = self._make_and_req_block([tx4])

        self._write_precommit_state(prev_block)

        self.assertEqual(tx_results[0].status, int(True))

        response = self._query(query_request)
        self.assertEqual(response, value1)


if __name__ == '__main__':
    unittest.main()
