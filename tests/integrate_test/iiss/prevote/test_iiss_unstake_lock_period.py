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

from iconservice.icon_constant import REV_IISS, ICX_IN_LOOP, ConfigKey, IISS_DAY_BLOCK
from tests.iiss.test_iiss_engine import EXPECTED_LOCK_PERIOD_PRE_STAKE_PERCENT
from tests.integrate_test.iiss.test_iiss_base import TestIISSBase
from tests.integrate_test.test_integrate_base import TOTAL_SUPPLY


class TestIISSUnStakeLockPeriod(TestIISSBase):
    def _make_init_config(self):
        return {
            ConfigKey.IISS_META_DATA: {
                ConfigKey.UN_STAKE_LOCK_MIN: IISS_DAY_BLOCK * 5,
                ConfigKey.UN_STAKE_LOCK_MAX: IISS_DAY_BLOCK * 20
            }
        }

    def test_unstake_lock_period(self):
        self.update_governance()

        # set Revision REV_IISS
        self.set_revision(REV_IISS)

        # get almost total supply (total supply - 3 ICX)
        genesis_balance: int = TOTAL_SUPPLY * ICX_IN_LOOP - 3 * ICX_IN_LOOP
        self.transfer_icx(from_=self._admin,
                          to_=self._accounts[0],
                          value=genesis_balance)

        # set stake (from total stake percent 1% ~ 99%)
        for stake_percent in range(1, 100):
            stake: int = int(TOTAL_SUPPLY * ICX_IN_LOOP * (stake_percent / 100))
            self.set_stake(from_=self._accounts[0],
                           value=stake)

            stake: int = 0
            self.set_stake(from_=self._accounts[0],
                           value=stake)

            actual_response: dict = self.get_stake(self._accounts[0])
            actual_lockup_period = actual_response['unstakeBlockHeight'] - self._block_height
            diff = abs(actual_lockup_period - EXPECTED_LOCK_PERIOD_PRE_STAKE_PERCENT[stake_percent])
            assert diff <= 1
