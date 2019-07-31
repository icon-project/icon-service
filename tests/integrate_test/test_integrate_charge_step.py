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

import json
from typing import TYPE_CHECKING, List

from iconservice.base.address import GOVERNANCE_SCORE_ADDRESS
from tests.integrate_test.test_integrate_base import TestIntegrateBase

if TYPE_CHECKING:
    from iconservice.iconscore.icon_score_result import TransactionResult
    from iconservice.base.address import Address


class TestIntegrateChargeStep(TestIntegrateBase):
    def test_json(self):
        dumps: bytes = json.dumps('').encode('utf-8')
        self.assertEqual(2, len(dumps))  # '""'
        dumps: bytes = json.dumps(None).encode('utf-8')
        self.assertEqual(4, len(dumps))  # 'null'

    def test_check_charge_step(self):
        self.update_governance()
        self.set_revision(3)

        self.score_call(from_=self._admin,
                        to_=GOVERNANCE_SCORE_ADDRESS,
                        func_name="setStepCost",
                        params={"stepType": "apiCall", "cost": "0x2710"})

        tx_results: List['TransactionResult'] = self.deploy_score("test_scores",
                                                                  "check_charge_step",
                                                                  self._accounts[0])
        score_addr: 'Address' = tx_results[0].score_address

        tx_results: List['TransactionResult'] = self.score_call(from_=self._accounts[0],
                                                                to_=score_addr,
                                                                func_name="test_str",
                                                                params={"bit": "0x000000000000"})
        base_step_used: int = tx_results[0].step_used

        tx_results: List['TransactionResult'] = self.score_call(from_=self._accounts[0],
                                                                to_=score_addr,
                                                                func_name="test_str",
                                                                params={"bit": "0x100000000000"})
        func = tx_results[0].step_used - base_step_used
        self.assertEqual(10000, func)

        tx_results: List['TransactionResult'] = self.score_call(from_=self._accounts[0],
                                                                to_=score_addr,
                                                                func_name="test_str",
                                                                params={"bit": "0x010000000000"})
        func = tx_results[0].step_used - base_step_used
        self.assertEqual(12000, func)

        tx_results: List['TransactionResult'] = self.score_call(from_=self._accounts[0],
                                                                to_=score_addr,
                                                                func_name="test_str",
                                                                params={"bit": "0x001000000000"})
        func = tx_results[0].step_used - base_step_used
        self.assertEqual(13000, func)

        tx_results: List['TransactionResult'] = self.score_call(from_=self._accounts[0],
                                                                to_=score_addr,
                                                                func_name="test_str",
                                                                params={"bit": "0x000000000001"})
        func = tx_results[0].step_used - base_step_used
        self.assertEqual(0, func)

        tx_results: List['TransactionResult'] = self.score_call(from_=self._accounts[0],
                                                                to_=score_addr,
                                                                func_name="test_str",
                                                                params={"bit": "0x000100000000"})
        func = tx_results[0].step_used - base_step_used
        self.assertEqual(150000, func)

        tx_results: List['TransactionResult'] = self.score_call(from_=self._accounts[0],
                                                                to_=score_addr,
                                                                func_name="test_str",
                                                                params={"bit": "0x000010000000"})
        func = tx_results[0].step_used - base_step_used
        self.assertEqual(150000, func)

        tx_results: List['TransactionResult'] = self.score_call(from_=self._accounts[0],
                                                                to_=score_addr,
                                                                func_name="test_str",
                                                                params={"bit": "0x000001000000"})
        func = tx_results[0].step_used - base_step_used
        self.assertEqual(15000, func)

        tx_results: List['TransactionResult'] = self.score_call(from_=self._accounts[0],
                                                                to_=score_addr,
                                                                func_name="test_str",
                                                                params={"bit": "0x000000100000"})
        func = tx_results[0].step_used - base_step_used
        self.assertEqual(51000, func)

        tx_results: List['TransactionResult'] = self.score_call(from_=self._accounts[0],
                                                                to_=score_addr,
                                                                func_name="test_str",
                                                                params={"bit": "0x000000010000"})
        func = tx_results[0].step_used - base_step_used
        self.assertEqual(52000, func)

        # Fail
        tx_results: List['TransactionResult'] = self.score_call(from_=self._accounts[0],
                                                                to_=score_addr,
                                                                func_name="test_str",
                                                                params={"bit": "0x000000001000"},
                                                                expected_status=False)
        func = tx_results[0].step_used - base_step_used
        self.assertEqual(40000, func)

        tx_results: List['TransactionResult'] = self.score_call(from_=self._accounts[0],
                                                                to_=score_addr,
                                                                func_name="test_str",
                                                                params={"bit": "0x000000000100"})
        func = tx_results[0].step_used - base_step_used
        self.assertEqual(700000, func)

        tx_results: List['TransactionResult'] = self.score_call(from_=self._accounts[0],
                                                                to_=score_addr,
                                                                func_name="test_str",
                                                                params={"bit": "0x000000000010"})
        func = tx_results[0].step_used - base_step_used
        self.assertEqual(700000, func)

    def test_check_charge_step2(self):
        self.update_governance()
        self.set_revision(3)

        self.score_call(from_=self._admin,
                        to_=GOVERNANCE_SCORE_ADDRESS,
                        func_name="setStepCost",
                        params={"stepType": "apiCall", "cost": "0x2710"})

        tx_results: List['TransactionResult'] = self.deploy_score("test_scores",
                                                                  "check_charge_step",
                                                                  self._accounts[0])
        score_addr: 'Address' = tx_results[0].score_address

        tx_results: List['TransactionResult'] = self.score_call(from_=self._accounts[0],
                                                                to_=score_addr,
                                                                func_name="test_str",
                                                                params={"bit": "0x000000000000"})
        base_step_used: int = tx_results[0].step_used

        # except Fail
        tx_results: List['TransactionResult'] = self.score_call(from_=self._accounts[0],
                                                                to_=score_addr,
                                                                func_name="test_str",
                                                                params={"bit": "0x111111110111"})
        func = tx_results[0].step_used - base_step_used
        self.assertEqual(1853000, func)
