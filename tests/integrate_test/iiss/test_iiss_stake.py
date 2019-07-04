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

from typing import TYPE_CHECKING

from iconservice.base.address import ZERO_SCORE_ADDRESS, GOVERNANCE_SCORE_ADDRESS
from iconservice.icon_config import default_icon_config
from iconservice.icon_constant import ConfigKey, REV_IISS
from tests.integrate_test.test_integrate_base import TestIntegrateBase

if TYPE_CHECKING:
    from iconservice import Address


class TestIntegrateIISSStake(TestIntegrateBase):

    def _make_init_config(self) -> dict:
        return {ConfigKey.IISS_UNSTAKE_LOCK_PERIOD: 10}

    def _update_governance(self):
        tx = self._make_deploy_tx("sample_builtin",
                                  "latest_version/governance",
                                  self._admin,
                                  GOVERNANCE_SCORE_ADDRESS)
        prev_block, tx_results = self._make_and_req_block([tx])
        self.assertEqual(int(True), tx_results[0].status)
        self._write_precommit_state(prev_block)

    def _set_revision(self, revision: int):
        tx = self._make_score_call_tx(self._admin,
                                      GOVERNANCE_SCORE_ADDRESS,
                                      'setRevision',
                                      {"code": hex(revision),
                                       "name": f"1.1.{revision}"})
        prev_block, tx_results = self._make_and_req_block([tx])
        self.assertEqual(int(True), tx_results[0].status)
        self._write_precommit_state(prev_block)

    def _stake(self, address: 'Address', value: int):
        tx = self._make_score_call_tx(address, ZERO_SCORE_ADDRESS,
                                      'setStake',
                                      {"value": hex(value)})
        prev_block, tx_results = self._make_and_req_block([tx])
        self.assertEqual(int(True), tx_results[0].status)
        self._write_precommit_state(prev_block)

    def _get_stake(self, address: 'Address') -> dict:
        query_request = {
            "version": self._version,
            "from": self._addr_array[0],
            "to": ZERO_SCORE_ADDRESS,
            "dataType": "call",
            "data": {
                "method": "getStake",
                "params": {
                    "address": str(address)
                }
            }
        }
        return self._query(query_request)

    def test_iiss_stake(self):
        self._update_governance()
        self._set_revision(REV_IISS)

        # gain 1000 icx
        balance: int = 1000 * 10 ** 18
        tx = self._make_icx_send_tx(self._genesis, self._addr_array[0], balance)
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)

        # set stake 50 icx
        stake: int = 50 * 10 ** 18
        unstake: int = 0
        total_stake = stake + unstake

        self._stake(self._addr_array[0], stake)
        actual_response: dict = self._get_stake(self._addr_array[0])
        expected_response = {
            "stake": stake
        }
        self.assertEqual(expected_response, actual_response)
        remain_balance: int = balance - total_stake
        actual_balance = self._query({"address": self._addr_array[0]}, 'icx_getBalance')
        self.assertEqual(remain_balance, actual_balance)

        # set stake 100 icx
        stake: int = 100 * 10 ** 18
        total_stake = stake + unstake

        self._stake(self._addr_array[0], stake)
        actual_response: dict = self._get_stake(self._addr_array[0])
        expected_response = {
            "stake": stake,
        }
        self.assertEqual(expected_response, actual_response)
        remain_balance: int = balance - total_stake
        actual_balance = self._query({"address": self._addr_array[0]}, 'icx_getBalance')
        self.assertEqual(remain_balance, actual_balance)

        # set stake 50 icx again
        stake: int = 50 * 10 ** 18
        unstake: int = 50 * 10 ** 18
        total_stake = stake + unstake

        self._stake(self._addr_array[0], stake)
        actual_response: dict = self._get_stake(self._addr_array[0])
        expected_response = {
            "stake": stake,
            "unstake": unstake
        }
        self.assertEqual(expected_response['stake'], actual_response['stake'])
        self.assertEqual(expected_response['unstake'], actual_response['unstake'])
        self.assertIn('unstakeBlockHeight', actual_response)
        remain_balance: int = balance - total_stake
        actual_balance = self._query({"address": self._addr_array[0]}, 'icx_getBalance')
        self.assertEqual(remain_balance, actual_balance)

        # set stake 100 icx again
        stake: int = 100 * 10 ** 18
        unstake: int = 0 * 10 ** 18
        total_stake = stake + unstake

        self._stake(self._addr_array[0], stake)
        actual_response: dict = self._get_stake(self._addr_array[0])
        expected_response = {
            "stake": stake
        }
        self.assertEqual(expected_response, actual_response)
        remain_balance: int = balance - total_stake
        actual_balance = self._query({"address": self._addr_array[0]}, 'icx_getBalance')
        self.assertEqual(remain_balance, actual_balance)

        # set stake 50 icx again
        stake: int = 50 * 10 ** 18
        unstake: int = 50 * 10 ** 18
        total_stake = stake + unstake

        self._stake(self._addr_array[0], stake)
        actual_response: dict = self._get_stake(self._addr_array[0])
        expected_response = {
            "stake": stake,
            "unstake": unstake
        }
        self.assertEqual(expected_response['stake'], actual_response['stake'])
        self.assertEqual(expected_response['unstake'], actual_response['unstake'])
        self.assertIn('unstakeBlockHeight', actual_response)
        remain_balance: int = balance - total_stake
        actual_balance = self._query({"address": self._addr_array[0]}, 'icx_getBalance')
        self.assertEqual(remain_balance, actual_balance)

        # set stake 150 icx
        stake: int = 150 * 10 ** 18
        unstake: int = 0 * 10 ** 18
        total_stake = stake + unstake

        self._stake(self._addr_array[0], stake)
        actual_response: dict = self._get_stake(self._addr_array[0])
        expected_response = {
            "stake": stake
        }
        self.assertEqual(expected_response, actual_response)
        remain_balance: int = balance - total_stake
        actual_balance = self._query({"address": self._addr_array[0]}, 'icx_getBalance')
        self.assertEqual(remain_balance, actual_balance)

        # set stake 50 icx
        stake: int = 50 * 10 ** 18
        unstake: int = 100 * 10 ** 18
        total_stake = stake + unstake

        self._stake(self._addr_array[0], stake)
        actual_response: dict = self._get_stake(self._addr_array[0])
        expected_response = {
            "stake": stake,
            "unstake": unstake
        }
        self.assertEqual(expected_response['stake'], actual_response['stake'])
        self.assertEqual(expected_response['unstake'], actual_response['unstake'])
        self.assertIn('unstakeBlockHeight', actual_response)
        remain_balance: int = balance - total_stake
        actual_balance = self._query({"address": self._addr_array[0]}, 'icx_getBalance')
        self.assertEqual(remain_balance, actual_balance)

        # set stake 0 icx
        stake: int = 0 * 10 ** 18
        unstake: int = 150 * 10 ** 18
        total_stake = stake + unstake
        self._stake(self._addr_array[0], stake)
        actual_response: dict = self._get_stake(self._addr_array[0])
        expected_response = {
            "stake": stake,
            "unstake": unstake,
        }
        self.assertEqual(expected_response['stake'], actual_response['stake'])
        self.assertEqual(expected_response['unstake'], actual_response['unstake'])
        self.assertIn('unstakeBlockHeight', actual_response)

        remain_balance: int = balance - total_stake
        actual_balance = self._query({"address": self._addr_array[0]}, 'icx_getBalance')
        self.assertEqual(remain_balance, actual_balance)

        expired_block_height: int = actual_response['unstakeBlockHeight'] - self._block_height
        for _ in range(expired_block_height + 1):
            tx = self._make_icx_send_tx(self._genesis, self._addr_array[0], 0)
            prev_block, tx_results = self._make_and_req_block([tx])
            self._write_precommit_state(prev_block)

        # after unstake_lock_period
        remain_balance: int = balance
        actual_balance = self._query({"address": self._addr_array[0]}, 'icx_getBalance')
        self.assertEqual(remain_balance, actual_balance)

        # update icx balance
        tx = self._make_icx_send_tx(self._addr_array[0], self._genesis, balance)
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)

        actual_response: dict = self._get_stake(self._addr_array[0])
        expected_response = {
            "stake": 0
        }
        self.assertEqual(expected_response, actual_response)
