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
from unittest.mock import Mock

from iconservice.base.address import SYSTEM_SCORE_ADDRESS
from iconservice.icon_constant import Revision, ICX_IN_LOOP
from iconservice.icx.storage import AccountPartFlag
from iconservice.iiss import IISSMethod
from iconservice.iiss.reward_calc.ipc.reward_calc_proxy import RewardCalcProxy
from tests.integrate_test.iiss.test_iiss_base import TestIISSBase


class TestIISS(TestIISSBase):
    def test_debug_get_account_coin(self):
        self.update_governance()

        # set Revision REV_IISS
        self.set_revision(Revision.IISS.value)

        expected_ret = {
            'coin': {
                'type': 0,
                'typeStr': 'GENERAL',
                'flag': 0,
                'flagStr': 'CoinPartFlag.NONE',
                'balance': 0
            }
        }
        ret: dict = self.debug_get_account(
            self._accounts[0],
            account_filter=AccountPartFlag.COIN.value
        )
        self.assertEqual(expected_ret, ret)

    def test_debug_get_account_stake(self):
        self.update_governance()

        # set Revision REV_IISS
        self.set_revision(Revision.IISS.value)

        expected_ret = {
            'stake': {
                'stake': 0,
                'unstake': 0,
                'unstakeBlockHeight': 0,
                'unstakesInfo': []
            }
        }
        ret: dict = self.debug_get_account(
            self._accounts[0],
            account_filter=AccountPartFlag.STAKE.value
        )
        self.assertEqual(expected_ret, ret)

    def test_debug_get_account_delegation(self):
        self.update_governance()

        # set Revision REV_IISS
        self.set_revision(Revision.IISS.value)

        expected_ret = {
            'delegation': {
                'delegations': [],
                'totalDelegated': 0
            }
        }
        ret: dict = self.debug_get_account(
            self._accounts[0],
            account_filter=AccountPartFlag.DELEGATION.value
        )
        self.assertEqual(expected_ret, ret)

    def test_debug_get_account_all(self):
        self.update_governance()

        # set Revision REV_IISS
        self.set_revision(Revision.IISS.value)

        expected_ret = {
            'coin': {
                'type': 0,
                'typeStr': 'GENERAL',
                'flag': 0,
                'flagStr': 'CoinPartFlag.NONE',
                'balance': 0
            },
            'stake': {
                'stake': 0,
                'unstake': 0,
                'unstakeBlockHeight': 0,
                'unstakesInfo': []
            },
            'delegation': {
                'delegations': [],
                'totalDelegated': 0
            }
        }
        all_filter: AccountPartFlag = \
            AccountPartFlag.COIN | \
            AccountPartFlag.STAKE | \
            AccountPartFlag.DELEGATION
        ret: dict = self.debug_get_account(
            self._accounts[0],
            account_filter=all_filter.value
        )
        self.assertEqual(expected_ret, ret)
