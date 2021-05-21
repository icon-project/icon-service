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
import time
from typing import TYPE_CHECKING, List, Any

from iconservice.base.address import Address
from tests.integrate_test.test_integrate_base import TestIntegrateBase

if TYPE_CHECKING:
    from iconservice.iconscore.icon_score_result import TransactionResult


class TestIntegrateScores(TestIntegrateBase):
    def query_db_returns(self,
                         to_: 'Address',
                         index: int) -> Any:
        query_request = {
            "version": self._version,
            "from": self._admin,
            "to": to_,
            "dataType": "call",
            "data": {
                "method": f"get_value{index}",
                "params": {}
            }
        }
        return self._query(query_request)

    def test_db_returns(self):
        tx_results: List['TransactionResult'] = self.deploy_score(
            score_root="sample_scores",
            score_name="sample_array_db2",
            from_=self._accounts[0],
            deploy_params={})
        score_address: 'Address' = tx_results[0].score_address

        def _put_address():
            tx_list = []
            for _ in range(500):
                tx = self.create_score_call_tx(self._accounts[0].address, score_address, "add_value")
                tx_list.append(tx)

        for _ in range(160):
            _put_address()

        start = time.time()
        ret = self.query_score(self._accounts[0], score_address, "check", {"address": f"hx{'1'*40}"})
        end = time.time()
        print("GET time : ", ret, end - start)
