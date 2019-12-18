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

from iconservice.icon_inner_service import MakeResponse
from tests.integrate_test.test_integrate_base import TestIntegrateBase

if TYPE_CHECKING:
    from iconservice.base.address import Address
    from iconservice.iconscore.icon_score_result import TransactionResult


def _create_query_request(from_: 'Address', to_: 'Address', method: str):
    return {
        "version": 3,
        "from": from_,
        "to": to_,
        "dataType": "call",
        "data": {"method": method}
    }


class TestScoreGlobalVariable(TestIntegrateBase):

    def setUp(self):
        super().setUp()

        sender: 'Address' = self._accounts[0].address

        tx_results: List['TransactionResult'] = self.deploy_score(
            score_root="sample_scores",
            score_name="sample_global_variable_score",
            from_=sender,
            expected_status=True)
        score_address: 'Address' = tx_results[0].score_address

        request = _create_query_request(sender, score_address, "hello")
        response = self._query(request)
        self.assertEqual(response, "hello")

        self.sender = sender
        self.score_address = score_address

    def _create_query_request(self, method: str):
        return _create_query_request(self.sender, self.score_address, method)

    def test_global_dict(self):
        expected_response = {"a": 1, "b": [2, 3], "c": {"d": 4}}
        expected_converted_response = {"a": "0x1", "b": ["0x2", "0x3"], "c": {"d": "0x4"}}
        request: dict = self._create_query_request("getGlobalDict")

        # First score call for query
        response_0 = self._query(request)
        assert isinstance(response_0, dict)
        assert response_0 == expected_response

        # make_response() does in-place value type conversion in response_0
        converted_response = MakeResponse.make_response(response_0)
        assert converted_response == expected_converted_response
        assert response_0 != expected_response
        assert id(converted_response) == id(response_0)

        # Check if the response is deeply copied on every query call
        response_1: dict = self._query(request)
        assert isinstance(response_1, dict)
        assert id(response_1) != id(response_0)
        assert response_1 == expected_response

    def test_global_list(self):
        expected_response = [1, {"a": 1}, ["c", 2]]
        expected_converted_response = ["0x1", {"a": "0x1"}, ["c", "0x2"]]
        request: dict = self._create_query_request("getGlobalList")

        # First score call for query
        response_0: list = self._query(request)
        assert isinstance(response_0, list)
        assert response_0 == expected_response

        # Check if the response is deeply copied on every query call
        converted_response = MakeResponse.make_response(response_0)
        assert converted_response == expected_converted_response
        assert id(converted_response) == id(response_0)

        response_1 = self._query(request)
        assert isinstance(response_1, list)
        assert id(response_1) != id(response_0)
        assert response_1 == expected_response

    def test_global_tuple(self):
        expected_response = ({"a": 1}, 2, ["c", 2])
        request: dict = self._create_query_request("getGlobalTuple")

        # First score call for query
        response_0: tuple = self._query(request)
        assert isinstance(response_0, tuple)
        assert response_0 == expected_response

        converted_response = MakeResponse.make_response(response_0)
        assert converted_response == expected_response
        assert response_0 == expected_response
        assert id(converted_response) == id(response_0)

        response_1 = self._query(request)
        assert isinstance(response_1, tuple)
        assert id(response_1) != id(response_0)
        assert response_1 == expected_response
