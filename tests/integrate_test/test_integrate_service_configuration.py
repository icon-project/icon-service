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
from typing import Any

from iconservice.base.address import GOVERNANCE_SCORE_ADDRESS, Address, AddressPrefix
from iconservice.base.exception import ExceptionCode
from iconservice.icon_constant import IconServiceFlag
from tests import raise_exception_start_tag, raise_exception_end_tag
from tests.integrate_test.test_integrate_base import TestIntegrateBase


class TestIntegrateServiceConfiguration(TestIntegrateBase):

    def setUp(self):
        super().setUp()
        self._update_governance()

    def _update_governance(self):
        tx = self._make_deploy_tx("test_builtin",
                                  "latest_version/governance",
                                  self._admin,
                                  GOVERNANCE_SCORE_ADDRESS)
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)

    def _set_service_conf(self, service_flag: Any) -> Any:
        params = {
            'serviceFlag': service_flag
        }
        tx = self._make_score_call_tx(self._admin,
                                      GOVERNANCE_SCORE_ADDRESS,
                                      'updateServiceConfig',
                                      params=params,
                                      pre_validation_enabled=False)

        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        return tx_results[0]

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
        params = {
            'serviceFlag': hex(IconServiceFlag.AUDIT)
        }
        tx = self._make_score_call_tx(Address.from_prefix_and_int(AddressPrefix.CONTRACT, 2),
                                      GOVERNANCE_SCORE_ADDRESS,
                                      'updateServiceConfig',
                                      params=params)

        raise_exception_start_tag("test_invalid_owner")
        prev_block, tx_results = self._make_and_req_block([tx])
        raise_exception_end_tag("test_invalid_owner")

        self._write_precommit_state(prev_block)

        self.assertEqual(tx_results[0].status, int(False))
        self.assertEqual(tx_results[0].failure.code, ExceptionCode.SCORE_ERROR)
        self.assertEqual(tx_results[0].failure.message, f'Invalid sender: not owner')

    def test_set_service_configuration(self):
        max_flag = 0
        for flag in IconServiceFlag:
            max_flag |= flag

        for conf in range(max_flag):
            tx_result = self._set_service_conf(hex(conf))
            self.assertEqual(tx_result.status, int(True), f'Failed conf: {conf}')
            self._assert_get_service_conf(conf)

    def test_set_service_configuration_wrong(self):
        wrong_conf = [
            1,
            -1,
            0xfffff,
            'abc',
            True,
            False,
            hex(-1),
            hex(65535),
        ]

        for conf in wrong_conf:
            tx_result = self._set_service_conf(conf)
            self.assertEqual(tx_result.status, int(False), f'Failed conf: {conf}')


if __name__ == '__main__':
    unittest.main()
