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

from typing import List, TYPE_CHECKING

from iconservice.icon_constant import ICX_IN_LOOP
from tests.integrate_test.test_integrate_base import TestIntegrateBase

if TYPE_CHECKING:
    from iconservice.iconscore.icon_score_result import TransactionResult
    from iconservice.base.address import Address


class TestIntegrateCallStateReversion(TestIntegrateBase):
    def test_invoke_chain(self):
        tx_results: List['TransactionResult'] = self.deploy_score("sample_score_call_state_reversion",
                                                                  "sample_score",
                                                                  self._accounts[0],
                                                                  deploy_params={
                                                                      '_name': 'E'
                                                                  })
        score_e: 'Address' = tx_results[0].score_address

        tx_results: List['TransactionResult'] = self.deploy_score("sample_score_call_state_reversion",
                                                                  "sample_score",
                                                                  self._accounts[0],
                                                                  deploy_params={
                                                                      '_name': 'D',
                                                                      '_nextAddress': str(score_e),
                                                                      '_nextFunction': 'invoke'
                                                                  })
        score_d: 'Address' = tx_results[0].score_address

        tx_results: List['TransactionResult'] = self.deploy_score("sample_score_call_state_reversion",
                                                                  "sample_score",
                                                                  self._accounts[0],
                                                                  deploy_params={
                                                                      '_name': 'C',
                                                                      '_nextAddress': str(score_d),
                                                                      '_nextFunction': 'invoke',
                                                                      '_shouldHandleException': '0x1'
                                                                  })
        score_c: 'Address' = tx_results[0].score_address

        tx_results: List['TransactionResult'] = self.deploy_score("sample_score_call_state_reversion",
                                                                  "sample_score",
                                                                  self._accounts[0],
                                                                  deploy_params={
                                                                      '_name': 'B',
                                                                      '_nextAddress': str(score_c),
                                                                      '_nextFunction': 'invoke'
                                                                  })
        score_b: 'Address' = tx_results[0].score_address

        tx_results: List['TransactionResult'] = self.deploy_score("sample_score_call_state_reversion",
                                                                  "sample_score",
                                                                  self._accounts[0],
                                                                  deploy_params={
                                                                      '_name': 'A',
                                                                      '_nextAddress': str(score_b),
                                                                      '_nextFunction': 'invoke'
                                                                  })
        score_a: 'Address' = tx_results[0].score_address

        value = 100 * ICX_IN_LOOP
        tx_results: List['TransactionResult'] = self.score_call(from_=self._admin,
                                                                to_=score_a,
                                                                func_name="invoke",
                                                                params={},
                                                                value=value)

        # Changes in A is OK
        response = self._query(
            {
                'to': score_a,
                'dataType': 'call',
                'data': {
                    'method': 'getInvoked'
                }
            }
        )
        self.assertEqual(response, True)

        balance: int = self.get_balance(score_a)
        self.assertNotEqual(response, balance)

        # Changes in B is OK
        response = self._query(
            {
                'to': score_b,
                'dataType': 'call',
                'data': {
                    'method': 'getInvoked'
                }
            }
        )
        self.assertEqual(response, True)

        balance: int = self.get_balance(score_b)
        self.assertNotEqual(response, balance)

        # Changes in C is OK
        response = self._query(
            {
                'to': score_c,
                'dataType': 'call',
                'data': {
                    'method': 'getInvoked'
                }
            }
        )
        self.assertEqual(response, True)

        balance: int = self.get_balance(score_c)
        self.assertNotEqual(response, balance)

        # Changes in D is reverted
        response = self._query(
            {
                'to': score_d,
                'dataType': 'call',
                'data': {
                    'method': 'getInvoked'
                }
            }
        )
        self.assertEqual(response, False)

        balance: int = self.get_balance(score_d)
        self.assertEqual(response, balance)

        # Changes in E is reverted
        response = self._query(
            {
                'to': score_e,
                'dataType': 'call',
                'data': {
                    'method': 'getInvoked'
                }
            }
        )
        self.assertEqual(response, False)

        balance: int = self.get_balance(score_e)
        self.assertEqual(response, balance)

        events_data = [x.data for x in tx_results[0].event_logs if x.indexed[0] == 'Event(str,str,Address)']
        score_names_event_occurred = [x[0] for x in events_data]

        # Checks Events from 'A', 'B', 'C' exist
        self.assertIn('A', score_names_event_occurred)
        self.assertIn('B', score_names_event_occurred)
        self.assertIn('C', score_names_event_occurred)

        # Checks Events from 'D', 'E' not exist
        self.assertNotIn('D', score_names_event_occurred)
        self.assertNotIn('E', score_names_event_occurred)

        # Checks msg stack is properly reverted every call
        self.assertEqual(events_data[0][2], events_data[5][2])
        self.assertEqual(events_data[1][2], events_data[4][2])
        self.assertEqual(events_data[2][2], events_data[3][2])

    def test_invoke_query_mixed(self):
        tx_results: List['TransactionResult'] = self.deploy_score("sample_score_call_state_reversion",
                                                                  "sample_score",
                                                                  self._accounts[0],
                                                                  deploy_params={
                                                                      '_name': 'E'
                                                                  })
        score_e: 'Address' = tx_results[0].score_address

        tx_results: List['TransactionResult'] = self.deploy_score("sample_score_call_state_reversion",
                                                                  "sample_score",
                                                                  self._accounts[0],
                                                                  deploy_params={
                                                                      '_name': 'D',
                                                                      '_nextAddress': str(score_e),
                                                                      '_nextFunction': 'invoke'
                                                                  })
        score_d: 'Address' = tx_results[0].score_address

        tx_results: List['TransactionResult'] = self.deploy_score("sample_score_call_state_reversion",
                                                                  "sample_score",
                                                                  self._accounts[0],
                                                                  deploy_params={
                                                                      '_name': 'C',
                                                                      '_nextAddress': str(score_d),
                                                                      '_nextFunction': 'invoke',
                                                                      '_shouldHandleException': '0x1'
                                                                  })
        score_c: 'Address' = tx_results[0].score_address

        tx_results: List['TransactionResult'] = self.deploy_score("sample_score_call_state_reversion",
                                                                  "sample_score",
                                                                  self._accounts[0],
                                                                  deploy_params={
                                                                      '_name': 'B',
                                                                      '_nextAddress': str(score_c),
                                                                      '_nextFunction': 'invoke'
                                                                  })
        score_b: 'Address' = tx_results[0].score_address

        tx_results: List['TransactionResult'] = self.deploy_score("sample_score_call_state_reversion",
                                                                  "sample_score",
                                                                  self._accounts[0],
                                                                  deploy_params={
                                                                      '_name': 'A',
                                                                      '_nextAddress': str(score_b),
                                                                      '_nextFunction': 'invoke'
                                                                  })
        score_a: 'Address' = tx_results[0].score_address

        value = 100 * ICX_IN_LOOP
        tx_results: List['TransactionResult'] = self.score_call(from_=self._admin,
                                                                to_=score_a,
                                                                func_name="invoke",
                                                                params={},
                                                                value=value)

        # Changes in A is OK
        response = self._query(
            {
                'to': score_a,
                'dataType': 'call',
                'data': {
                    'method': 'getInvoked'
                }
            }
        )
        self.assertEqual(response, True)

        balance: int = self.get_balance(score_a)
        self.assertNotEqual(response, balance)

        # Changes in B is OK
        response = self._query(
            {
                'to': score_b,
                'dataType': 'call',
                'data': {
                    'method': 'getInvoked'
                }
            }
        )
        self.assertEqual(response, True)

        balance: int = self.get_balance(score_b)
        self.assertNotEqual(response, balance)

        # Changes in C is OK
        response = self._query(
            {
                'to': score_c,
                'dataType': 'call',
                'data': {
                    'method': 'getInvoked'
                }
            }
        )
        self.assertEqual(response, True)

        balance: int = self.get_balance(score_c)
        self.assertNotEqual(response, balance)

        # Changes in D is reverted
        response = self._query(
            {
                'to': score_d,
                'dataType': 'call',
                'data': {
                    'method': 'getInvoked'
                }
            }
        )
        self.assertEqual(response, False)
        balance: int = self.get_balance(score_d)
        self.assertEqual(response, balance)

        # Changes in E is reverted
        balance: int = self.get_balance(score_e)
        self.assertEqual(response, balance)

        events_data = [x.data for x in tx_results[0].event_logs if x.indexed[0] == 'Event(str,str,Address)']
        score_names_event_occurred = [x[0] for x in events_data]

        # Checks Events from 'A', 'B', 'C' exist
        self.assertIn('A', score_names_event_occurred)
        self.assertIn('B', score_names_event_occurred)
        self.assertIn('C', score_names_event_occurred)

        # Checks Events from 'D', 'E' not exist
        self.assertNotIn('D', score_names_event_occurred)
        self.assertNotIn('E', score_names_event_occurred)

        # Checks msg stack is properly reverted every call
        self.assertEqual(events_data[0][2], events_data[5][2])
        self.assertEqual(events_data[1][2], events_data[4][2])
        self.assertEqual(events_data[2][2], events_data[3][2])
