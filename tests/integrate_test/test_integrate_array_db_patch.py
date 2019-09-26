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

from iconservice.base.address import GOVERNANCE_SCORE_ADDRESS
from iconservice.icon_constant import Revision
from tests.integrate_test.test_integrate_base import TestIntegrateBase

if TYPE_CHECKING:
    from iconservice.base.address import Address
    from iconservice.iconscore.icon_score_result import TransactionResult


class TestIntegrateArrayDBPatch(TestIntegrateBase):
    def test_array_db_defective(self):
        self.update_governance("0_0_4")

        expected_status = {
            "code": Revision.TWO.value,
            "name": "1.1.0"
        }

        query_request = {
            "version": self._version,
            "from": self._accounts[0],
            "to": GOVERNANCE_SCORE_ADDRESS,
            "dataType": "call",
            "data": {
                "method": "getRevision",
                "params": {}
            }
        }
        response = self._query(query_request)
        self.assertEqual(expected_status, response)

        tx_results: List['TransactionResult'] = self.deploy_score("sample_scores",
                                                                  "sample_array_db",
                                                                  self._accounts[0])
        score_address: 'Address' = tx_results[0].score_address

        self.score_call(self._accounts[0], score_address, "set_values")
        self.score_call(self._accounts[1], score_address, "set_values", step_limit=140519, expected_status=False)
        self.score_call(self._accounts[2], score_address, "set_values")

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
        self.update_governance("0_0_4")
        self.set_revision(Revision.THREE.value)

        expected_status = {
            "code": Revision.THREE.value,
            "name": f"1.1.{Revision.THREE.value}"
        }
        query_request = {
            "version": self._version,
            "from": self._accounts[0],
            "to": GOVERNANCE_SCORE_ADDRESS,
            "dataType": "call",
            "data": {
                "method": "getRevision",
                "params": {}
            }
        }
        response = self._query(query_request)
        self.assertEqual(expected_status, response)

        tx_results: List['TransactionResult'] = self.deploy_score("sample_scores",
                                                                  "sample_array_db",
                                                                  self._accounts[0])
        score_address: 'Address' = tx_results[0].score_address

        self.score_call(self._accounts[0], score_address, "set_values")
        self.score_call(self._accounts[1], score_address, "set_values", step_limit=140519, expected_status=False)
        self.score_call(self._accounts[2], score_address, "set_values")

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
