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
    from iconservice.iconscore.icon_score_result import TransactionResult
    from iconservice.base.address import Address


class TestIntegrateRevision(TestIntegrateBase):
    def setUp(self):
        super().setUp()
        # this unit test's purpose is just for test getRevision and setRevision method,
        # so don't need to add unit test whenever governance version is increased.
        self.update_governance("0_0_4")

    def test_governance_call_about_set_revision(self):
        expected_status = {"code": Revision.TWO.value, "name": "1.1.0"}

        query_request = {
            "version": self._version,
            "from": self._accounts[0],
            "to": GOVERNANCE_SCORE_ADDRESS,
            "dataType": "call",
            "data": {"method": "getRevision", "params": {}},
        }
        response = self._query(query_request)
        self.assertEqual(expected_status, response)

        next_revision = Revision.TWO.value + 1

        self.score_call(
            from_=self._admin,
            to_=GOVERNANCE_SCORE_ADDRESS,
            func_name="setRevision",
            params={"code": hex(next_revision), "name": "1.1.1"},
        )

        expected_status = {"code": next_revision, "name": "1.1.1"}
        response = self._query(query_request)
        self.assertEqual(expected_status, response)

    def test_revision_update_on_block(self):
        tx_results: List["TransactionResult"] = self.deploy_score(
            score_root="sample_scores",
            score_name="sample_revision_checker",
            from_=self._accounts[0],
        )
        score_address: "Address" = tx_results[0].score_address

        first_revision = Revision.TWO.value
        next_revision = first_revision + 1

        # 1-revision check
        # 2-revision update
        # 3-revision check

        tx1: dict = self.create_score_call_tx(
            from_=self._accounts[0],
            to_=score_address,
            func_name="checkRevision",
            params={},
        )
        tx2: dict = self.create_score_call_tx(
            from_=self._admin,
            to_=GOVERNANCE_SCORE_ADDRESS,
            func_name="setRevision",
            params={"code": hex(next_revision), "name": "1.1.1"},
        )
        tx3: dict = self.create_score_call_tx(
            from_=self._accounts[0],
            to_=score_address,
            func_name="checkRevision",
            params={},
        )

        tx_results: List["TransactionResult"] = self.process_confirm_block_tx(
            [tx1, tx2, tx3]
        )

        self.assertEqual(tx_results[0].status, int(True))
        self.assertEqual(tx_results[0].event_logs[0].indexed[1], first_revision)
        self.assertEqual(tx_results[1].status, int(True))
        self.assertEqual(tx_results[2].status, int(True))
        self.assertEqual(tx_results[2].event_logs[0].indexed[1], next_revision)

        query_request = {
            "version": self._version,
            "from": self._accounts[0],
            "to": GOVERNANCE_SCORE_ADDRESS,
            "dataType": "call",
            "data": {"method": "getRevision", "params": {}},
        }

        expected_status = {"code": next_revision, "name": "1.1.1"}
        response = self._query(query_request)
        self.assertEqual(expected_status, response)

        tx: dict = self.create_score_call_tx(
            from_=self._accounts[0],
            to_=score_address,
            func_name="checkRevision",
            params={},
        )

        tx_results: List["TransactionResult"] = self.process_confirm_block_tx([tx])
        self.assertEqual(tx_results[0].event_logs[0].indexed[1], next_revision)
