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
from iconservice.base.exception import ExceptionCode
from tests.integrate_test.test_integrate_base import TestIntegrateBase


class TestIntegrateFallbackCall(TestIntegrateBase):

    def test_score_pass(self):
        tx1 = self._make_deploy_tx("test_fallback_call_scores",
                                   "test_score_pass",
                                   self._addr_array[0],
                                   ZERO_SCORE_ADDRESS)
        prev_block, tx_results = self._make_and_req_block([tx1])

        self._write_precommit_state(prev_block)

        self.assertEqual(tx_results[0].status, int(True))
        score_addr1 = tx_results[0].score_address

        value = 1 * self._icx_factor
        tx2 = self._make_icx_send_tx(self._genesis, score_addr1, value)

        prev_block, tx_results = self._make_and_req_block([tx2])

        self._write_precommit_state(prev_block)

        query_request = {
            "address": score_addr1
        }

        response = self._query(query_request, 'icx_getBalance')
        self.assertEqual(response, value)

    def test_score_send_to_eoa(self):
        tx1 = self._make_deploy_tx("test_fallback_call_scores",
                                   "test_score_to_eoa",
                                   self._addr_array[0],
                                   ZERO_SCORE_ADDRESS)
        prev_block, tx_results = self._make_and_req_block([tx1])

        self._write_precommit_state(prev_block)

        self.assertEqual(tx_results[0].status, int(True))
        score_addr1 = tx_results[0].score_address

        tx2 = self._make_score_call_tx(self._addr_array[0],
                                       score_addr1,
                                       'set_addr_func',
                                       {"addr": str(self._addr_array[1])})

        prev_block, tx_results = self._make_and_req_block([tx2])

        self._write_precommit_state(prev_block)

        self.assertEqual(tx_results[0].status, int(True))

        value = 1 * self._icx_factor
        tx3 = self._make_icx_send_tx(self._genesis, score_addr1, value)

        prev_block, tx_results = self._make_and_req_block([tx3])

        self._write_precommit_state(prev_block)

        query_request = {
            "address": self._addr_array[1]
        }

        response = self._query(query_request, 'icx_getBalance')
        self.assertEqual(response, value)

    def test_score_revert(self):
        tx1 = self._make_deploy_tx("test_fallback_call_scores",
                                   "test_score_revert",
                                   self._addr_array[0],
                                   ZERO_SCORE_ADDRESS)
        prev_block, tx_results = self._make_and_req_block([tx1])

        self._write_precommit_state(prev_block)

        self.assertEqual(tx_results[0].status, int(True))
        score_addr1 = tx_results[0].score_address

        value = 1 * self._icx_factor
        tx2 = self._make_icx_send_tx(self._genesis, score_addr1, value)

        prev_block, tx_results = self._make_and_req_block([tx2])

        self._write_precommit_state(prev_block)

        self.assertEqual(tx_results[0].status, int(False))
        self.assertEqual(tx_results[0].failure.code, ExceptionCode.SCORE_ERROR)
        self.assertEqual(tx_results[0].failure.message, "fallback!!")

        query_request = {
            "address": score_addr1
        }

        response = self._query(query_request, 'icx_getBalance')
        self.assertEqual(response, 0)

    def test_score_no_payable(self):
        tx1 = self._make_deploy_tx("test_fallback_call_scores",
                                   "test_score_no_payable",
                                   self._addr_array[0],
                                   ZERO_SCORE_ADDRESS)
        prev_block, tx_results = self._make_and_req_block([tx1])

        self._write_precommit_state(prev_block)

        self.assertEqual(tx_results[0].status, int(True))
        score_addr1 = tx_results[0].score_address

        value = 1 * self._icx_factor
        tx2 = self._make_icx_send_tx(self._genesis, score_addr1, value)

        prev_block, tx_results = self._make_and_req_block([tx2])

        self._write_precommit_state(prev_block)

        self.assertEqual(tx_results[0].status, int(False))
        self.assertEqual(tx_results[0].failure.code, ExceptionCode.SCORE_ERROR)
        self.assertEqual(tx_results[0].failure.message, "This is not payable")

        query_request = {
            "address": score_addr1
        }

        response = self._query(query_request, 'icx_getBalance')
        self.assertEqual(response, 0)

    def test_score_pass_link_transfer(self):
        tx1 = self._make_deploy_tx("test_fallback_call_scores",
                                   "test_score_pass",
                                   self._addr_array[0],
                                   ZERO_SCORE_ADDRESS)
        tx2 = self._make_deploy_tx("test_fallback_call_scores",
                                   "test_link_score_transfer",
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

        value = 1 * self._icx_factor
        tx4 = self._make_icx_send_tx(self._genesis, score_addr2, value)

        prev_block, tx_results = self._make_and_req_block([tx3, tx4])

        self._write_precommit_state(prev_block)

        self.assertEqual(tx_results[0].status, int(True))
        self.assertEqual(tx_results[1].status, int(True))

        query_request = {
            "address": score_addr1
        }

        response = self._query(query_request, 'icx_getBalance')
        self.assertEqual(response, value)

    def test_score_pass_link_send(self):
        tx1 = self._make_deploy_tx("test_fallback_call_scores",
                                   "test_score_pass",
                                   self._addr_array[0],
                                   ZERO_SCORE_ADDRESS)
        tx2 = self._make_deploy_tx("test_fallback_call_scores",
                                   "test_link_score_send",
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

        value = 1 * self._icx_factor
        tx4 = self._make_icx_send_tx(self._genesis, score_addr2, value)

        prev_block, tx_results = self._make_and_req_block([tx3, tx4])

        self._write_precommit_state(prev_block)

        self.assertEqual(tx_results[0].status, int(True))
        self.assertEqual(tx_results[1].status, int(True))

        query_request = {
            "address": score_addr1
        }

        response = self._query(query_request, 'icx_getBalance')
        self.assertEqual(response, value)

    def test_score_no_payable_link_transfer(self):
        tx1 = self._make_deploy_tx("test_fallback_call_scores",
                                   "test_score_no_payable",
                                   self._addr_array[0],
                                   ZERO_SCORE_ADDRESS)
        tx2 = self._make_deploy_tx("test_fallback_call_scores",
                                   "test_link_score_transfer",
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

        value = 1 * self._icx_factor
        tx4 = self._make_icx_send_tx(self._genesis, score_addr2, value)

        prev_block, tx_results = self._make_and_req_block([tx3, tx4])

        self._write_precommit_state(prev_block)

        self.assertEqual(tx_results[0].status, int(True))
        self.assertEqual(tx_results[1].status, int(False))
        self.assertEqual(tx_results[1].failure.code, ExceptionCode.SCORE_ERROR)
        self.assertEqual(tx_results[1].failure.message, "This is not payable")

        query_request = {
            "address": score_addr1
        }

        response = self._query(query_request, 'icx_getBalance')
        self.assertEqual(response, 0)

    def test_score_no_payable_link_send(self):
        tx1 = self._make_deploy_tx("test_fallback_call_scores",
                                   "test_score_no_payable",
                                   self._addr_array[0],
                                   ZERO_SCORE_ADDRESS)
        tx2 = self._make_deploy_tx("test_fallback_call_scores",
                                   "test_link_score_send",
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

        value = 1 * self._icx_factor
        tx4 = self._make_icx_send_tx(self._genesis, score_addr2, value)

        prev_block, tx_results = self._make_and_req_block([tx3, tx4])

        self._write_precommit_state(prev_block)

        self.assertEqual(tx_results[0].status, int(True))
        self.assertEqual(tx_results[1].status, int(False))
        self.assertEqual(tx_results[1].failure.code, ExceptionCode.SCORE_ERROR)
        self.assertEqual(tx_results[1].failure.message, "This is not payable")

        query_request = {
            "address": score_addr1
        }

        response = self._query(query_request, 'icx_getBalance')
        self.assertEqual(response, 0)

    def test_score_revert_link_transfer(self):
        tx1 = self._make_deploy_tx("test_fallback_call_scores",
                                   "test_score_revert",
                                   self._addr_array[0],
                                   ZERO_SCORE_ADDRESS)
        tx2 = self._make_deploy_tx("test_fallback_call_scores",
                                   "test_link_score_transfer",
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

        value = 1 * self._icx_factor
        tx4 = self._make_icx_send_tx(self._genesis, score_addr2, value)

        prev_block, tx_results = self._make_and_req_block([tx3, tx4])

        self._write_precommit_state(prev_block)

        self.assertEqual(tx_results[0].status, int(True))
        self.assertEqual(tx_results[1].status, int(False))
        self.assertEqual(tx_results[1].failure.code, ExceptionCode.SCORE_ERROR)
        self.assertEqual(tx_results[1].failure.message, "fallback!!")

        query_request = {
            "address": score_addr1
        }

        response = self._query(query_request, 'icx_getBalance')
        self.assertEqual(response, 0)

    def test_score_revert_link_send(self):
        tx1 = self._make_deploy_tx("test_fallback_call_scores",
                                   "test_score_revert",
                                   self._addr_array[0],
                                   ZERO_SCORE_ADDRESS)
        tx2 = self._make_deploy_tx("test_fallback_call_scores",
                                   "test_link_score_send",
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

        value = 1 * self._icx_factor
        tx4 = self._make_icx_send_tx(self._genesis, score_addr2, value)

        prev_block, tx_results = self._make_and_req_block([tx3, tx4])

        self._write_precommit_state(prev_block)

        self.assertEqual(tx_results[0].status, int(True))
        self.assertEqual(tx_results[1].status, int(False))
        self.assertEqual(tx_results[1].failure.code, ExceptionCode.SCORE_ERROR)
        self.assertEqual(tx_results[1].failure.message, "This is not payable")

        query_request = {
            "address": score_addr1
        }

        response = self._query(query_request, 'icx_getBalance')
        self.assertEqual(response, 0)

    def test_score_revert_link_send_fail(self):
        tx1 = self._make_deploy_tx("test_fallback_call_scores",
                                   "test_score_revert",
                                   self._addr_array[0],
                                   ZERO_SCORE_ADDRESS)
        tx2 = self._make_deploy_tx("test_fallback_call_scores",
                                   "test_link_score_send_fail",
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

        value = 1 * self._icx_factor
        tx4 = self._make_icx_send_tx(self._genesis, score_addr2, value)

        prev_block, tx_results = self._make_and_req_block([tx3, tx4])

        self._write_precommit_state(prev_block)

        self.assertEqual(tx_results[0].status, int(True))
        self.assertEqual(tx_results[1].status, int(False))
        self.assertEqual(tx_results[1].failure.code, ExceptionCode.SCORE_ERROR)
        self.assertEqual(tx_results[1].failure.message, "Fail icx.send!")

        query_request = {
            "address": score_addr1
        }

        response = self._query(query_request, 'icx_getBalance')
        self.assertEqual(response, 0)

    def test_fallback(self):
        query_request = {
            "address": self._genesis
        }

        response = self._query(query_request, 'icx_getBalance')
        self.assertEqual(response, 100 * self._icx_factor)

        tx1 = self._make_deploy_tx("test_fallback_call_scores",
                                   "test_link_score_send_A",
                                   self._addr_array[0],
                                   ZERO_SCORE_ADDRESS)
        tx2 = self._make_deploy_tx("test_fallback_call_scores",
                                   "test_link_score_send_B",
                                   self._addr_array[0],
                                   ZERO_SCORE_ADDRESS)

        prev_block, tx_results = self._make_and_req_block([tx1, tx2])

        self._write_precommit_state(prev_block)

        self.assertEqual(tx_results[0].status, int(True))
        score_addr1 = tx_results[0].score_address
        self.assertEqual(tx_results[1].status, int(True))
        score_addr2 = tx_results[1].score_address

        tx3 = self._make_score_call_tx(self._admin,
                                       score_addr1,
                                       'add_score_addr',
                                       {"score_addr": str(score_addr2)})
        tx4 = self._make_score_call_tx(self._admin,
                                       score_addr1,
                                       'add_user_addr',
                                       {"eoa_addr": str(self._addr_array[2])})
        tx5 = self._make_score_call_tx(self._admin,
                                       score_addr2,
                                       'add_user_addr1',
                                       {"eoa_addr": str(self._addr_array[3])})
        tx6 = self._make_score_call_tx(self._admin,
                                       score_addr2,
                                       'add_user_addr2',
                                       {"eoa_addr": str(self._addr_array[2])})

        value = 20 * self._icx_factor
        tx7 = self._make_icx_send_tx(self._genesis, score_addr1, value)

        prev_block, tx_results = self._make_and_req_block([tx3, tx4, tx5, tx6, tx7])

        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))
        self.assertEqual(tx_results[1].status, int(True))
        self.assertEqual(tx_results[2].status, int(True))
        self.assertEqual(tx_results[3].status, int(True))
        self.assertEqual(tx_results[4].status, int(True))

        query_request = {
            "address": score_addr1
        }

        response = self._query(query_request, 'icx_getBalance')
        self.assertEqual(response, 0)

        query_request = {
            "address": score_addr2
        }

        response = self._query(query_request, 'icx_getBalance')
        self.assertEqual(response, 0)

        query_request = {
            "address": self._addr_array[2]
        }
        response = self._query(query_request, 'icx_getBalance')
        self.assertEqual(response, 15 * self._icx_factor)

        query_request = {
            "address": self._addr_array[3]
        }
        response = self._query(query_request, 'icx_getBalance')
        self.assertEqual(response, 5 * self._icx_factor)


if __name__ == '__main__':
    unittest.main()
