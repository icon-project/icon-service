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

from iconservice.base.address import ZERO_SCORE_ADDRESS
from iconservice.base.exception import ExceptionCode, ScoreErrorException
from tests import raise_exception_start_tag, raise_exception_end_tag
from tests.integrate_test.test_integrate_base import TestIntegrateBase


class TestIntegrateScoreInternalCall(TestIntegrateBase):

    def test_link_score(self):
        value1 = 1 * self._icx_factor
        tx1 = self._make_deploy_tx("test_internal_call_scores",
                                   "test_score",
                                   self._addr_array[0],
                                   ZERO_SCORE_ADDRESS,
                                   deploy_params={'value': hex(value1)})

        tx2 = self._make_deploy_tx("test_internal_call_scores",
                                   "test_link_score",
                                   self._addr_array[0],
                                   ZERO_SCORE_ADDRESS)

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

        prev_block, tx_results = self._make_and_req_block([tx3])

        self._write_precommit_state(prev_block)

        self.assertEqual(tx_results[0].status, int(True))

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
        response = self._query(query_request)
        self.assertEqual(response, value1)

        value2 = 1 * self._icx_factor
        tx4 = self._make_score_call_tx(self._addr_array[0],
                                       score_addr2,
                                       'set_value',
                                       {"value": hex(value2)})

        prev_block, tx_results = self._make_and_req_block([tx4])

        self._write_precommit_state(prev_block)

        self.assertEqual(tx_results[0].status, int(True))

        response = self._query(query_request)
        self.assertEqual(response, value2)

    def test_link_score_cross(self):
        value1 = 1 * self._icx_factor
        tx1 = self._make_deploy_tx("test_internal_call_scores",
                                   "test_score",
                                   self._addr_array[0],
                                   ZERO_SCORE_ADDRESS,
                                   deploy_params={'value': hex(value1)})

        tx2 = self._make_deploy_tx("test_internal_call_scores",
                                   "test_link_score_cross",
                                   self._addr_array[0],
                                   ZERO_SCORE_ADDRESS)

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

        prev_block, tx_results = self._make_and_req_block([tx3])

        self._write_precommit_state(prev_block)

        self.assertEqual(tx_results[0].status, int(True))

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
        self.assertEqual(e.exception.message, "put is not allowed")

        value2 = 1 * self._icx_factor
        tx4 = self._make_score_call_tx(self._addr_array[0],
                                       score_addr2,
                                       'set_value',
                                       {"value": hex(value2)})

        prev_block, tx_results = self._make_and_req_block([tx4])

        self._write_precommit_state(prev_block)

        self.assertEqual(tx_results[0].status, int(True))

    def test_link_score_loop(self):
        tx1 = self._make_deploy_tx("test_internal_call_scores",
                                   "test_link_loop",
                                   self._addr_array[0],
                                   ZERO_SCORE_ADDRESS)

        tx2 = self._make_deploy_tx("test_internal_call_scores",
                                   "test_link_loop",
                                   self._addr_array[0],
                                   ZERO_SCORE_ADDRESS)

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

        tx4 = self._make_score_call_tx(self._addr_array[0],
                                       score_addr1,
                                       'add_score_func',
                                       {"score_addr": str(score_addr2)})

        prev_block, tx_results = self._make_and_req_block([tx3, tx4])

        self._write_precommit_state(prev_block)

        self.assertEqual(tx_results[0].status, int(True))
        self.assertEqual(tx_results[1].status, int(True))

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

        with self.assertRaises(BaseException) as context:
            self._query(query_request)

        self.assertEqual(context.exception.message, 'Max call stack size exceeded')

        value2 = 1 * self._icx_factor
        tx4 = self._make_score_call_tx(self._addr_array[0],
                                       score_addr2,
                                       'set_value',
                                       {"value": hex(value2)})

        raise_exception_start_tag("test_link_score_loop")
        prev_block, tx_results = self._make_and_req_block([tx4])
        raise_exception_end_tag("test_link_score_loop")

        self._write_precommit_state(prev_block)

        self.assertEqual(tx_results[0].status, int(False))
        self.assertEqual(tx_results[0].failure.message, 'Max call stack size exceeded')

    # case when query method call query method
    def test_link_score_check_return_type1(self):
        value1 = 1 * self._icx_factor
        tx1 = self._make_deploy_tx("test_internal_call_scores/test_returns_wrong_type",
                                   "test_score",
                                   self._addr_array[0],
                                   ZERO_SCORE_ADDRESS,
                                   deploy_params={'value': hex(value1)})

        tx2 = self._make_deploy_tx("test_internal_call_scores/test_returns_wrong_type",
                                   "test_link_score",
                                   self._addr_array[0],
                                   ZERO_SCORE_ADDRESS)

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

        prev_block, tx_results = self._make_and_req_block([tx3])

        self._write_precommit_state(prev_block)

        self.assertEqual(tx_results[0].status, int(True))

        query_request = {
            "version": self._version,
            "from": self._admin,
            "to": score_addr2,
            "dataType": "call",
            "data": {
                "method": "get_value_fail",
                "params": {}
            }
        }
        with self.assertRaises(ScoreErrorException) as e:
            self._query(query_request)
        self.assertEqual(e.exception.code, ExceptionCode.SCORE_ERROR)

    # case when invoke method call query method
    def test_link_score_check_return_type2(self):
        value1 = 1 * self._icx_factor
        tx1 = self._make_deploy_tx("test_internal_call_scores/test_returns_wrong_type",
                                   "test_score",
                                   self._addr_array[0],
                                   ZERO_SCORE_ADDRESS,
                                   deploy_params={'value': hex(value1)})

        tx2 = self._make_deploy_tx("test_internal_call_scores/test_returns_wrong_type",
                                   "test_link_score",
                                   self._addr_array[0],
                                   ZERO_SCORE_ADDRESS)

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

        prev_block, tx_results = self._make_and_req_block([tx3])

        self._write_precommit_state(prev_block)

        self.assertEqual(tx_results[0].status, int(True))

        tx4 = self._make_score_call_tx(self._addr_array[0],
                                       score_addr2,
                                       'increase_value_fail',
                                       {})

        prev_block, tx_results = self._make_and_req_block([tx4])

        self._write_precommit_state(prev_block)

        self.assertEqual(tx_results[0].status, int(False))
        self.assertEqual(tx_results[0].failure.code, ExceptionCode.SCORE_ERROR)


if __name__ == '__main__':
    unittest.main()
