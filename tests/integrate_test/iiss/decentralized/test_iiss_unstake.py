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

from iconservice.icon_constant import Revision, ICX_IN_LOOP
from iconservice.icx.coin_part import CoinPart, CoinPartFlag
from iconservice.icx.stake_part import StakePart
from tests.integrate_test.iiss.test_iiss_base import TestIISSBase

if TYPE_CHECKING:
    from iconservice.iconscore.icon_score_result import TransactionResult
    from tests.integrate_test.test_integrate_base import EOAAccount


class TestIISSUnStake(TestIISSBase):
    def test_unstake_balance_rev_10(self):
        self._test_unstake_balance(
            rev=Revision.FIX_UNSTAKE_BUG.value,
            expected_expired_ustake_cnt=2,
            expected_last_balance=0
        )

    def test_unstake_balance_rev_11(self):
        self._test_unstake_balance(
            rev=Revision.FIX_BALANCE_BUG.value,
            expected_expired_ustake_cnt=3,
            expected_last_balance=1 * ICX_IN_LOOP
        )

    def _test_unstake_balance(
            self,
            rev: int,
            expected_expired_ustake_cnt: int,
            expected_last_balance: int
    ):
        self.update_governance()

        # set Revision REV_IISS
        self.set_revision(Revision.IISS.value)

        # gain 10 icx
        balance: int = 10 * ICX_IN_LOOP
        self.distribute_icx(
            accounts=self._accounts[:1],
            init_balance=balance
        )

        # set stake
        target_stake: int = 8
        stake: int = target_stake * ICX_IN_LOOP
        tx_results: List['TransactionResult'] = self.set_stake(
            from_=self._accounts[0],
            value=stake
        )
        fee = tx_results[0].step_used * tx_results[0].step_price
        expected_balance: int = balance - stake - fee
        response: int = self.get_balance(self._accounts[0])
        self.assertEqual(expected_balance, response)

        self.set_revision(Revision.MULTIPLE_UNSTAKE.value)

        for i in range(6):
            self.set_stake(
                from_=self._accounts[0],
                value=stake - (i+1) * ICX_IN_LOOP
            )

        last_balance: int = self.get_balance(self._accounts[0])

        actual_res: dict = self.get_stake(self._accounts[0])
        first_remaining_blocks: int = 14
        expected_res = {
            "stake": stake - 1 * ICX_IN_LOOP * 6,
            "unstakes": [
                {"unstake": 1 * ICX_IN_LOOP, "unstakeBlockHeight": 25, "remainingBlocks": first_remaining_blocks},
                {"unstake": 1 * ICX_IN_LOOP, "unstakeBlockHeight": 26, "remainingBlocks": first_remaining_blocks+1},
                {"unstake": 1 * ICX_IN_LOOP, "unstakeBlockHeight": 27, "remainingBlocks": first_remaining_blocks+2},
                {"unstake": 1 * ICX_IN_LOOP, "unstakeBlockHeight": 28, "remainingBlocks": first_remaining_blocks+3},
                {"unstake": 1 * ICX_IN_LOOP, "unstakeBlockHeight": 29, "remainingBlocks": first_remaining_blocks+4},
                {"unstake": 1 * ICX_IN_LOOP, "unstakeBlockHeight": 30, "remainingBlocks": first_remaining_blocks+5},
            ]
        }
        self.assertEqual(expected_res, actual_res)

        self.set_revision(rev)

        # 1st expired unstake
        self.make_empty_blocks(first_remaining_blocks)

        res: dict = self.get_stake(self._accounts[0])
        expected_res = {
            "stake": stake - 1 * ICX_IN_LOOP * 6,
            "unstakes": [
                {"unstake": 1 * ICX_IN_LOOP, "unstakeBlockHeight": 26, "remainingBlocks": 0},
                {"unstake": 1 * ICX_IN_LOOP, "unstakeBlockHeight": 27, "remainingBlocks": 1},
                {"unstake": 1 * ICX_IN_LOOP, "unstakeBlockHeight": 28, "remainingBlocks": 2},
                {"unstake": 1 * ICX_IN_LOOP, "unstakeBlockHeight": 29, "remainingBlocks": 3},
                {"unstake": 1 * ICX_IN_LOOP, "unstakeBlockHeight": 30, "remainingBlocks": 4},
            ]
        }
        self.assertEqual(res, expected_res)

        tx_results = self.transfer_icx(from_=self._accounts[0], to_=self._accounts[1], value=0)

        res: dict = self.get_stake(self._accounts[0])
        expected_res = {
            "stake": stake - 1 * ICX_IN_LOOP * 6,
            "unstakes": [
                {"unstake": 1 * ICX_IN_LOOP, "unstakeBlockHeight": 27, "remainingBlocks": 0},
                {"unstake": 1 * ICX_IN_LOOP, "unstakeBlockHeight": 28, "remainingBlocks": 1},
                {"unstake": 1 * ICX_IN_LOOP, "unstakeBlockHeight": 29, "remainingBlocks": 2},
                {"unstake": 1 * ICX_IN_LOOP, "unstakeBlockHeight": 30, "remainingBlocks": 3},
            ]
        }
        self.assertEqual(res, expected_res)

        estimate_fee = tx_results[0].step_used * tx_results[0].step_price

        # 2nd expired unstake
        self.make_empty_blocks(1)

        res: dict = self.get_stake(self._accounts[0])
        expected_res = {
            "stake": stake - 1 * ICX_IN_LOOP * 6,
            "unstakes": [
                {"unstake": 1 * ICX_IN_LOOP, "unstakeBlockHeight": 28, "remainingBlocks": 0},
                {"unstake": 1 * ICX_IN_LOOP, "unstakeBlockHeight": 29, "remainingBlocks": 1},
                {"unstake": 1 * ICX_IN_LOOP, "unstakeBlockHeight": 30, "remainingBlocks": 2},
            ]
        }
        self.assertEqual(res, expected_res)

        current_balance: int = self.get_balance(self._accounts[0])
        expected_exipred_stake_balance: int = 1 * ICX_IN_LOOP * expected_expired_ustake_cnt
        expected_balance: int = last_balance + expected_exipred_stake_balance - estimate_fee
        self.assertEqual(current_balance, expected_balance)

        self.transfer_icx(
            from_=self._accounts[0],
            to_=self._accounts[1],
            value=expected_balance-estimate_fee,
            disable_pre_validate=True,
            step_limit=1 * 10 ** 5,
            expected_status=True
        )

        res: dict = self.get_stake(self._accounts[0])
        expected_res = {
            "stake": stake - 1 * ICX_IN_LOOP * 6,
            "unstakes": [
                {"unstake": 1 * ICX_IN_LOOP, "unstakeBlockHeight": 29, "remainingBlocks": 0},
                {"unstake": 1 * ICX_IN_LOOP, "unstakeBlockHeight": 30, "remainingBlocks": 1},
            ]
        }
        self.assertEqual(res, expected_res)

        balance: int = self.get_balance(self._accounts[0])
        self.assertEqual(balance, expected_last_balance)

    def test_ghost_icx_case1(self):
        initial_balance: int = 150 * ICX_IN_LOOP
        stake: int = 100 * ICX_IN_LOOP
        balance, unstake_block_height = self._setup(
            init_balance=initial_balance,
            stake=stake
        )
        account = self._accounts[0]

        # transfer 10 icx to other account
        ghost_icx = stake
        transfer_value = 10 * ICX_IN_LOOP
        tx_results = self.transfer_icx(account, self._accounts[1], transfer_value)
        fee = tx_results[0].step_used * tx_results[0].step_price
        transfer_fee: int = fee
        # Balance | Stake   | UnStake    | Ghost_icx
        # 40 icx  | 0 icx   | 100 icx(e) | 100 icx
        self._check_ghost_icx(ghost_icx, unstake_block_height)

        # gain unstaked icx
        # Balance | Stake   | UnStake    | Ghost_icx
        # 140 icx | 0 icx   | 100 icx(e) | 0 icx
        expected_balance = balance - transfer_value - fee + stake
        self.assertEqual(expected_balance, self.get_balance(account))
        balance = expected_balance

        # set stake to 30
        stake = 30 * ICX_IN_LOOP
        tx_results: List['TransactionResult'] = self.set_stake(from_=account, value=stake)
        fee = tx_results[0].step_used * tx_results[0].step_price
        # Balance | Stake   | UnStake    | Ghost_icx
        # 210 icx | 30 icx  | 0 icx      | 0 icx
        expected_balance = balance - stake - fee + ghost_icx
        self.assertEqual(expected_balance, self.get_balance(account))
        balance = expected_balance
        response_stake = self.get_stake(account)
        self.assertEqual(stake, response_stake["stake"])
        self._check_ghost_icx_release()

        # account can transfer ghost icx all
        self.transfer_icx(
            account,
            self._accounts[1],
            balance - transfer_fee,
            step_limit=100_000,
        )
        actual_balance: int = self.get_balance(account=account)
        self.assertEqual(0, actual_balance)
        # Balance | Stake   | UnStake    | Ghost_icx
        # 0 icx   | 30 icx  | 0 icx      | 0 icx
        self.assertEqual(0, self.get_balance(account))
        response_stake = self.get_stake(account)
        self.assertEqual(stake, response_stake["stake"])
        self._check_ghost_icx_release()

    def test_ghost_icx_case2(self):
        initial_balance: int = 150 * ICX_IN_LOOP
        stake: int = 100 * ICX_IN_LOOP
        balance, unstake_block_height = self._setup(
            init_balance=initial_balance,
            stake=stake
        )

        # delegation
        ghost_icx: int = stake
        tx_results: List["TransactionResult"] = self.set_delegation(
            from_=self._accounts[0],
            origin_delegations=[
                (
                    self._accounts[0],
                    0
                )
            ]
        )
        fee = tx_results[0].step_used * tx_results[0].step_price
        expected_balance = balance - fee + ghost_icx
        self.assertEqual(expected_balance, self.get_balance(self._accounts[0]))
        balance = expected_balance

        # check ghost_icx 1
        self._check_ghost_icx(
            ghost_icx=ghost_icx,
            unstake_block_height=unstake_block_height
        )

        # Balance | Stake   | UnStake    | Ghost_icx
        # 150 icx | 0 icx   | 100 icx(e) | 100 icx

        tx_results: List["TransactionResult"] = self.set_delegation(
            from_=self._accounts[0],
            origin_delegations=[
                (
                    self._accounts[0],
                    0
                )
            ]
        )

        fee = tx_results[0].step_used * tx_results[0].step_price
        expected_balance = balance - fee + ghost_icx
        self.assertEqual(expected_balance, self.get_balance(self._accounts[0]))
        balance = expected_balance

        # check ghost_icx 2
        self._check_ghost_icx(
            ghost_icx=ghost_icx,
            unstake_block_height=unstake_block_height
        )

        # Balance | Stake   | UnStake    | Ghost_icx
        # 250 icx | 0 icx   | 100 icx(e) | 100 icx

        # Fix Unstake Bug
        self.set_revision(Revision.FIX_UNSTAKE_BUG.value)

        # Try Again
        tx_results: List["TransactionResult"] = self.set_delegation(
            from_=self._accounts[0],
            origin_delegations=[
                (
                    self._accounts[0],
                    0
                )
            ]
        )

        fee = tx_results[0].step_used * tx_results[0].step_price
        expected_balance = balance - fee + ghost_icx
        self.assertEqual(expected_balance, self.get_balance(self._accounts[0]))
        balance = expected_balance

        # check ghost_icx 3
        self._check_ghost_icx_release()

        # Balance | Stake   | UnStake    | Ghost_icx
        # 350 icx | 0 icx   | 0 icx(e) | 0 icx

        tx_results: List["TransactionResult"] = self.set_delegation(
            from_=self._accounts[0],
            origin_delegations=[
                (
                    self._accounts[0],
                    0
                )
            ]
        )

        fee = tx_results[0].step_used * tx_results[0].step_price
        expected_balance = balance - fee
        self.assertEqual(expected_balance, self.get_balance(self._accounts[0]))

        # check ghost_icx 4
        self._check_ghost_icx_release()

        # Balance | Stake   | UnStake    | Ghost_icx
        # 350 icx | 0 icx   | 0 icx(e) | 0 icx

    def _get_account_info(self, account: 'EOAAccount') -> dict:
        c_key: bytes = CoinPart.make_key(account.address)
        value: bytes = self.get_state_db(c_key)
        coin_part: 'CoinPart' = CoinPart.from_bytes(value)
        s_key: bytes = StakePart.make_key(account.address)
        value: bytes = self.get_state_db(s_key)
        state_part: 'StakePart' = StakePart.from_bytes(value)

        return {
            "coin": coin_part,
            "stake": state_part
        }

    def _check_ghost_icx(self, ghost_icx: int, unstake_block_height: int, account_count: int = 1):
        for i in range(account_count):
            get_stake_info: dict = self.get_stake(self._accounts[i])
            self.assertNotIn("unstakes", get_stake_info)
            db_info: dict = self._get_account_info(self._accounts[i])
            unstakes_info: list = db_info["stake"]._unstakes_info
            flag: CoinPartFlag = db_info["coin"].flags
            self.assertEqual(CoinPartFlag.NONE, flag)
            self.assertEqual(1, len(unstakes_info))
            self.assertEqual(ghost_icx, unstakes_info[0][0])
            self.assertEqual(unstake_block_height, unstakes_info[0][1])

    def _check_ghost_icx_release(self, account_count: int = 1):
        for i in range(account_count):
            get_stake_info: dict = self.get_stake(self._accounts[i])
            self.assertNotIn("unstakes", get_stake_info)
            db_info: dict = self._get_account_info(self._accounts[i])
            unstakes_info: list = db_info["stake"]._unstakes_info
            flag: CoinPartFlag = db_info["coin"].flags
            self.assertEqual(CoinPartFlag.NONE, flag)
            self.assertEqual(0, len(unstakes_info))

    def test_fix_bug_rev11(self):
        account_count: int = 5
        initial_balance: int = 150 * ICX_IN_LOOP
        stake: int = 100 * ICX_IN_LOOP
        balance, unstake_block_height = self._setup(
            init_balance=initial_balance,
            stake=stake,
            account_count=account_count
        )

        # TODO make ghost icx case

        # delegation
        ghost_icx: int = stake
        tx_list = []
        for i in range(account_count):
            tx = self.create_set_delegation_tx(
                from_=self._accounts[i],
                origin_delegations=[
                    (
                        self._accounts[i],
                        0
                    )
                ]
            )
            tx_list.append(tx)
        tx_results: List['TransactionResult'] = self.process_confirm_block_tx(tx_list=tx_list)

        expected_balance = 0
        for i in range(account_count):
            fee = tx_results[i].step_used * tx_results[i].step_price
            expected_balance = balance - fee + ghost_icx
            self.assertEqual(expected_balance, self.get_balance(self._accounts[i]))
        balance = expected_balance

        # check ghost_icx 1
        self._check_ghost_icx(
            ghost_icx=ghost_icx,
            unstake_block_height=unstake_block_height,
            account_count=account_count
        )

        # TODO update Revision 11

        # TODO check state DB

    def _setup(self, init_balance: int, stake: int, account_count: int = 1) -> tuple:
        self.update_governance()
        self.set_revision(Revision.MULTIPLE_UNSTAKE.value)
        # gain 150 icx
        balance: int = init_balance
        self.distribute_icx(
            accounts=self._accounts[:account_count],
            init_balance=balance
        )
        # Balance | Stake   | UnStake    | Ghost_icx
        # 150 icx | 0 icx   | 0 icx      | 0 icx

        # set stake
        tx_list = []
        for i in range(account_count):
            tx = self.create_set_stake_tx(from_=self._accounts[i], value=stake)
            tx_list.append(tx)
        tx_results: List['TransactionResult'] = self.process_confirm_block_tx(tx_list=tx_list)

        expected_balance = 0
        for i in range(account_count):
            fee = tx_results[i].step_used * tx_results[i].step_price
            expected_balance = balance - stake - fee
            self.assertEqual(expected_balance, self.get_balance(self._accounts[i]))
        balance = expected_balance
        # Balance | Stake   | UnStake    | Ghost_icx
        # 50 icx  | 100 icx | 0 icx      | 0 icx

        # unstake all staked value
        tx_list = []
        for i in range(account_count):
            tx = self.create_set_stake_tx(from_=self._accounts[i], value=0)
            tx_list.append(tx)
        tx_results: List['TransactionResult'] = self.process_confirm_block_tx(tx_list=tx_list)

        expected_balance = 0
        for i in range(account_count):
            fee = tx_results[i].step_used * tx_results[i].step_price
            expected_balance = balance - fee
            self.assertEqual(expected_balance, self.get_balance(self._accounts[i]))
        balance = expected_balance
        # Balance | Stake   | UnStake    | Ghost_icx
        # 50 icx  | 0 icx   | 100 icx    | 0 icx

        # wait expire unstake
        remaining_blocks = 0
        unstake_block_height: int = 0
        for i in range(account_count):
            unstake_info = self.get_stake(self._accounts[0])["unstakes"][0]
            unstake_block_height: int = unstake_info["unstakeBlockHeight"]
            remaining_blocks = unstake_info["remainingBlocks"]
        self.make_empty_blocks(remaining_blocks + 1)
        # Balance | Stake   | UnStake    | Ghost_icx
        # 50 icx  | 0 icx   | 100 icx(e) | 100 icx

        return balance, unstake_block_height
