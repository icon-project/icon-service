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

from typing import TYPE_CHECKING, Any, List

from iconservice.base.address import GOVERNANCE_SCORE_ADDRESS
from iconservice.base.exception import ExceptionCode
from iconservice.icon_constant import IconServiceFlag
from tests import raise_exception_start_tag, raise_exception_end_tag
from tests.integrate_test.test_integrate_base import TestIntegrateBase

if TYPE_CHECKING:
    from iconservice.iconscore.icon_score_result import TransactionResult


class TestIntegrateServiceConfiguration(TestIntegrateBase):

    def setUp(self):
        super().setUp()
        self.update_governance()

    def _set_service_conf(self, service_flag: Any, expected_status: bool = True) -> List['TransactionResult']:
        return self.score_call(from_=self._admin,
                               to_=GOVERNANCE_SCORE_ADDRESS,
                               func_name='updateServiceConfig',
                               params={"serviceFlag": service_flag},
                               expected_status=expected_status)

    def _assert_get_service_conf(self, service_flag: int):
        query_request = {
            "version": self._version,
            "from": self._admin,
            "to": GOVERNANCE_SCORE_ADDRESS,
            "dataType": "call",
            "data": {
                "method": "getServiceConfig",
            }
        }
        expect_ret = {}
        for flag in IconServiceFlag:
            if service_flag & flag == flag:
                expect_ret[flag.name] = True
            else:
                expect_ret[flag.name] = False

        response = self._query(query_request)
        self.assertEqual(response, expect_ret)

    def test_invalid_owner(self):
        raise_exception_start_tag("sample_invalid_owner")
        tx_results: List['TransactionResult'] = self.score_call(from_=self._accounts[0],
                                                                to_=GOVERNANCE_SCORE_ADDRESS,
                                                                func_name='updateServiceConfig',
                                                                params={"serviceFlag": hex(IconServiceFlag.AUDIT)},
                                                                expected_status=False)
        raise_exception_end_tag("sample_invalid_owner")

        self.assertEqual(tx_results[0].failure.code, ExceptionCode.SCORE_ERROR)
        self.assertEqual(tx_results[0].failure.message, f'Invalid sender: not owner')

    def test_set_service_configuration(self):
        max_flag = 0
        for flag in IconServiceFlag:
            max_flag |= flag

        for conf in range(max_flag):
            tx_results: List['TransactionResult'] = self._set_service_conf(hex(conf))
            self.assertEqual(tx_results[0].status, int(True), f'Failed conf: {conf}')
            self._assert_get_service_conf(conf)

    def test_set_service_configuration_wrong(self):
        wrong_conf = [
            hex(-1),
            str(self._admin.address),
            "0xfffff",
            "abc",
            hex(65535),
        ]

        for conf in wrong_conf:
            self._set_service_conf(conf, expected_status=False)
