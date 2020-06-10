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
from unittest.mock import patch

from iconservice import SYSTEM_SCORE_ADDRESS
from iconservice.icon_constant import Revision, ICX_IN_LOOP
from tests.integrate_test.iiss.test_iiss_base import TestIISSBase

if TYPE_CHECKING:
    from iconservice.iconscore.icon_score_result import TransactionResult


class TestIISSStake(TestIISSBase):
    def test_full_stake(self):
        self.update_governance()

        # set Revision REV_IISS
        self.set_revision(Revision.IISS.value)

        # transfer 100 icx to self.addr_array[0]
        balance: int = 100 * ICX_IN_LOOP
        self.distribute_icx(accounts=self._accounts[:1],
                            init_balance=balance)

        # estimate
        tx: dict = self.create_set_stake_tx(self._accounts[0], balance)
        estimate_step: int = self.estimate_step(tx)

        # set full stake
        step_price: int = self.get_step_price()
        estimate_fee: int = step_price * estimate_step

        # set full stake
        stake: int = balance
        tx_results: List['TransactionResult'] = self.set_stake(from_=self._accounts[0],
                                                               value=stake,
                                                               expected_status=False)
        balance -= tx_results[0].step_used * tx_results[0].step_price

        # set full stake - estimated_fee
        stake: int = balance - estimate_fee
        tx_results: List['TransactionResult'] = self.set_stake(from_=self._accounts[0],
                                                               value=stake)
        fee = tx_results[0].step_used * tx_results[0].step_price
        expected_balance: int = balance - stake - fee
        response: int = self.get_balance(self._accounts[0])
        self.assertEqual(expected_balance, response)

    def test_iiss_stake(self):
        self.update_governance()

        # set Revision REV_IISS
        self.set_revision(Revision.IISS.value)

        # gain 1000 icx
        balance: int = 1000 * ICX_IN_LOOP
        self.distribute_icx(accounts=self._accounts[:1],
                            init_balance=balance)

        # set stake 50 icx
        stake: int = 50 * ICX_IN_LOOP
        unstake: int = 0
        total_stake = stake + unstake
        tx_results: List['TransactionResult'] = self.set_stake(from_=self._accounts[0],
                                                               value=stake)
        balance -= tx_results[0].step_used * tx_results[0].step_price

        # get stake
        actual_response: dict = self.get_stake(self._accounts[0])
        expected_response = {
            "stake": stake
        }
        self.assertEqual(expected_response, actual_response)

        # get balance
        remain_balance: int = balance - total_stake
        actual_balance: int = self.get_balance(self._accounts[0])
        self.assertEqual(remain_balance, actual_balance)

        # set stake 100 icx
        stake: int = 100 * ICX_IN_LOOP
        total_stake = stake + unstake
        tx_results: List['TransactionResult'] = self.set_stake(from_=self._accounts[0],
                                                               value=stake)
        balance -= tx_results[0].step_used * tx_results[0].step_price

        # get stake
        actual_response: dict = self.get_stake(self._accounts[0])
        expected_response = {
            "stake": stake,
        }
        self.assertEqual(expected_response, actual_response)

        # get balance
        remain_balance: int = balance - total_stake
        actual_balance: int = self.get_balance(self._accounts[0])
        self.assertEqual(remain_balance, actual_balance)

        # set stake 50 icx again
        stake: int = 50 * ICX_IN_LOOP
        unstake: int = 50 * ICX_IN_LOOP
        total_stake = stake + unstake
        tx_results: List['TransactionResult'] = self.set_stake(from_=self._accounts[0],
                                                               value=stake)
        balance -= tx_results[0].step_used * tx_results[0].step_price

        # get stake
        actual_response: dict = self.get_stake(self._accounts[0])
        estimate_unstake_lock_period_response: dict = self.estimate_unstake_lock_period()
        expected_response = {
            "stake": stake,
            "unstake": unstake
        }
        self.assertEqual(expected_response['stake'], actual_response['stake'])
        self.assertEqual(expected_response['unstake'], actual_response["unstakeList"][0]['unstake'])
        self.assertIn('unstakeBlockHeight', actual_response["unstakeList"][0])
        self.assertEqual(estimate_unstake_lock_period_response["unstakeLockPeriod"],
                         actual_response["unstakeList"][0]["remainingBlocks"])

        # get balance
        remain_balance: int = balance - total_stake
        actual_balance: int = self.get_balance(self._accounts[0])
        self.assertEqual(remain_balance, actual_balance)

        # set stake 100 icx again
        stake: int = 100 * ICX_IN_LOOP
        unstake: int = 0 * ICX_IN_LOOP
        total_stake = stake + unstake
        tx_results: List['TransactionResult'] = self.set_stake(from_=self._accounts[0],
                                                               value=stake)
        balance -= tx_results[0].step_used * tx_results[0].step_price

        # get stake
        actual_response: dict = self.get_stake(self._accounts[0])
        expected_response = {
            "stake": stake
        }
        self.assertEqual(expected_response, actual_response)

        # get balance
        remain_balance: int = balance - total_stake
        actual_balance: int = self.get_balance(self._accounts[0])
        self.assertEqual(remain_balance, actual_balance)

        # set stake 50 icx again
        stake: int = 50 * ICX_IN_LOOP
        unstake: int = 50 * ICX_IN_LOOP
        total_stake = stake + unstake
        tx_results: List['TransactionResult'] = self.set_stake(from_=self._accounts[0],
                                                               value=stake)
        balance -= tx_results[0].step_used * tx_results[0].step_price

        # get stake
        actual_response: dict = self.get_stake(self._accounts[0])
        estimate_unstake_lock_period_response: dict = self.estimate_unstake_lock_period()
        expected_response = {
            "stake": stake,
            "unstake": unstake
        }
        self.assertEqual(expected_response['stake'], actual_response['stake'])
        self.assertEqual(expected_response['unstake'], actual_response["unstakeList"][0]['unstake'])
        self.assertIn('unstakeBlockHeight', actual_response["unstakeList"][0])
        self.assertEqual(estimate_unstake_lock_period_response["unstakeLockPeriod"],
                         actual_response["unstakeList"][0]["remainingBlocks"])

        # get balance
        remain_balance: int = balance - total_stake
        actual_balance: int = self.get_balance(self._accounts[0])
        self.assertEqual(remain_balance, actual_balance)

        # set stake 150 icx
        stake: int = 150 * ICX_IN_LOOP
        unstake: int = 0 * ICX_IN_LOOP
        total_stake = stake + unstake
        tx_results: List['TransactionResult'] = self.set_stake(from_=self._accounts[0],
                                                               value=stake)
        balance -= tx_results[0].step_used * tx_results[0].step_price

        # get stake
        actual_response: dict = self.get_stake(self._accounts[0])
        expected_response = {
            "stake": stake
        }
        self.assertEqual(expected_response, actual_response)

        # get balance
        remain_balance: int = balance - total_stake
        actual_balance: int = self.get_balance(self._accounts[0])
        self.assertEqual(remain_balance, actual_balance)

        # set stake 50 icx
        stake: int = 50 * ICX_IN_LOOP
        unstake: int = 100 * ICX_IN_LOOP
        total_stake = stake + unstake
        tx_results: List['TransactionResult'] = self.set_stake(from_=self._accounts[0],
                                                               value=stake)
        balance -= tx_results[0].step_used * tx_results[0].step_price

        # get stake
        actual_response: dict = self.get_stake(self._accounts[0])
        estimate_unstake_lock_period_response: dict = self.estimate_unstake_lock_period()
        expected_response = {
            "stake": stake,
            "unstake": unstake
        }
        self.assertEqual(expected_response['stake'], actual_response['stake'])
        self.assertEqual(expected_response['unstake'], actual_response["unstakeList"][0]['unstake'])
        self.assertIn('unstakeBlockHeight', actual_response["unstakeList"][0])
        self.assertEqual(estimate_unstake_lock_period_response["unstakeLockPeriod"],
                         actual_response["unstakeList"][0]["remainingBlocks"])

        # get balance
        remain_balance: int = balance - total_stake
        actual_balance: int = self.get_balance(self._accounts[0])
        self.assertEqual(remain_balance, actual_balance)

        # set stake 0 icx
        stake: int = 0 * ICX_IN_LOOP
        unstake: int = 150 * ICX_IN_LOOP
        total_stake = stake + unstake
        tx_results: List['TransactionResult'] = self.set_stake(from_=self._accounts[0],
                                                               value=stake)
        balance -= tx_results[0].step_used * tx_results[0].step_price

        # get stake
        actual_response: dict = self.get_stake(self._accounts[0])
        expected_response = {
            "stake": stake,
            "unstake": unstake,
        }
        self.assertEqual(expected_response['stake'], actual_response['stake'])
        self.assertEqual(expected_response['unstake'], actual_response["unstakeList"][0]['unstake'])
        self.assertIn('unstakeBlockHeight', actual_response["unstakeList"][0])

        # get balance
        remain_balance: int = balance - total_stake
        actual_balance: int = self.get_balance(self._accounts[0])
        self.assertEqual(remain_balance, actual_balance)

        expired_block_height: int = actual_response["unstakeList"][0]['unstakeBlockHeight']
        self.make_blocks(expired_block_height + 1)

        # after unstake_lock_period
        remain_balance: int = balance
        actual_balance: int = self.get_balance(self._accounts[0])
        self.assertEqual(remain_balance, actual_balance)

        # update icx balance
        # estimate
        tx: dict = self.create_transfer_icx_tx(from_=self._accounts[0],
                                               to_=self._admin,
                                               value=0)
        estimate_step: int = self.estimate_step(tx)

        # set full stake
        step_price: int = self.get_step_price()
        estimate_fee: int = step_price * estimate_step

        tx = self.create_transfer_icx_tx(self._accounts[0],
                                         self._admin,
                                         balance - estimate_fee,
                                         step_limit=estimate_step)
        self.process_confirm_block_tx([tx])

        # get balance
        actual_response: dict = self.get_stake(self._accounts[0])
        expected_response = {
            "stake": 0
        }
        self.assertEqual(expected_response, actual_response)

    def test_unstake(self):
        self.update_governance()

        # set Revision REV_IISS
        self.set_revision(Revision.IISS.value)

        # gain 10 icx
        balance: int = 10 * ICX_IN_LOOP
        self.distribute_icx(accounts=self._accounts[:1],
                            init_balance=balance)

        # set stake
        stake: int = 8 * ICX_IN_LOOP
        tx_results: List['TransactionResult'] = self.set_stake(from_=self._accounts[0],
                                                               value=stake)
        fee = tx_results[0].step_used * tx_results[0].step_price
        expected_balance: int = balance - stake - fee
        response: int = self.get_balance(self._accounts[0])
        self.assertEqual(expected_balance, response)

        # test scenario 1
        total_stake: int = 8
        for i in range(0, total_stake // 2):
            # stake reset
            self.set_stake(from_=self._accounts[0],
                           value=total_stake * ICX_IN_LOOP)

            # delegation
            delegation_amount: int = (total_stake - i) * ICX_IN_LOOP
            delegations: list = [(self._accounts[0], delegation_amount)]
            self.set_delegation(from_=self._accounts[0],
                                origin_delegations=delegations)

            # stake
            self.set_stake(from_=self._accounts[0],
                           value=i * ICX_IN_LOOP,
                           expected_status=False)

            response: dict = self.get_delegation(self._accounts[0])
            voting_power: int = response['votingPower']
            self.assertFalse(voting_power < 0)

        # test scenario 2
        for i in range(total_stake // 2 + 1, total_stake + 1):
            # stake reset
            self.set_stake(from_=self._accounts[0],
                           value=total_stake * ICX_IN_LOOP)

            # delegation
            delegation_amount: int = (total_stake - i) * ICX_IN_LOOP
            delegations: list = [(self._accounts[0], delegation_amount)]
            self.set_delegation(from_=self._accounts[0],
                                origin_delegations=delegations)

            # stake
            self.set_stake(from_=self._accounts[0],
                           value=i * ICX_IN_LOOP)

            response: dict = self.get_delegation(self._accounts[0])
            voting_power: int = response['votingPower']
            self.assertFalse(voting_power < 0)

        # test scenario 3
        # stake reset
        self.set_stake(from_=self._accounts[0],
                       value=total_stake * ICX_IN_LOOP)

        # delegation
        delegation_amount: int = total_stake * ICX_IN_LOOP - 1
        delegations: list = [(self._accounts[0], delegation_amount)]
        self.set_delegation(from_=self._accounts[0],
                            origin_delegations=delegations)

        # unstake 1 loop
        self.set_stake(from_=self._accounts[0],
                       value=total_stake * ICX_IN_LOOP - 1)

        response: dict = self.get_delegation(self._accounts[0])
        voting_power: int = response['votingPower']
        self.assertFalse(voting_power < 0)

        # Fail
        # unstake 2 loop
        self.set_stake(from_=self._accounts[0],
                       value=total_stake * ICX_IN_LOOP - 2,
                       expected_status=False)

        response: dict = self.get_delegation(self._accounts[0])
        voting_power: int = response['votingPower']
        self.assertFalse(voting_power < 0)

    @patch("iconservice.icx.stake_part.UNSTAKE_SLOT_MAX", 10)
    def test_multiple_unstake(self):
        # in integrate tests unstaking period is about 20 so that patch UNSTAKE_SLOT_MAX to 10
        unstake_slot_max = 10
        self.update_governance()

        # set Revision REV_MULTIPLE_UNSTAKE
        self.set_revision(Revision.MULTIPLE_UNSTAKE.value)

        # gain 1000 icx
        balance: int = unstake_slot_max * 2 * ICX_IN_LOOP
        self.distribute_icx(accounts=self._accounts[:1], init_balance=balance)

        # set stake
        stake: int = unstake_slot_max * ICX_IN_LOOP
        tx_results: List['TransactionResult'] = self.set_stake(from_=self._accounts[0],
                                                               value=stake)
        fee = tx_results[0].step_used * tx_results[0].step_price
        expected_balance: int = balance - stake - fee
        response: int = self.get_balance(self._accounts[0])
        self.assertEqual(expected_balance, response)
        balance = expected_balance

        # unstake 10
        unstake_list = []
        unstake = stake // unstake_slot_max // 2
        for i in range(unstake_slot_max):
            total_unstake = unstake * (i + 1)
            tx_results: List["TransactionResult"] = self.set_stake(from_=self._accounts[0], value=stake-total_unstake)
            fee = tx_results[0].step_used * tx_results[0].step_price
            expected_balance: int = balance - fee
            response: int = self.get_balance(self._accounts[0])
            self.assertEqual(expected_balance, response)
            balance = expected_balance
            unstake_list.append(unstake)

        response: dict = self.get_stake(self._accounts[0])
        for i in range(unstake_slot_max):
            unstake_response = response["unstakeList"][i]["unstake"]
            self.assertEqual(unstake_list[i], unstake_response)

        # increase unstake in last slot
        total_unstake = sum(unstake_list) + ICX_IN_LOOP
        tx_results: List["TransactionResult"] = self.set_stake(from_=self._accounts[0], value=stake-total_unstake)
        fee = tx_results[0].step_used * tx_results[0].step_price
        expected_balance: int = balance - fee
        response: int = self.get_balance(self._accounts[0])
        self.assertEqual(expected_balance, response)
        balance = expected_balance
        response: dict = self.get_stake(self._accounts[0])
        last_slot_block_height = response["unstakeList"][unstake_slot_max-1]["unstakeBlockHeight"]
        original_unstake = unstake_list.pop()
        unstake_list.append(original_unstake + ICX_IN_LOOP)
        last_slot_block_height2 = response["unstakeList"][unstake_slot_max-1]["unstakeBlockHeight"]
        for i in range(len(unstake_list)):
            self.assertEqual(unstake_list[i], response["unstakeList"][i]["unstake"])
        # unstakeBlockHeight in last slot will be updated
        self.assertGreaterEqual(last_slot_block_height2, last_slot_block_height)

        # decrease slots
        total_unstake = sum(unstake_list[:3])
        tx_results: List["TransactionResult"] = self.set_stake(from_=self._accounts[0], value=stake-total_unstake)
        fee = tx_results[0].step_used * tx_results[0].step_price
        expected_balance: int = balance - fee
        response: int = self.get_balance(self._accounts[0])
        self.assertEqual(expected_balance, response)
        response: dict = self.get_stake(self._accounts[0])
        expected_unstakes = [unstake, unstake, unstake]
        for i in range(len(expected_unstakes)):
            self.assertEqual(expected_unstakes[i], response["unstakeList"][i]["unstake"])

    def test_migrate_unstake_data(self):
        self.update_governance()

        # set Revision REV_IISS
        self.set_revision(Revision.IISS.value)

        # gain 1000 icx
        balance: int = 1000 * ICX_IN_LOOP
        self.distribute_icx(accounts=self._accounts[:1], init_balance=balance)

        # set stake
        stake: int = 100 * ICX_IN_LOOP
        tx_results: List['TransactionResult'] = self.set_stake(from_=self._accounts[0],
                                                               value=stake)
        fee = tx_results[0].step_used * tx_results[0].step_price
        expected_balance: int = balance - stake - fee
        response: int = self.get_balance(self._accounts[0])
        self.assertEqual(expected_balance, response)
        balance = expected_balance

        # unstake 10
        unstake = 10 * ICX_IN_LOOP
        total_unstake = unstake
        tx_results: List["TransactionResult"] = self.set_stake(from_=self._accounts[0], value=stake-total_unstake)
        fee2 = tx_results[0].step_used * tx_results[0].step_price
        expected_balance: int = balance - fee2
        response: int = self.get_balance(self._accounts[0])
        self.assertEqual(expected_balance, response)
        balance = expected_balance
        response: dict = self.get_stake(self._accounts[0])
        unstake_info = response["unstakeList"][0]
        unstake_block_height = unstake_info["unstakeBlockHeight"]

        # unstake 10 again and unstakeBlockHeight will be changed in rev IISS
        unstake = 10 * ICX_IN_LOOP
        total_unstake = unstake
        tx_results: List["TransactionResult"] = self.set_stake(from_=self._accounts[0], value=stake-total_unstake)
        fee2 = tx_results[0].step_used * tx_results[0].step_price
        expected_balance: int = balance - fee2
        response: int = self.get_balance(self._accounts[0])
        self.assertEqual(expected_balance, response)
        balance = expected_balance
        response: dict = self.get_stake(self._accounts[0])
        unstake_info = response["unstakeList"][0]
        unstake_block_height2 = unstake_info["unstakeBlockHeight"]
        self.assertGreaterEqual(unstake_block_height2, unstake_block_height)

        # set Revision REV_MULTIPLE_UNSTAKE
        self.set_revision(Revision.MULTIPLE_UNSTAKE.value)

        # unstake 10 again and unstakeBlockHeight will not be changed
        unstake = 10 * ICX_IN_LOOP
        total_unstake = unstake
        tx_results: List["TransactionResult"] = self.set_stake(from_=self._accounts[0], value=stake-total_unstake)
        fee2 = tx_results[0].step_used * tx_results[0].step_price
        expected_balance: int = balance - fee2
        response: int = self.get_balance(self._accounts[0])
        self.assertEqual(expected_balance, response)
        response: dict = self.get_stake(self._accounts[0])
        unstake_info = response["unstakeList"][0]
        unstake_block_height3 = unstake_info["unstakeBlockHeight"]
        self.assertEqual(unstake_block_height2, unstake_block_height3)

    def test_update_unstake_block_height(self):
        self.update_governance()

        # set Revision REV_IISS
        self.set_revision(Revision.IISS.value)

        # gain 1000 icx
        balance: int = 1000 * ICX_IN_LOOP
        self.distribute_icx(accounts=self._accounts[:1], init_balance=balance)

        # set stake
        stake: int = 100 * ICX_IN_LOOP
        tx_results: List['TransactionResult'] = self.set_stake(from_=self._accounts[0],
                                                               value=stake)
        fee = tx_results[0].step_used * tx_results[0].step_price
        expected_balance: int = balance - stake - fee
        response: int = self.get_balance(self._accounts[0])
        self.assertEqual(expected_balance, response)
        balance = expected_balance

        # unstake 10
        unstake = 10 * ICX_IN_LOOP
        total_unstake = unstake
        tx_results: List["TransactionResult"] = self.set_stake(from_=self._accounts[0], value=stake-total_unstake)
        fee2 = tx_results[0].step_used * tx_results[0].step_price
        expected_balance: int = balance - fee2
        response: int = self.get_balance(self._accounts[0])
        self.assertEqual(expected_balance, response)
        balance = expected_balance
        response: dict = self.get_stake(self._accounts[0])
        self.assertEqual(response["unstakeList"][0]["unstake"], unstake)

        # set stake 120 icx and unstake info will be removed
        new_stake = 120 * ICX_IN_LOOP
        tx_results: List["TransactionResult"] = self.set_stake(from_=self._accounts[0], value=new_stake)
        fee2 = tx_results[0].step_used * tx_results[0].step_price
        expected_balance: int = balance - fee2 - (new_stake - stake)
        response: int = self.get_balance(self._accounts[0])
        self.assertEqual(expected_balance, response)
        balance = expected_balance
        response: dict = self.get_stake(self._accounts[0])
        self.assertNotIn("unstakeList", response)

        # set Revision REV_MULTIPLE_UNSTAKE
        self.set_revision(Revision.MULTIPLE_UNSTAKE.value)

        # unstake 10
        unstake = 10 * ICX_IN_LOOP
        tx_results: List["TransactionResult"] = self.set_stake(from_=self._accounts[0], value=new_stake-unstake)
        fee2 = tx_results[0].step_used * tx_results[0].step_price
        expected_balance: int = balance - fee2
        response: int = self.get_balance(self._accounts[0])
        self.assertEqual(expected_balance, response)
        balance = expected_balance
        response: dict = self.get_stake(self._accounts[0])
        self.assertEqual(response["unstakeList"][0]["unstake"], unstake)

        # set stake 140 icx and unstake info will be removed
        new_stake2 = 140 * ICX_IN_LOOP
        tx_results: List["TransactionResult"] = self.set_stake(from_=self._accounts[0], value=new_stake2)
        fee2 = tx_results[0].step_used * tx_results[0].step_price
        expected_balance: int = balance - fee2 - (new_stake2 - new_stake)
        response: int = self.get_balance(self._accounts[0])
        self.assertEqual(expected_balance, response)
        response: dict = self.get_stake(self._accounts[0])
        self.assertNotIn("unstakeList", response)

    def test_stake_with_value_should_raise_exception(self):
        self.update_governance()
        self.set_revision(Revision.IISS.value)
        balance: int = 10 * ICX_IN_LOOP
        self.distribute_icx(accounts=self._accounts[:1],
                            init_balance=balance)

        tx: dict = self.create_score_call_tx(from_=self._accounts[0],
                                             to_=SYSTEM_SCORE_ADDRESS,
                                             func_name='setStake',
                                             params={"value": hex(8 * ICX_IN_LOOP)},
                                             value=5)

        return self.process_confirm_block_tx([tx], expected_status=False)
