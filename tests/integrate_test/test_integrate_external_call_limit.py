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
from tests.integrate_test.test_integrate_base import TestIntegrateBase


class TestIntegrateExternalCallLimit(TestIntegrateBase):

    def setUp(self):
        super().setUp()
        self._update_governance()

    def _update_governance(self):
        tx = self._make_deploy_tx("test_builtin",
                                  "latest_version/governance",
                                  self._admin,
                                  GOVERNANCE_SCORE_ADDRESS)
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)

    def test_invoke_loop(self):
        # Deploys SCORE
        prev_block, tx_results = self._make_and_req_block([
            self._make_deploy_tx("test_score_external_call_limit",
                                 "test_score_start",
                                 self._addr_array[0],
                                 ZERO_SCORE_ADDRESS),
            self._make_deploy_tx("test_score_external_call_limit",
                                 "test_score_call_termination",
                                 self._addr_array[0],
                                 ZERO_SCORE_ADDRESS)
        ])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))
        start_score = tx_results[0].score_address
        self.assertEqual(tx_results[1].status, int(True))
        termination_score = tx_results[1].score_address

        loop_count = 100
        prev_block, tx_results = self._make_and_req_block([
            self._make_score_call_tx(
                self._genesis,
                start_score,
                'invokeLoop',
                {'_to': str(termination_score), '_name': 'invoke', '_count': hex(loop_count)},
                0)
        ])

        self._write_precommit_state(prev_block)

        # Checks if the result is successful
        self.assertEqual(tx_results[0].status, 1)

        response = self._query(
            {
                'to': termination_score,
                'dataType': 'call',
                'data': {'method': 'getValue'}
            }
        )
        self.assertEqual(response, loop_count)

    def test_invoke_loop_over(self):
        # Deploys SCORE
        prev_block, tx_results = self._make_and_req_block([
            self._make_deploy_tx("test_score_external_call_limit",
                                 "test_score_start",
                                 self._addr_array[0],
                                 ZERO_SCORE_ADDRESS),
            self._make_deploy_tx("test_score_external_call_limit",
                                 "test_score_call_termination",
                                 self._addr_array[0],
                                 ZERO_SCORE_ADDRESS)
        ])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))
        start_score = tx_results[0].score_address
        self.assertEqual(tx_results[1].status, int(True))
        termination_score = tx_results[1].score_address

        loop_count = 1025
        prev_block, tx_results = self._make_and_req_block([
            self._make_score_call_tx(
                self._genesis,
                start_score,
                'invokeLoop',
                {'_to': str(termination_score), '_name': 'invoke', '_count': hex(loop_count)},
                0)
        ])

        self._write_precommit_state(prev_block)

        self.assertEqual(tx_results[0].status, 0)
        self.assertEqual(tx_results[0].failure.message, 'Too many external calls')

        response = self._query(
            {
                'to': termination_score,
                'dataType': 'call',
                'data': {'method': 'getValue'}
            }
        )
        self.assertEqual(response, 0)

    def test_invoke_query_loop(self):
        # Deploys SCORE
        prev_block, tx_results = self._make_and_req_block([
            self._make_deploy_tx("test_score_external_call_limit",
                                 "test_score_start",
                                 self._addr_array[0],
                                 ZERO_SCORE_ADDRESS),
            self._make_deploy_tx("test_score_external_call_limit",
                                 "test_score_call_termination",
                                 self._addr_array[0],
                                 ZERO_SCORE_ADDRESS)
        ])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))
        start_score = tx_results[0].score_address
        self.assertEqual(tx_results[1].status, int(True))
        termination_score = tx_results[1].score_address

        loop_count = 100
        prev_block, tx_results = self._make_and_req_block([
            self._make_score_call_tx(
                self._genesis,
                start_score,
                'invokeLoop',
                {'_to': str(termination_score), '_name': 'query', '_count': hex(loop_count)},
                0)
        ])

        self._write_precommit_state(prev_block)

        self.assertEqual(tx_results[0].status, 1)

    def test_invoke_query_loop_over(self):
        # Deploys SCORE
        prev_block, tx_results = self._make_and_req_block([
            self._make_deploy_tx("test_score_external_call_limit",
                                 "test_score_start",
                                 self._addr_array[0],
                                 ZERO_SCORE_ADDRESS),
            self._make_deploy_tx("test_score_external_call_limit",
                                 "test_score_call_termination",
                                 self._addr_array[0],
                                 ZERO_SCORE_ADDRESS)
        ])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))
        start_score = tx_results[0].score_address
        self.assertEqual(tx_results[1].status, int(True))
        termination_score = tx_results[1].score_address

        loop_count = 1025
        prev_block, tx_results = self._make_and_req_block([
            self._make_score_call_tx(
                self._genesis,
                start_score,
                'invokeLoop',
                {'_to': str(termination_score), '_name': 'query', '_count': hex(loop_count)},
                0)
        ])

        self._write_precommit_state(prev_block)

        self.assertEqual(tx_results[0].status, 0)
        self.assertEqual(tx_results[0].failure.message, 'Too many external calls')

    def test_query_loop(self):
        # Deploys SCORE
        prev_block, tx_results = self._make_and_req_block([
            self._make_deploy_tx("test_score_external_call_limit",
                                 "test_score_start",
                                 self._addr_array[0],
                                 ZERO_SCORE_ADDRESS),
            self._make_deploy_tx("test_score_external_call_limit",
                                 "test_score_call_termination",
                                 self._addr_array[0],
                                 ZERO_SCORE_ADDRESS)
        ])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))
        start_score = tx_results[0].score_address
        self.assertEqual(tx_results[1].status, int(True))
        termination_score = tx_results[1].score_address

        loop_count = 100

        response = self._query(
            {
                'to': start_score,
                'dataType': 'call',
                'data': {
                    'method': 'queryLoop',
                    'params': {
                        '_to': str(termination_score),
                        '_name': 'query',
                        '_count': hex(loop_count)
                    }
                }
            }
        )
        self.assertEqual(response, str(loop_count))

    def test_query_loop_over(self):
        # Deploys SCORE
        prev_block, tx_results = self._make_and_req_block([
            self._make_deploy_tx("test_score_external_call_limit",
                                 "test_score_start",
                                 self._addr_array[0],
                                 ZERO_SCORE_ADDRESS),
            self._make_deploy_tx("test_score_external_call_limit",
                                 "test_score_call_termination",
                                 self._addr_array[0],
                                 ZERO_SCORE_ADDRESS)
        ])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))
        start_score = tx_results[0].score_address
        self.assertEqual(tx_results[1].status, int(True))
        termination_score = tx_results[1].score_address

        loop_count = 1025
        with self.assertRaises(BaseException) as context:
            response = self._query(
                {
                    'to': start_score,
                    'stepLimit': 0x999999999,
                    'dataType': 'call',
                    'data': {
                        'method': 'queryLoop',
                        'params': {
                            '_to': str(termination_score),
                            '_name': 'query',
                            '_count': hex(loop_count)
                        }
                    }
                }
            )

        self.assertEqual(context.exception.message, 'Too many external calls')

    def test_invoke_recursive(self):

        # Deploys SCORE
        prev_block, tx_results = self._make_and_req_block([
            self._make_deploy_tx("test_score_external_call_limit",
                                 "test_score_start",
                                 self._addr_array[0],
                                 ZERO_SCORE_ADDRESS),
            self._make_deploy_tx("test_score_external_call_limit",
                                 "test_score_call_reflex",
                                 self._addr_array[0],
                                 ZERO_SCORE_ADDRESS)
        ])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))
        start_score = tx_results[0].score_address
        self.assertEqual(tx_results[1].status, int(True))
        reflex_score = tx_results[1].score_address

        prev_block, tx_results = self._make_and_req_block([
            self._make_score_call_tx(
                self._genesis,
                start_score,
                'invokeRecursive',
                {'_to': str(reflex_score), '_name': 'invoke'},
                0)
        ])

        self._write_precommit_state(prev_block)

        self.assertEqual(tx_results[0].status, 0)
        self.assertEqual(tx_results[0].failure.message, 'Max call stack size exceeded')

    def test_invoke_query_recursive(self):

        # Deploys SCORE
        prev_block, tx_results = self._make_and_req_block([
            self._make_deploy_tx("test_score_external_call_limit",
                                 "test_score_start",
                                 self._addr_array[0],
                                 ZERO_SCORE_ADDRESS),
            self._make_deploy_tx("test_score_external_call_limit",
                                 "test_score_call_reflex",
                                 self._addr_array[0],
                                 ZERO_SCORE_ADDRESS)
        ])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))
        start_score = tx_results[0].score_address
        self.assertEqual(tx_results[1].status, int(True))
        reflex_score = tx_results[1].score_address

        prev_block, tx_results = self._make_and_req_block([
            self._make_score_call_tx(
                self._genesis,
                start_score,
                'invokeRecursive',
                {'_to': str(reflex_score), '_name': 'query'},
                0)
        ])

        self._write_precommit_state(prev_block)

        self.assertEqual(tx_results[0].status, 0)
        self.assertEqual(tx_results[0].failure.message, 'Max call stack size exceeded')

    def test_query_recursive(self):
        # Deploys SCORE
        prev_block, tx_results = self._make_and_req_block([
            self._make_deploy_tx("test_score_external_call_limit",
                                 "test_score_start",
                                 self._addr_array[0],
                                 ZERO_SCORE_ADDRESS),
            self._make_deploy_tx("test_score_external_call_limit",
                                 "test_score_call_reflex",
                                 self._addr_array[0],
                                 ZERO_SCORE_ADDRESS)
        ])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))
        start_score = tx_results[0].score_address
        self.assertEqual(tx_results[1].status, int(True))
        reflex_score = tx_results[1].score_address

        with self.assertRaises(BaseException) as context:
            response = self._query(
                {
                    'to': start_score,
                    'stepLimit': 0x999999999,
                    'dataType': 'call',
                    'data': {
                        'method': 'queryRecursive',
                        'params': {
                            '_to': str(reflex_score),
                            '_name': 'query'
                        }
                    }
                }
            )

        self.assertEqual(context.exception.message, 'Max call stack size exceeded')


if __name__ == '__main__':
    unittest.main()
