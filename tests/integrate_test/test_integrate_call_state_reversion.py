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
from tests.integrate_test.test_integrate_base import TestIntegrateBase


class TestIntegrateCallStateReversion(TestIntegrateBase):

    def test_invoke_chain(self):
        prev_block, tx_results = self._make_and_req_block([
            self._make_deploy_tx(
                "sample_score_call_state_reversion",
                "sample_score",
                self._addr_array[0],
                ZERO_SCORE_ADDRESS,
                {
                    '_name': 'E'
                })
        ])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))
        score_e = tx_results[0].score_address

        prev_block, tx_results = self._make_and_req_block([
            self._make_deploy_tx(
                "sample_score_call_state_reversion",
                "sample_score",
                self._addr_array[0],
                ZERO_SCORE_ADDRESS,
                {
                    '_name': 'D',
                    '_nextAddress': str(score_e),
                    '_nextFunction': 'invoke'
                })
        ])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))
        score_d = tx_results[0].score_address

        prev_block, tx_results = self._make_and_req_block([
            self._make_deploy_tx(
                "sample_score_call_state_reversion",
                "sample_score",
                self._addr_array[0],
                ZERO_SCORE_ADDRESS,
                {
                    '_name': 'C',
                    '_nextAddress': str(score_d),
                    '_nextFunction': 'invoke',
                    '_shouldHandleException': '0x1'
                })
        ])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))
        score_c = tx_results[0].score_address

        prev_block, tx_results = self._make_and_req_block([
            self._make_deploy_tx(
                "sample_score_call_state_reversion",
                "sample_score",
                self._addr_array[0],
                ZERO_SCORE_ADDRESS,
                {
                    '_name': 'B',
                    '_nextAddress': str(score_c),
                    '_nextFunction': 'invoke'
                })
        ])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))
        score_b = tx_results[0].score_address

        prev_block, tx_results = self._make_and_req_block([
            self._make_deploy_tx(
                "sample_score_call_state_reversion",
                "sample_score",
                self._addr_array[0],
                ZERO_SCORE_ADDRESS,
                {
                    '_name': 'A',
                    '_nextAddress': str(score_b),
                    '_nextFunction': 'invoke'
                })
        ])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))
        score_a = tx_results[0].score_address

        value = 100 * self._icx_factor
        prev_block, tx_results = self._make_and_req_block([
            self._make_score_call_tx(
                self._genesis,
                score_a,
                'invoke',
                {},
                value)
        ])

        self._write_precommit_state(prev_block)

        # Checks if the result is successful
        self.assertEqual(tx_results[0].status, True)

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
        response = self._query({"address": score_a}, 'icx_getBalance')
        self.assertNotEqual(response, 0)

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
        response = self._query({"address": score_b}, 'icx_getBalance')
        self.assertNotEqual(response, 0)

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
        response = self._query({"address": score_c}, 'icx_getBalance')
        self.assertNotEqual(response, 0)

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
        response = self._query({"address": score_d}, 'icx_getBalance')
        self.assertEqual(response, 0)

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
        response = self._query({"address": score_d}, 'icx_getBalance')
        self.assertEqual(response, 0)

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
        prev_block, tx_results = self._make_and_req_block([
            self._make_deploy_tx(
                "sample_score_call_state_reversion",
                "sample_score",
                self._addr_array[0],
                ZERO_SCORE_ADDRESS,
                {
                    '_name': 'E'
                })
        ])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))
        score_e = tx_results[0].score_address

        prev_block, tx_results = self._make_and_req_block([
            self._make_deploy_tx(
                "sample_score_call_state_reversion",
                "sample_score",
                self._addr_array[0],
                ZERO_SCORE_ADDRESS,
                {
                    '_name': 'D',
                    '_nextAddress': str(score_e),
                    '_nextFunction': 'query'
                })
        ])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))
        score_d = tx_results[0].score_address

        prev_block, tx_results = self._make_and_req_block([
            self._make_deploy_tx(
                "sample_score_call_state_reversion",
                "sample_score",
                self._addr_array[0],
                ZERO_SCORE_ADDRESS,
                {
                    '_name': 'C',
                    '_nextAddress': str(score_d),
                    '_nextFunction': 'invoke',
                    '_shouldHandleException': '0x1'
                })
        ])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))
        score_c = tx_results[0].score_address

        prev_block, tx_results = self._make_and_req_block([
            self._make_deploy_tx(
                "sample_score_call_state_reversion",
                "sample_score",
                self._addr_array[0],
                ZERO_SCORE_ADDRESS,
                {
                    '_name': 'B',
                    '_nextAddress': str(score_c),
                    '_nextFunction': 'invoke'
                })
        ])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))
        score_b = tx_results[0].score_address

        prev_block, tx_results = self._make_and_req_block([
            self._make_deploy_tx(
                "sample_score_call_state_reversion",
                "sample_score",
                self._addr_array[0],
                ZERO_SCORE_ADDRESS,
                {
                    '_name': 'A',
                    '_nextAddress': str(score_b),
                    '_nextFunction': 'invoke'
                })
        ])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))
        score_a = tx_results[0].score_address

        value = 100 * self._icx_factor
        prev_block, tx_results = self._make_and_req_block([
            self._make_score_call_tx(
                self._genesis,
                score_a,
                'invoke',
                {},
                value)
        ])

        self._write_precommit_state(prev_block)

        # Checks if the result is successful
        self.assertEqual(tx_results[0].status, True)

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
        response = self._query({"address": score_a}, 'icx_getBalance')
        self.assertNotEqual(response, 0)

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
        response = self._query({"address": score_b}, 'icx_getBalance')
        self.assertNotEqual(response, 0)

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
        response = self._query({"address": score_c}, 'icx_getBalance')
        self.assertNotEqual(response, 0)

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
        response = self._query({"address": score_d}, 'icx_getBalance')
        self.assertEqual(response, 0)

        # Changes in E is reverted
        response = self._query({"address": score_d}, 'icx_getBalance')
        self.assertEqual(response, 0)

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


if __name__ == '__main__':
    unittest.main()
