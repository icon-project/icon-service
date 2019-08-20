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

from tests.integrate_test.test_integrate_base import TestIntegrateBase

if TYPE_CHECKING:
    from iconservice.base.address import Address
    from iconservice.iconscore.icon_score_result import TransactionResult


class TestScoreMemberVariable(TestIntegrateBase):

    def test_use_cached_score(self):
        tx_results: List['TransactionResult'] = self.deploy_score(
            score_root="sample_scores",
            score_name="sample_member_variable_score",
            from_=self._accounts[0])
        score_address: 'Address' = tx_results[0].score_address

        request = {
            "version": self._version,
            "from": self._accounts[0],
            "to": score_address,
            "dataType": "call",
            "data": {
                "method": "getName",
                "params": {}
            }
        }
        response = self._query(request)
        self.assertEqual(response, 'on_install')

    def test_use_every_time_created_score(self):
        self.update_governance()
        self.set_revision(3)

        tx_results: List['TransactionResult'] = self.deploy_score(
            score_root="sample_scores",
            score_name="sample_member_variable_score",
            from_=self._accounts[0])
        score_address: 'Address' = tx_results[0].score_address

        request = {
            "version": self._version,
            "from": self._accounts[0],
            "to": score_address,
            "dataType": "call",
            "data": {
                "method": "getName",
                "params": {}
            }
        }
        response = self._query(request)
        self.assertEqual(response, '__init__')
