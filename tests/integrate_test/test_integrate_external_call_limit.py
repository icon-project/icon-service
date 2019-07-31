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
from typing import TYPE_CHECKING, List

from iconservice.base.address import ZERO_SCORE_ADDRESS
from iconservice.base.exception import InvalidRequestException, StackOverflowException
from tests.integrate_test.test_integrate_base import TestIntegrateBase

if TYPE_CHECKING:
    from iconservice.iconscore.icon_score_result import TransactionResult
    from iconservice.base.address import Address


class TestIntegrateExternalCallLimit(TestIntegrateBase):

    def setUp(self):
        super().setUp()
        self.update_governance()

    def test_invoke_loop(self):
        # Deploys SCORE
        tx1: dict = self.create_deploy_score_tx(score_root="sample_score_external_call_limit",
                                                score_name="sample_score_start",
                                                from_=self._accounts[0],
                                                to_=ZERO_SCORE_ADDRESS)
        tx2: dict = self.create_deploy_score_tx(score_root="sample_score_external_call_limit",
                                                score_name="sample_score_call_termination",
                                                from_=self._accounts[0],
                                                to_=ZERO_SCORE_ADDRESS)

        tx_results: List['TransactionResult'] = self.process_confirm_block_tx([tx1, tx2])
        start_score: 'Address' = tx_results[0].score_address
        termination_score: 'Address' = tx_results[1].score_address

        loop_count = 100

        tx: dict = self.create_score_call_tx(from_=self._admin,
                                             to_=start_score,
                                             func_name="invokeLoop",
                                             params={
                                                 '_to': str(termination_score),
                                                 '_name': 'invoke',
                                                 '_count': hex(loop_count)
                                             })

        self.process_confirm_block_tx([tx])

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
        tx1: dict = self.create_deploy_score_tx(score_root="sample_score_external_call_limit",
                                                score_name="sample_score_start",
                                                from_=self._accounts[0],
                                                to_=ZERO_SCORE_ADDRESS)
        tx2: dict = self.create_deploy_score_tx(score_root="sample_score_external_call_limit",
                                                score_name="sample_score_call_termination",
                                                from_=self._accounts[0],
                                                to_=ZERO_SCORE_ADDRESS)

        tx_results: List['TransactionResult'] = self.process_confirm_block_tx([tx1, tx2])
        start_score: 'Address' = tx_results[0].score_address
        termination_score: 'Address' = tx_results[1].score_address

        loop_count = 1025
        tx: dict = self.create_score_call_tx(from_=self._admin,
                                             to_=start_score,
                                             func_name="invokeLoop",
                                             params={
                                                 '_to': str(termination_score),
                                                 '_name': 'invoke',
                                                 '_count': hex(loop_count)
                                             })

        tx_results: List['TransactionResult'] = self.process_confirm_block_tx([tx],
                                                                              expected_status=False)
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
        tx1: dict = self.create_deploy_score_tx(score_root="sample_score_external_call_limit",
                                                score_name="sample_score_start",
                                                from_=self._accounts[0],
                                                to_=ZERO_SCORE_ADDRESS)
        tx2: dict = self.create_deploy_score_tx(score_root="sample_score_external_call_limit",
                                                score_name="sample_score_call_termination",
                                                from_=self._accounts[0],
                                                to_=ZERO_SCORE_ADDRESS)

        tx_results: List['TransactionResult'] = self.process_confirm_block_tx([tx1, tx2])
        start_score: 'Address' = tx_results[0].score_address
        termination_score: 'Address' = tx_results[1].score_address

        loop_count = 100
        tx: dict = self.create_score_call_tx(from_=self._admin,
                                             to_=start_score,
                                             func_name="invokeLoop",
                                             params={
                                                 '_to': str(termination_score),
                                                 '_name': 'query',
                                                 '_count': hex(loop_count)
                                             })

        self.process_confirm_block_tx([tx])

    def test_invoke_query_loop_over(self):
        # Deploys SCORE
        tx1: dict = self.create_deploy_score_tx(score_root="sample_score_external_call_limit",
                                                score_name="sample_score_start",
                                                from_=self._accounts[0],
                                                to_=ZERO_SCORE_ADDRESS)
        tx2: dict = self.create_deploy_score_tx(score_root="sample_score_external_call_limit",
                                                score_name="sample_score_call_termination",
                                                from_=self._accounts[0],
                                                to_=ZERO_SCORE_ADDRESS)

        tx_results: List['TransactionResult'] = self.process_confirm_block_tx([tx1, tx2])
        start_score: 'Address' = tx_results[0].score_address
        termination_score: 'Address' = tx_results[1].score_address

        loop_count = 1025
        tx: dict = self.create_score_call_tx(from_=self._admin,
                                             to_=start_score,
                                             func_name="invokeLoop",
                                             params={
                                                 '_to': str(termination_score),
                                                 '_name': 'query',
                                                 '_count': hex(loop_count)
                                             })

        tx_results: List['TransactionResult'] = self.process_confirm_block_tx([tx],
                                                                              expected_status=False)
        self.assertEqual(tx_results[0].failure.message, 'Too many external calls')

    def test_query_loop(self):
        # Deploys SCORE
        tx1: dict = self.create_deploy_score_tx(score_root="sample_score_external_call_limit",
                                                score_name="sample_score_start",
                                                from_=self._accounts[0],
                                                to_=ZERO_SCORE_ADDRESS)
        tx2: dict = self.create_deploy_score_tx(score_root="sample_score_external_call_limit",
                                                score_name="sample_score_call_termination",
                                                from_=self._accounts[0],
                                                to_=ZERO_SCORE_ADDRESS)

        tx_results: List['TransactionResult'] = self.process_confirm_block_tx([tx1, tx2])
        start_score: 'Address' = tx_results[0].score_address
        termination_score: 'Address' = tx_results[1].score_address

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
        self.assertEqual(response, loop_count)

    def test_query_loop_over(self):
        # Deploys SCORE
        tx1: dict = self.create_deploy_score_tx(score_root="sample_score_external_call_limit",
                                                score_name="sample_score_start",
                                                from_=self._accounts[0],
                                                to_=ZERO_SCORE_ADDRESS)
        tx2: dict = self.create_deploy_score_tx(score_root="sample_score_external_call_limit",
                                                score_name="sample_score_call_termination",
                                                from_=self._accounts[0],
                                                to_=ZERO_SCORE_ADDRESS)

        tx_results: List['TransactionResult'] = self.process_confirm_block_tx([tx1, tx2])
        start_score: 'Address' = tx_results[0].score_address
        termination_score: 'Address' = tx_results[1].score_address

        loop_count = 1025
        with self.assertRaises(InvalidRequestException) as context:
            self._query(
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
        tx1: dict = self.create_deploy_score_tx(score_root="sample_score_external_call_limit",
                                                score_name="sample_score_start",
                                                from_=self._accounts[0],
                                                to_=ZERO_SCORE_ADDRESS)
        tx2: dict = self.create_deploy_score_tx(score_root="sample_score_external_call_limit",
                                                score_name="sample_score_call_reflex",
                                                from_=self._accounts[0],
                                                to_=ZERO_SCORE_ADDRESS)

        tx_results: List['TransactionResult'] = self.process_confirm_block_tx([tx1, tx2])
        start_score: 'Address' = tx_results[0].score_address
        reflex_score: 'Address' = tx_results[1].score_address

        tx: dict = self.create_score_call_tx(from_=self._admin,
                                             to_=start_score,
                                             func_name="invokeRecursive",
                                             params={
                                                 '_to': str(reflex_score),
                                                 '_name': 'query'
                                             })

        tx_results: List['TransactionResult'] = self.process_confirm_block_tx([tx],
                                                                              expected_status=False)
        self.assertEqual(tx_results[0].failure.message, 'Max call stack size exceeded')

    def test_invoke_query_recursive(self):
        # Deploys SCORE
        tx1: dict = self.create_deploy_score_tx(score_root="sample_score_external_call_limit",
                                                score_name="sample_score_start",
                                                from_=self._accounts[0],
                                                to_=ZERO_SCORE_ADDRESS)
        tx2: dict = self.create_deploy_score_tx(score_root="sample_score_external_call_limit",
                                                score_name="sample_score_call_reflex",
                                                from_=self._accounts[0],
                                                to_=ZERO_SCORE_ADDRESS)

        tx_results: List['TransactionResult'] = self.process_confirm_block_tx([tx1, tx2])
        start_score: 'Address' = tx_results[0].score_address
        reflex_score: 'Address' = tx_results[1].score_address

        tx: dict = self.create_score_call_tx(from_=self._admin,
                                             to_=start_score,
                                             func_name="invokeRecursive",
                                             params={
                                                 '_to': str(reflex_score),
                                                 '_name': 'query'
                                             })
        tx_results: List['TransactionResult'] = self.process_confirm_block_tx([tx],
                                                                              expected_status=False)
        self.assertEqual(tx_results[0].failure.message, 'Max call stack size exceeded')

    def test_query_recursive(self):
        # Deploys SCORE
        tx1: dict = self.create_deploy_score_tx(score_root="sample_score_external_call_limit",
                                                score_name="sample_score_start",
                                                from_=self._accounts[0],
                                                to_=ZERO_SCORE_ADDRESS)
        tx2: dict = self.create_deploy_score_tx(score_root="sample_score_external_call_limit",
                                                score_name="sample_score_call_reflex",
                                                from_=self._accounts[0],
                                                to_=ZERO_SCORE_ADDRESS)

        tx_results: List['TransactionResult'] = self.process_confirm_block_tx([tx1, tx2])
        start_score: 'Address' = tx_results[0].score_address
        reflex_score: 'Address' = tx_results[1].score_address

        with self.assertRaises(StackOverflowException) as context:
            self._query(
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
