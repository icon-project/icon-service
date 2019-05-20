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

from iconservice.base.address import ZERO_SCORE_ADDRESS, GOVERNANCE_SCORE_ADDRESS
from tests.integrate_test.test_integrate_base import TestIntegrateBase, LATEST_GOVERNANCE


class TestIntegrateChargeStep(TestIntegrateBase):
    def _update_governance(self):
        tx = self._make_deploy_tx("test_builtin",
                                  LATEST_GOVERNANCE,
                                  self._admin,
                                  GOVERNANCE_SCORE_ADDRESS)
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)

    def _set_revision(self, revision):
        set_revision_tx = self._make_score_call_tx(self._admin, GOVERNANCE_SCORE_ADDRESS, 'setRevision',
                                                   {"code": hex(revision), "name": f"1.1.{revision}"})
        prev_block, tx_results = self._make_and_req_block([set_revision_tx])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))

    def test_json(self):
        dumps: bytes = json.dumps('').encode('utf-8')
        self.assertEqual(2, len(dumps)) # '""'
        dumps: bytes = json.dumps(None).encode('utf-8')
        self.assertEqual(4, len(dumps)) # 'null'

    def test_check_charge_step(self):
        self._update_governance()
        self._set_revision(3)

        tx = self._make_score_call_tx(self._admin, GOVERNANCE_SCORE_ADDRESS,
                                      'setStepCost',
                                      {"stepType": "apiCall", "cost": "0x2710"})

        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))

        tx = self._make_deploy_tx("test_scores",
                                  "check_charge_step",
                                  self._addr_array[0],
                                  ZERO_SCORE_ADDRESS)

        prev_block, tx_results = self._make_and_req_block([tx])

        self._write_precommit_state(prev_block)

        self.assertEqual(tx_results[0].status, int(True))
        score_addr1 = tx_results[0].score_address

        tx = self._make_score_call_tx(self._addr_array[0], score_addr1, 'test_str', {"bit": "0x000000000000"})

        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))
        base = tx_results[0].step_used

        tx = self._make_score_call_tx(self._addr_array[0], score_addr1, 'test_str', {"bit": "0x100000000000"})
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))
        func = tx_results[0].step_used - base
        self.assertEqual(10000, func)

        tx = self._make_score_call_tx(self._addr_array[0], score_addr1, 'test_str', {"bit": "0x010000000000"})
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))
        func = tx_results[0].step_used - base
        self.assertEqual(12000, func)

        tx = self._make_score_call_tx(self._addr_array[0], score_addr1, 'test_str', {"bit": "0x001000000000"})
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))
        func = tx_results[0].step_used - base
        self.assertEqual(13000, func)

        tx = self._make_score_call_tx(self._addr_array[0], score_addr1, 'test_str', {"bit": "0x000000000001"})
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))
        func = tx_results[0].step_used - base
        self.assertEqual(0, func)

        tx = self._make_score_call_tx(self._addr_array[0], score_addr1, 'test_str', {"bit": "0x000100000000"})
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))
        func = tx_results[0].step_used - base
        self.assertEqual(150000, func)

        tx = self._make_score_call_tx(self._addr_array[0], score_addr1, 'test_str', {"bit": "0x000010000000"})
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))
        func = tx_results[0].step_used - base
        self.assertEqual(150000, func)

        tx = self._make_score_call_tx(self._addr_array[0], score_addr1, 'test_str', {"bit": "0x000001000000"})
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))
        func = tx_results[0].step_used - base
        self.assertEqual(15000, func)

        tx = self._make_score_call_tx(self._addr_array[0], score_addr1, 'test_str', {"bit": "0x000000100000"})
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))
        func = tx_results[0].step_used - base
        self.assertEqual(51000, func)

        tx = self._make_score_call_tx(self._addr_array[0], score_addr1, 'test_str', {"bit": "0x000000010000"})
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))
        func = tx_results[0].step_used - base
        self.assertEqual(52000, func)

        # Fail
        tx = self._make_score_call_tx(self._addr_array[0], score_addr1, 'test_str', {"bit": "0x000000001000"})
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(False))
        func = tx_results[0].step_used - base
        self.assertEqual(40000, func)

        tx = self._make_score_call_tx(self._addr_array[0], score_addr1, 'test_str', {"bit": "0x000000000100"})
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))
        func = tx_results[0].step_used - base
        self.assertEqual(700000, func)

        tx = self._make_score_call_tx(self._addr_array[0], score_addr1, 'test_str', {"bit": "0x000000000010"})
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))
        func = tx_results[0].step_used - base
        self.assertEqual(700000, func)

    def test_check_charge_step2(self):
        self._update_governance()
        self._set_revision(3)

        tx = self._make_score_call_tx(self._admin, GOVERNANCE_SCORE_ADDRESS,
                                      'setStepCost',
                                      {"stepType": "apiCall", "cost": "0x2710"})

        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))

        tx = self._make_deploy_tx("test_scores",
                                  "check_charge_step",
                                  self._addr_array[0],
                                  ZERO_SCORE_ADDRESS)

        prev_block, tx_results = self._make_and_req_block([tx])

        self._write_precommit_state(prev_block)

        self.assertEqual(tx_results[0].status, int(True))
        score_addr1 = tx_results[0].score_address

        tx = self._make_score_call_tx(self._addr_array[0], score_addr1, 'test_str', {"bit": "0x000000000000"})

        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))
        base = tx_results[0].step_used

        # except Fail
        tx = self._make_score_call_tx(self._addr_array[0], score_addr1, 'test_str', {"bit": "0x111111110111"})
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))
        func = tx_results[0].step_used - base
        self.assertEqual(1853000, func)
