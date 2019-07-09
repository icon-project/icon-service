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

from iconservice.icon_constant import ConfigKey, REV_IISS, ICX_IN_LOOP
from tests.integrate_test.iiss.test_iiss_base import TestIISSBase


class TestIISSStake(TestIISSBase):

    def _make_init_config(self) -> dict:
        config: dict = super()._make_init_config()
        config[ConfigKey.IISS_UNSTAKE_LOCK_PERIOD] = 10
        return config

    def test_iiss_stake(self):
        self.update_governance()

        # set Revision REV_IISS
        tx: dict = self.create_set_revision_tx(REV_IISS)
        prev_block, tx_results = self._make_and_req_block([tx])
        self.assertEqual(int(True), tx_results[0].status)
        self._write_precommit_state(prev_block)

        # gain 1000 icx
        balance: int = 1000 * ICX_IN_LOOP
        tx = self._make_icx_send_tx(self._genesis, self._addr_array[0], balance)
        prev_block, tx_results = self._make_and_req_block([tx])
        self.assertEqual(int(True), tx_results[0].status)
        self._write_precommit_state(prev_block)

        # set stake 50 icx
        stake: int = 50 * ICX_IN_LOOP
        unstake: int = 0
        total_stake = stake + unstake
        tx: dict = self.create_set_stake_tx(self._addr_array[0], stake)
        prev_block, tx_results = self._make_and_req_block([tx])
        self.assertEqual(int(True), tx_results[0].status)
        self._write_precommit_state(prev_block)

        # get stake
        actual_response: dict = self.get_stake(self._addr_array[0])
        expected_response = {
            "stake": stake
        }
        self.assertEqual(expected_response, actual_response)

        # get balance
        remain_balance: int = balance - total_stake
        actual_balance: int = self.get_balance(self._addr_array[0])
        self.assertEqual(remain_balance, actual_balance)

        # set stake 100 icx
        stake: int = 100 * ICX_IN_LOOP
        total_stake = stake + unstake
        tx: dict = self.create_set_stake_tx(self._addr_array[0], stake)
        prev_block, tx_results = self._make_and_req_block([tx])
        self.assertEqual(int(True), tx_results[0].status)
        self._write_precommit_state(prev_block)

        # get stake
        actual_response: dict = self.get_stake(self._addr_array[0])
        expected_response = {
            "stake": stake,
        }
        self.assertEqual(expected_response, actual_response)

        # get balance
        remain_balance: int = balance - total_stake
        actual_balance: int = self.get_balance(self._addr_array[0])
        self.assertEqual(remain_balance, actual_balance)

        # set stake 50 icx again
        stake: int = 50 * ICX_IN_LOOP
        unstake: int = 50 * ICX_IN_LOOP
        total_stake = stake + unstake
        tx: dict = self.create_set_stake_tx(self._addr_array[0], stake)
        prev_block, tx_results = self._make_and_req_block([tx])
        self.assertEqual(int(True), tx_results[0].status)
        self._write_precommit_state(prev_block)

        # get stake
        actual_response: dict = self.get_stake(self._addr_array[0])
        expected_response = {
            "stake": stake,
            "unstake": unstake
        }
        self.assertEqual(expected_response['stake'], actual_response['stake'])
        self.assertEqual(expected_response['unstake'], actual_response['unstake'])
        self.assertIn('unstakeBlockHeight', actual_response)

        # get balance
        remain_balance: int = balance - total_stake
        actual_balance: int = self.get_balance(self._addr_array[0])
        self.assertEqual(remain_balance, actual_balance)

        # set stake 100 icx again
        stake: int = 100 * ICX_IN_LOOP
        unstake: int = 0 * ICX_IN_LOOP
        total_stake = stake + unstake
        tx: dict = self.create_set_stake_tx(self._addr_array[0], stake)
        prev_block, tx_results = self._make_and_req_block([tx])
        self.assertEqual(int(True), tx_results[0].status)
        self._write_precommit_state(prev_block)

        # get stake
        actual_response: dict = self.get_stake(self._addr_array[0])
        expected_response = {
            "stake": stake
        }
        self.assertEqual(expected_response, actual_response)

        # get balance
        remain_balance: int = balance - total_stake
        actual_balance: int = self.get_balance(self._addr_array[0])
        self.assertEqual(remain_balance, actual_balance)

        # set stake 50 icx again
        stake: int = 50 * ICX_IN_LOOP
        unstake: int = 50 * ICX_IN_LOOP
        total_stake = stake + unstake
        tx: dict = self.create_set_stake_tx(self._addr_array[0], stake)
        prev_block, tx_results = self._make_and_req_block([tx])
        self.assertEqual(int(True), tx_results[0].status)
        self._write_precommit_state(prev_block)

        # get stake
        actual_response: dict = self.get_stake(self._addr_array[0])
        expected_response = {
            "stake": stake,
            "unstake": unstake
        }
        self.assertEqual(expected_response['stake'], actual_response['stake'])
        self.assertEqual(expected_response['unstake'], actual_response['unstake'])
        self.assertIn('unstakeBlockHeight', actual_response)

        # get balance
        remain_balance: int = balance - total_stake
        actual_balance: int = self.get_balance(self._addr_array[0])
        self.assertEqual(remain_balance, actual_balance)

        # set stake 150 icx
        stake: int = 150 * ICX_IN_LOOP
        unstake: int = 0 * ICX_IN_LOOP
        total_stake = stake + unstake
        tx: dict = self.create_set_stake_tx(self._addr_array[0], stake)
        prev_block, tx_results = self._make_and_req_block([tx])
        self.assertEqual(int(True), tx_results[0].status)
        self._write_precommit_state(prev_block)

        # get stake
        actual_response: dict = self.get_stake(self._addr_array[0])
        expected_response = {
            "stake": stake
        }
        self.assertEqual(expected_response, actual_response)

        # get balance
        remain_balance: int = balance - total_stake
        actual_balance: int = self.get_balance(self._addr_array[0])
        self.assertEqual(remain_balance, actual_balance)

        # set stake 50 icx
        stake: int = 50 * ICX_IN_LOOP
        unstake: int = 100 * ICX_IN_LOOP
        total_stake = stake + unstake
        tx: dict = self.create_set_stake_tx(self._addr_array[0], stake)
        prev_block, tx_results = self._make_and_req_block([tx])
        self.assertEqual(int(True), tx_results[0].status)
        self._write_precommit_state(prev_block)

        # get stake
        actual_response: dict = self.get_stake(self._addr_array[0])
        expected_response = {
            "stake": stake,
            "unstake": unstake
        }
        self.assertEqual(expected_response['stake'], actual_response['stake'])
        self.assertEqual(expected_response['unstake'], actual_response['unstake'])
        self.assertIn('unstakeBlockHeight', actual_response)

        # get balance
        remain_balance: int = balance - total_stake
        actual_balance: int = self.get_balance(self._addr_array[0])
        self.assertEqual(remain_balance, actual_balance)

        # set stake 0 icx
        stake: int = 0 * ICX_IN_LOOP
        unstake: int = 150 * ICX_IN_LOOP
        total_stake = stake + unstake
        tx: dict = self.create_set_stake_tx(self._addr_array[0], stake)
        prev_block, tx_results = self._make_and_req_block([tx])
        self.assertEqual(int(True), tx_results[0].status)
        self._write_precommit_state(prev_block)

        # get stake
        actual_response: dict = self.get_stake(self._addr_array[0])
        expected_response = {
            "stake": stake,
            "unstake": unstake,
        }
        self.assertEqual(expected_response['stake'], actual_response['stake'])
        self.assertEqual(expected_response['unstake'], actual_response['unstake'])
        self.assertIn('unstakeBlockHeight', actual_response)

        # get balance
        remain_balance: int = balance - total_stake
        actual_balance: int = self.get_balance(self._addr_array[0])
        self.assertEqual(remain_balance, actual_balance)

        expired_block_height: int = actual_response['unstakeBlockHeight']
        self.make_blocks(expired_block_height + 1)

        # after unstake_lock_period
        remain_balance: int = balance
        actual_balance: int = self.get_balance(self._addr_array[0])
        self.assertEqual(remain_balance, actual_balance)

        # update icx balance
        tx = self._make_icx_send_tx(self._addr_array[0], self._genesis, balance)
        prev_block, tx_results = self._make_and_req_block([tx])
        self.assertEqual(int(True), tx_results[0].status)
        self._write_precommit_state(prev_block)

        # get balance
        actual_response: dict = self.get_stake(self._addr_array[0])
        expected_response = {
            "stake": 0
        }
        self.assertEqual(expected_response, actual_response)