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
from typing import TYPE_CHECKING, Any

from iconservice.base.address import ZERO_SCORE_ADDRESS, GOVERNANCE_SCORE_ADDRESS
from iconservice.icon_constant import REVISION_2, REVISION_3
from tests.integrate_test.test_integrate_base import TestIntegrateBase

if TYPE_CHECKING:
    from iconservice.base.address import Address


class TestIntegrateArrayDBPatch(TestIntegrateBase):

    def _update_governance(self):
        tx = self._make_deploy_tx("test_builtin",
                                  "0_0_4/governance",
                                  self._admin,
                                  GOVERNANCE_SCORE_ADDRESS)
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))

    def _deploy_score(self) -> Any:
        address = ZERO_SCORE_ADDRESS
        tx = self._make_deploy_tx("test_scores",
                                  "test_array_db",
                                  self._addr_array[0],
                                  address,
                                  deploy_params={})

        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        return tx_results[0].score_address

    def _call_set_value(self, from_: 'Address', to: 'Address', step_limit=None):
        tx = self._make_score_call_tx(from_,
                                      to,
                                      'set_values', {})

        if step_limit:
            tx['params']['stepLimit'] = step_limit

        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        return tx_results[0]

    def _external_call(self, from_addr: 'Address', score_addr: 'Address', func_name: str, params: dict):
        tx = self._make_score_call_tx(from_addr, score_addr, func_name, params)
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        return tx_results[0]

    def test_array_db_defective(self):
        self._update_governance()

        expected_status = {
            "code": REVISION_2,
            "name": "1.1.0"
        }

        query_request = {
            "version": self._version,
            "from": self._addr_array[0],
            "to": GOVERNANCE_SCORE_ADDRESS,
            "dataType": "call",
            "data": {
                "method": "getRevision",
                "params": {}
            }
        }
        response = self._query(query_request)
        self.assertEqual(expected_status, response)

        score_address = self._deploy_score()
        tx_result = self._call_set_value(self._addr_array[0], score_address)
        self.assertEqual(tx_result.status, int(True))
        tx_result = self._call_set_value(self._addr_array[1], score_address, 140519)
        self.assertEqual(tx_result.status, int(False))
        tx_result = self._call_set_value(self._addr_array[2], score_address)
        self.assertEqual(tx_result.status, int(True))

        response = self._query(
            {
                'to': score_address,
                'dataType': 'call',
                'data': {
                    'method': 'get_values'
                }
            }
        )

        self.assertEqual(len(response), 3)

    def test_array_db_patch(self):
        self._update_governance()

        tx_result = self._external_call(self._admin,
                                        GOVERNANCE_SCORE_ADDRESS,
                                        'setRevision',
                                        {"code": hex(REVISION_3), "name": "1.1.1"})
        self.assertEqual(tx_result.status, int(True))

        expected_status = {
            "code": REVISION_3,
            "name": "1.1.1"
        }
        query_request = {
            "version": self._version,
            "from": self._addr_array[0],
            "to": GOVERNANCE_SCORE_ADDRESS,
            "dataType": "call",
            "data": {
                "method": "getRevision",
                "params": {}
            }
        }
        response = self._query(query_request)
        self.assertEqual(expected_status, response)

        score_address = self._deploy_score()
        tx_result = self._call_set_value(self._addr_array[0], score_address)
        self.assertEqual(tx_result.status, int(True))
        tx_result = self._call_set_value(self._addr_array[1], score_address, 140519)
        self.assertEqual(tx_result.status, int(False))
        tx_result = self._call_set_value(self._addr_array[2], score_address)
        self.assertEqual(tx_result.status, int(True))

        response = self._query(
            {
                'to': score_address,
                'dataType': 'call',
                'data': {
                    'method': 'get_values'
                }
            }
        )

        self.assertEqual(len(response), 2)


if __name__ == '__main__':
    unittest.main()
