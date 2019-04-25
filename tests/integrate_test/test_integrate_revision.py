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
from iconservice.icon_constant import REVISION_2
from tests.integrate_test.test_integrate_base import TestIntegrateBase

if TYPE_CHECKING:
    from iconservice.base.address import Address


class TestIntegrateRevision(TestIntegrateBase):
    """
    audit on
    test governance deploy audit accept, reject
    """

    def _update_governance_0_0_4(self):
        tx = self._make_deploy_tx("sample_builtin",
                                  "0_0_4/governance",
                                  self._admin,
                                  GOVERNANCE_SCORE_ADDRESS)
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))

    def _deploy_score(self, score_path: str, value: int, update_score_addr: 'Address' = None) -> Any:
        address = ZERO_SCORE_ADDRESS
        if update_score_addr:
            address = update_score_addr

        tx = self._make_deploy_tx("sample_deploy_scores",
                                  score_path,
                                  self._addr_array[0],
                                  address,
                                  deploy_params={'value': hex(value * self._icx_factor)})

        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        return tx_results[0]

    def _external_call(self, from_addr: 'Address', score_addr: 'Address', func_name: str, params: dict):
        tx = self._make_score_call_tx(from_addr, score_addr, func_name, params)
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        return tx_results[0]

    def test_governance_call_about_set_revision(self):
        # this unit test's purpose is just for test getRevision and setRevision method,
        # so don't need to add unit test whenever governance version is increased.
        self._update_governance_0_0_4()

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

        next_revision = REVISION_2 + 1

        tx_result = self._external_call(self._admin,
                                        GOVERNANCE_SCORE_ADDRESS,
                                        'setRevision',
                                        {"code": hex(next_revision), "name": "1.1.1"})
        self.assertEqual(tx_result.status, int(True))

        expected_status = {
            "code": next_revision,
            "name": "1.1.1"
        }
        response = self._query(query_request)
        self.assertEqual(expected_status, response)

    def test_revision_update_on_block(self):
        # this unit test's purpose is just for test getRevision and setRevision method,
        # so don't need to add unit test whenever governance version is increased.
        self._update_governance_0_0_4()

        tx = self._make_deploy_tx("sample_scores",
                                  "sample_revision_checker",
                                  self._addr_array[0],
                                  ZERO_SCORE_ADDRESS)

        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)

        first_revision = REVISION_2
        next_revision = first_revision + 1

        checker_address = tx_results[0].score_address

        # 1-revision check
        # 2-revision update
        # 3-revision check
        prev_block, tx_results = self._make_and_req_block([
            self._make_score_call_tx(
                self._addr_array[0],
                checker_address,
                "checkRevision",
                {}),
            self._make_score_call_tx(
                self._admin,
                GOVERNANCE_SCORE_ADDRESS,
                'setRevision',
                {"code": hex(next_revision), "name": "1.1.1"},
            ),
            self._make_score_call_tx(
                self._addr_array[0],
                checker_address,
                "checkRevision",
                {})
        ])
        self._write_precommit_state(prev_block)

        self.assertEqual(tx_results[0].status, int(True))
        self.assertEqual(tx_results[0].event_logs[0].indexed[1], first_revision)
        self.assertEqual(tx_results[1].status, int(True))
        self.assertEqual(tx_results[2].status, int(True))
        self.assertEqual(tx_results[2].event_logs[0].indexed[1], next_revision)

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

        expected_status = {
            "code": next_revision,
            "name": "1.1.1"
        }
        response = self._query(query_request)
        self.assertEqual(expected_status, response)

        prev_block, tx_results = self._make_and_req_block([
            self._make_score_call_tx(
                self._addr_array[0],
                checker_address,
                "checkRevision",
                {})
        ])
        self._write_precommit_state(prev_block)

        self.assertEqual(tx_results[0].status, int(True))
        self.assertEqual(tx_results[0].event_logs[0].indexed[1], next_revision)


if __name__ == '__main__':
    unittest.main()
