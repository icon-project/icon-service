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

from iconservice.icon_constant import REV_IISS, ICX_IN_LOOP
from tests.iiss.test_iiss_engine import EXPECTED_LOCK_PERIOD_PRE_STAKE_PERCENT
from tests.integrate_test.iiss.test_iiss_base import TestIISSBase
from tests.integrate_test.test_integrate_base import TOTAL_SUPPLY


class TestIISSUnStakeLockPeriod(TestIISSBase):

    def test_unstake_lock_period(self):
        self.update_governance()

        # set Revision REV_IISS
        tx: dict = self.create_set_revision_tx(REV_IISS)
        prev_block, tx_results = self._make_and_req_block([tx])
        self.assertEqual(int(True), tx_results[0].status)
        self._write_precommit_state(prev_block)

        # get almost total supply (total supply - 3 ICX)
        genesis_balance: int = TOTAL_SUPPLY * ICX_IN_LOOP // 2 - (1 * ICX_IN_LOOP)
        tx = self._make_icx_send_tx(self._genesis, self._addr_array[0], genesis_balance)
        prev_block, tx_results = self._make_and_req_block([tx])
        self.assertEqual(int(True), tx_results[0].status)
        self._write_precommit_state(prev_block)

        admin_balance: int = TOTAL_SUPPLY * ICX_IN_LOOP // 2 - (2 * ICX_IN_LOOP)
        tx = self._make_icx_send_tx(self._admin, self._addr_array[0], admin_balance)
        prev_block, tx_results = self._make_and_req_block([tx])
        self.assertEqual(int(True), tx_results[0].status)
        self._write_precommit_state(prev_block)

        # set stake (from total stake percent 1% ~ 99%)
        for stake_percent in range(1, 100):
            stake: int = int(TOTAL_SUPPLY * ICX_IN_LOOP * (stake_percent / 100))
            tx: dict = self.create_set_stake_tx(self._addr_array[0], stake)
            prev_block, tx_results = self._make_and_req_block([tx])
            self.assertEqual(int(True), tx_results[0].status)
            self._write_precommit_state(prev_block)

            stake: int = 0
            tx: dict = self.create_set_stake_tx(self._addr_array[0], stake)
            prev_block, tx_results = self._make_and_req_block([tx])
            self.assertEqual(int(True), tx_results[0].status)
            self._write_precommit_state(prev_block)

            actual_response: dict = self.get_stake(self._addr_array[0])
            actual_lockup_period = actual_response['unstakeBlockHeight'] - prev_block._height
            diff = abs(actual_lockup_period - EXPECTED_LOCK_PERIOD_PRE_STAKE_PERCENT[stake_percent])
            assert diff <= 1
