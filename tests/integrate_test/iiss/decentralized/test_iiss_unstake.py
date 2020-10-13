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
import json
import os
from typing import TYPE_CHECKING, List, Tuple
from unittest.mock import patch

from iconservice.icon_constant import Revision, ICX_IN_LOOP, ConfigKey
from iconservice.icx.coin_part import CoinPart, CoinPartFlag
from iconservice.icx.stake_part import StakePart
from iconservice.icx.unstake_patcher import INVALID_EXPIRED_UNSTAKES_FILENAME
from iconservice.icx.unstake_patcher import UnstakePatcher, Target
from tests.integrate_test.iiss.test_iiss_base import TestIISSBase

if TYPE_CHECKING:
    from iconservice.iconscore.icon_score_result import TransactionResult
    from tests.integrate_test.test_integrate_base import EOAAccount


class TestIISSUnStake1(TestIISSBase):
    def test_unstake_balance_rev_10(self):
        self._test_unstake_balance(
            rev=Revision.FIX_UNSTAKE_BUG.value,
            expected_expired_unstake_cnt=2,
            expected_last_balance=0
        )

    def test_unstake_balance_rev_11(self):
        self._test_unstake_balance(
            rev=Revision.FIX_BALANCE_BUG.value,
            expected_expired_unstake_cnt=3,
            expected_last_balance=1 * ICX_IN_LOOP
        )

    def _test_unstake_balance(
            self,
            rev: int,
            expected_expired_unstake_cnt: int,
            expected_last_balance: int
    ):
        self.init_decentralized()
        self.init_inv()

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
        fee = tx_results[1].step_used * tx_results[1].step_price
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
                {"unstake": 1 * ICX_IN_LOOP, "unstakeBlockHeight": 70, "remainingBlocks": first_remaining_blocks},
                {"unstake": 1 * ICX_IN_LOOP, "unstakeBlockHeight": 71, "remainingBlocks": first_remaining_blocks+1},
                {"unstake": 1 * ICX_IN_LOOP, "unstakeBlockHeight": 72, "remainingBlocks": first_remaining_blocks+2},
                {"unstake": 1 * ICX_IN_LOOP, "unstakeBlockHeight": 73, "remainingBlocks": first_remaining_blocks+3},
                {"unstake": 1 * ICX_IN_LOOP, "unstakeBlockHeight": 74, "remainingBlocks": first_remaining_blocks+4},
                {"unstake": 1 * ICX_IN_LOOP, "unstakeBlockHeight": 75, "remainingBlocks": first_remaining_blocks+5},
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
                {"unstake": 1 * ICX_IN_LOOP, "unstakeBlockHeight": 71, "remainingBlocks": 0},
                {"unstake": 1 * ICX_IN_LOOP, "unstakeBlockHeight": 72, "remainingBlocks": 1},
                {"unstake": 1 * ICX_IN_LOOP, "unstakeBlockHeight": 73, "remainingBlocks": 2},
                {"unstake": 1 * ICX_IN_LOOP, "unstakeBlockHeight": 74, "remainingBlocks": 3},
                {"unstake": 1 * ICX_IN_LOOP, "unstakeBlockHeight": 75, "remainingBlocks": 4},
            ]
        }
        self.assertEqual(res, expected_res)

        tx_results = self.transfer_icx(from_=self._accounts[0], to_=self._accounts[1], value=0)

        res: dict = self.get_stake(self._accounts[0])
        expected_res = {
            "stake": stake - 1 * ICX_IN_LOOP * 6,
            "unstakes": [
                {"unstake": 1 * ICX_IN_LOOP, "unstakeBlockHeight": 72, "remainingBlocks": 0},
                {"unstake": 1 * ICX_IN_LOOP, "unstakeBlockHeight": 73, "remainingBlocks": 1},
                {"unstake": 1 * ICX_IN_LOOP, "unstakeBlockHeight": 74, "remainingBlocks": 2},
                {"unstake": 1 * ICX_IN_LOOP, "unstakeBlockHeight": 75, "remainingBlocks": 3},
            ]
        }
        self.assertEqual(res, expected_res)

        estimate_fee = tx_results[1].step_used * tx_results[1].step_price

        # 2nd expired unstake
        self.make_empty_blocks(1)

        res: dict = self.get_stake(self._accounts[0])
        expected_res = {
            "stake": stake - 1 * ICX_IN_LOOP * 6,
            "unstakes": [
                {"unstake": 1 * ICX_IN_LOOP, "unstakeBlockHeight": 73, "remainingBlocks": 0},
                {"unstake": 1 * ICX_IN_LOOP, "unstakeBlockHeight": 74, "remainingBlocks": 1},
                {"unstake": 1 * ICX_IN_LOOP, "unstakeBlockHeight": 75, "remainingBlocks": 2},
            ]
        }
        self.assertEqual(res, expected_res)

        current_balance: int = self.get_balance(self._accounts[0])
        expected_expired_stake_balance: int = 1 * ICX_IN_LOOP * expected_expired_unstake_cnt
        expected_balance: int = last_balance + expected_expired_stake_balance - estimate_fee
        self.assertEqual(current_balance, expected_balance)

        self.transfer_icx(
            from_=self._accounts[0],
            to_=self._accounts[1],
            value=expected_balance-estimate_fee,
            disable_pre_validate=True,
            step_limit=100_000,
            expected_status=True
        )

        res: dict = self.get_stake(self._accounts[0])
        expected_res = {
            "stake": stake - 1 * ICX_IN_LOOP * 6,
            "unstakes": [
                {"unstake": 1 * ICX_IN_LOOP, "unstakeBlockHeight": 74, "remainingBlocks": 0},
                {"unstake": 1 * ICX_IN_LOOP, "unstakeBlockHeight": 75, "remainingBlocks": 1},
            ]
        }
        self.assertEqual(res, expected_res)

        balance: int = self.get_balance(self._accounts[0])
        self.assertEqual(balance, expected_last_balance)


class TestIISSUnStake2(TestIISSBase):
    def tearDown(self):
        super().tearDown()
        names: List[str] = INVALID_EXPIRED_UNSTAKES_FILENAME.split(".")
        log_dir = "."
        report_path: str = os.path.join(log_dir, f"{names[0]}_report.json")
        if os.path.isfile(report_path):
            os.remove(report_path)

    def _setup(
            self,
            init_balance: int,
            stake: int,
            unstake_count: int = 1,
            account_count: int = 1
    ) -> list:
        self.init_decentralized()
        self.init_inv()
        self.set_revision(Revision.MULTIPLE_UNSTAKE.value)

        # gain 150 icx
        self.distribute_icx(
            accounts=self._accounts[:account_count],
            init_balance=init_balance
        )
        for i in range(account_count):
            self._accounts[i].balance = init_balance

        # Balance | Stake   | UnStake    | Expired_icx
        # 150 icx | 0 icx   | 0 icx      | 0 icx

        # set stake
        tx_list = []
        for i in range(account_count):
            tx = self.create_set_stake_tx(from_=self._accounts[i], value=stake)
            tx_list.append(tx)
        tx_results: List['TransactionResult'] = self.process_confirm_block_tx(tx_list=tx_list)

        for i in range(account_count):
            fee = tx_results[i+1].step_used * tx_results[i+1].step_price
            expected_balance = self._accounts[i].balance - stake - fee
            self.assertEqual(expected_balance, self.get_balance(self._accounts[i]))
            self._accounts[i].balance = expected_balance
        # Balance | Stake   | UnStake    | Expired_icx
        # 50 icx  | 100 icx | 0 icx      | 0 icx

        # unstake (unstake_count - 1) times
        tx_list = []
        unstake = stake // unstake_count
        for i in range(unstake_count-1):
            for j in range(account_count):
                unstake_value = (i+1) * unstake
                tx = self.create_set_stake_tx(from_=self._accounts[j], value=stake - unstake_value)
                tx_list.append(tx)
            tx_results: List['TransactionResult'] = self.process_confirm_block_tx(tx_list=tx_list)

            for j in range(account_count):
                fee = tx_results[j+1].step_used * tx_results[j+1].step_price
                expected_balance = self._accounts[i].balance - fee
                self.assertEqual(expected_balance, self.get_balance(self._accounts[j]))
                self._accounts[i].balance = expected_balance

        # unstake all staked value
        tx_list = []
        for i in range(account_count):
            tx = self.create_set_stake_tx(from_=self._accounts[i], value=0)
            tx_list.append(tx)
        tx_results: List['TransactionResult'] = self.process_confirm_block_tx(tx_list=tx_list)

        for i in range(account_count):
            fee = tx_results[i+1].step_used * tx_results[i+1].step_price
            expected_balance = self._accounts[i].balance - fee
            self.assertEqual(expected_balance, self.get_balance(self._accounts[i]))
            self._accounts[i].balance = expected_balance

        # Balance | Stake   | UnStake    | Expired_icx
        # 50 icx  | 0 icx   | 100 icx    | 0 icx

        # wait expire unstake
        remaining_blocks = 0

        rets = []
        for i in range(account_count):
            unstakes_info: list = self.get_stake(self._accounts[0]).get("unstakes")
            rets.append(unstakes_info)
            unstake_info = unstakes_info[-1]
            remaining_blocks = unstake_info["remainingBlocks"]
        self.make_empty_blocks(remaining_blocks + 1)
        # Balance | Stake   | UnStake    | Expired_icx
        # 50 icx  | 0 icx   | 100 icx(e) | 100 icx
        return rets

    def test_expired_icx_case1(self):
        initial_balance: int = 150 * ICX_IN_LOOP
        stake: int = 100 * ICX_IN_LOOP
        unstakes_info_per_account: list = self._setup(
            init_balance=initial_balance,
            stake=stake
        )

        # transfer 10 icx to other account
        expired_icx = stake
        transfer_value = 10 * ICX_IN_LOOP
        tx_results = self.transfer_icx(self._accounts[0], self._accounts[1], transfer_value)
        fee = tx_results[1].step_used * tx_results[1].step_price
        transfer_fee: int = fee
        account0_unstakes_info = unstakes_info_per_account[0]
        expired_unstake = (
            account0_unstakes_info[0]["unstake"],
            account0_unstakes_info[0]["unstakeBlockHeight"]
        )
        expired_unstakes_info = [expired_unstake]
        # Balance | Stake   | UnStake    | Expired_icx
        # 40 icx  | 0 icx   | 100 icx(e) | 100 icx
        self._check_expired_icx(expired_icx, expired_unstakes_info)

        # gain unstaked icx
        # Balance | Stake   | UnStake    | Expired_icx
        # 140 icx | 0 icx   | 100 icx(e) | 0 icx
        expected_balance = self._accounts[0].balance - transfer_value - fee + stake
        self.assertEqual(expected_balance, self.get_balance(self._accounts[0]))
        self._accounts[0].balance = expected_balance

        # set stake to 30
        stake = 30 * ICX_IN_LOOP
        tx_results: List['TransactionResult'] = self.set_stake(
            from_=self._accounts[0],
            value=stake
        )
        fee = tx_results[1].step_used * tx_results[1].step_price
        # Balance | Stake   | UnStake    | Expired_icx
        # 210 icx | 30 icx  | 0 icx      | 0 icx
        expected_balance = self._accounts[0].balance - stake - fee + expired_icx
        self.assertEqual(expected_balance, self.get_balance(self._accounts[0]))
        self._accounts[0].balance = expected_balance

        response_stake = self.get_stake(self._accounts[0])
        self.assertEqual(stake, response_stake["stake"])
        self._check_expired_icx_release()

        # account can transfer invalid expired icx all
        self.transfer_icx(
            self._accounts[0],
            self._accounts[1],
            self._accounts[0].balance - transfer_fee,
            step_limit=100_000,
        )
        actual_balance: int = self.get_balance(account=self._accounts[0])
        self.assertEqual(0, actual_balance)

        # Balance | Stake   | UnStake    | Expired_icx
        # 0 icx   | 30 icx  | 0 icx      | 0 icx
        response_stake = self.get_stake(self._accounts[0])
        self.assertEqual(stake, response_stake["stake"])
        self._check_expired_icx_release()

    def test_multiple_expired_icx(self):
        initial_balance: int = 150 * ICX_IN_LOOP
        stake: int = 100 * ICX_IN_LOOP
        unstakes_info_per_account: list = self._setup(
            init_balance=initial_balance,
            stake=stake,
            unstake_count=2
        )

        # transfer 10 icx to other account
        expired_icx = stake
        transfer_value = 10 * ICX_IN_LOOP
        tx_results = self.transfer_icx(
            self._accounts[0],
            self._accounts[1],
            transfer_value
        )
        fee = tx_results[1].step_used * tx_results[1].step_price
        account0_unstakes_info = unstakes_info_per_account[0]
        expired_unstake1 = (
            account0_unstakes_info[0]["unstake"],
            account0_unstakes_info[0]["unstakeBlockHeight"]
        )
        expired_unstake2 = (
            account0_unstakes_info[1]["unstake"],
            account0_unstakes_info[1]["unstakeBlockHeight"]
        )
        expired_unstakes_info = [expired_unstake1, expired_unstake2]
        # Balance | Stake   | UnStake    | Expired_icx
        # 40 icx  | 0 icx   | 100 icx(e) | 100 icx
        self._check_expired_icx(expired_icx, expired_unstakes_info)

        # gain unstaked icx
        # Balance | Stake   | UnStake    | Expired_icx
        # 140 icx | 0 icx   | 100 icx(e) | 0 icx
        expected_balance = self._accounts[0].balance - transfer_value - fee + stake
        self.assertEqual(expected_balance, self.get_balance(self._accounts[0]))
        self._accounts[0].balance = expected_balance

        # fix unstake bug
        self.set_revision(Revision.FIX_UNSTAKE_BUG.value)

        # transfer 10 icx to other account
        transfer_value = 10 * ICX_IN_LOOP
        tx_results = self.transfer_icx(
            self._accounts[0],
            self._accounts[1],
            transfer_value
        )
        fee = tx_results[1].step_used * tx_results[1].step_price
        transfer_fee: int = fee
        account0_unstakes_info = unstakes_info_per_account[0]
        expired_unstake1 = (
            account0_unstakes_info[0]["unstake"],
            account0_unstakes_info[0]["unstakeBlockHeight"]
        )
        expired_unstake2 = (
            account0_unstakes_info[1]["unstake"],
            account0_unstakes_info[1]["unstakeBlockHeight"]
        )
        expired_unstakes_info = [expired_unstake1, expired_unstake2]
        self._check_expired_icx(expired_icx, expired_unstakes_info)

        # invalid expired icx will not be produced
        # Balance | Stake   | UnStake    | Expired_icx
        # 130 icx | 0 icx   | 100 icx(e) | 0 icx
        expected_balance = self._accounts[0].balance - transfer_value - fee
        self.assertEqual(expected_balance, self.get_balance(self._accounts[0]))
        self._accounts[0].balance = expected_balance

        # set stake to 30
        stake = 30 * ICX_IN_LOOP
        tx_results: List['TransactionResult'] = self.set_stake(
            from_=self._accounts[0],
            value=stake
        )
        fee = tx_results[1].step_used * tx_results[1].step_price
        # Balance | Stake   | UnStake    | Expired_icx
        # 200 icx | 30 icx  | 0 icx      | 0 icx
        expected_balance = self._accounts[0].balance - stake - fee + expired_icx
        self.assertEqual(expected_balance, self.get_balance(self._accounts[0]))
        self._accounts[0].balance = expected_balance

        response_stake = self.get_stake(self._accounts[0])
        self.assertEqual(stake, response_stake["stake"])
        self._check_expired_icx_release()

        # account can transfer invalid expired icx all
        self.transfer_icx(
            self._accounts[0],
            self._accounts[1],
            self._accounts[0].balance - transfer_fee,
            step_limit=100_000,
        )
        actual_balance: int = self.get_balance(account=self._accounts[0])
        self.assertEqual(0, actual_balance)
        # Balance | Stake   | UnStake    | Expired_icx
        # 0 icx   | 30 icx  | 0 icx      | 0 icx

        response_stake = self.get_stake(self._accounts[0])
        self.assertEqual(stake, response_stake["stake"])
        self._check_expired_icx_release()

    def test_expired_icx_case2_1_gain_icx(self):
        initial_balance: int = 150 * ICX_IN_LOOP
        stake: int = 100 * ICX_IN_LOOP
        unstakes_info_per_account: list = self._setup(
            init_balance=initial_balance,
            stake=stake
        )

        # delegation
        expired_icx: int = stake

        def set_delegation():
            _tx_results: List["TransactionResult"] = self.set_delegation(
                from_=self._accounts[0],
                origin_delegations=[
                    (
                        self._accounts[0],
                        0
                    )
                ]
            )
            _fee = _tx_results[1].step_used * _tx_results[1].step_price
            _expected_balance = self._accounts[0].balance - _fee + expired_icx
            self.assertEqual(_expected_balance, self.get_balance(self._accounts[0]))
            self._accounts[0].balance = _expected_balance

        set_delegation()
        account0_unstakes_info = unstakes_info_per_account[0]
        expired_unstake = (
            account0_unstakes_info[0]["unstake"],
            account0_unstakes_info[0]["unstakeBlockHeight"]
        )
        expired_unstake_info = [expired_unstake]
        # check expired_icx 1
        self._check_expired_icx(
            expired_icx=expired_icx,
            expired_unstakes_info=expired_unstake_info
        )

        # Balance | Stake   | UnStake    | Expired_icx
        # 150 icx | 0 icx   | 100 icx(e) | 100 icx

        set_delegation()
        # check expired_icx 2
        self._check_expired_icx(
            expired_icx=expired_icx,
            expired_unstakes_info=expired_unstake_info
        )

        # Balance | Stake   | UnStake    | Expired_icx
        # 250 icx | 0 icx   | 100 icx(e) | 100 icx

        # Fix Unstake Bug
        self.set_revision(Revision.FIX_UNSTAKE_BUG.value)

        # Try Again
        set_delegation()

        # check expired_icx 3
        self._check_expired_icx_release()

        # Balance | Stake   | UnStake    | Expired_icx
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

        fee = tx_results[1].step_used * tx_results[1].step_price
        expected_balance = self._accounts[0].balance - fee
        self.assertEqual(expected_balance, self.get_balance(self._accounts[0]))
        self._accounts[0].balance = expected_balance

        # check expired_icx 4
        self._check_expired_icx_release()

        # Balance | Stake   | UnStake    | Expired_icx
        # 350 icx | 0 icx   | 0 icx(e) | 0 icx

    def test_expired_icx_case2_2_transfer_icx(self):
        initial_balance: int = 150 * ICX_IN_LOOP
        stake: int = 100 * ICX_IN_LOOP
        unstakes_info_per_account: list = self._setup(
            init_balance=initial_balance,
            stake=stake
        )

        expired_icx: int = stake
        # transfer icx 10
        transfer_value = 10 * ICX_IN_LOOP
        tx_results = self.transfer_icx(self._accounts[0], self._accounts[1], transfer_value)
        fee = tx_results[1].step_used * tx_results[1].step_price
        transfer_fee: int = fee
        account0_unstakes_info = unstakes_info_per_account[0]
        expired_unstake = (
            account0_unstakes_info[0]["unstake"],
            account0_unstakes_info[0]["unstakeBlockHeight"]
        )
        expired_unstakes_info = [expired_unstake]
        # Balance | Stake   | UnStake    | Expired_icx
        # 40 icx  | 0 icx   | 100 icx(e) | 100 icx
        self._check_expired_icx(expired_icx, expired_unstakes_info)
        self._accounts[0].balance = self.get_balance(self._accounts[0])

        # delegation
        def set_delegation():
            _tx_results: List["TransactionResult"] = self.set_delegation(
                from_=self._accounts[0],
                origin_delegations=[
                    (
                        self._accounts[0],
                        0
                    )
                ]
            )
            _fee = _tx_results[1].step_used * _tx_results[1].step_price
            expected_balance = self._accounts[0].balance - _fee + expired_icx
            self.assertEqual(expected_balance, self.get_balance(self._accounts[0]))
            self._accounts[0].balance = expected_balance

        set_delegation()
        account0_unstakes_info = unstakes_info_per_account[0]
        expired_unstake = (
            account0_unstakes_info[0]["unstake"],
            account0_unstakes_info[0]["unstakeBlockHeight"]
        )
        expired_unstake_info = [expired_unstake]

        # check expired_icx 1
        self._check_expired_icx(
            expired_icx=expired_icx,
            expired_unstakes_info=expired_unstake_info
        )

        # Balance | Stake   | UnStake    | Expired_icx
        # 140 icx | 0 icx   | 100 icx(e) | 100 icx

        set_delegation()
        # check expired_icx 2
        self._check_expired_icx(
            expired_icx=expired_icx,
            expired_unstakes_info=expired_unstake_info
        )

        # Balance | Stake   | UnStake    | Expired_icx
        # 240 icx | 0 icx   | 100 icx(e) | 100 icx

        # account can transfer invalid expired icx all
        self.transfer_icx(
            self._accounts[0],
            self._accounts[1],
            self._accounts[0].balance - transfer_fee,
            step_limit=100_000,
            )
        actual_balance: int = self.get_balance(account=self._accounts[0])
        self.assertEqual(0, actual_balance)
        # Balance | Stake   | UnStake    | Expired_icx
        # 0 icx   | 0 icx   | 0 icx      | 100 icx

        self._check_expired_icx(
            expired_icx=expired_icx,
            expired_unstakes_info=expired_unstake_info
        )

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

    def _check_expired_icx(self, expired_icx: int,
                           expired_unstakes_info: List[Tuple[int, int]], account_count: int = 1):
        for i in range(account_count):
            get_stake_info: dict = self.get_stake(self._accounts[i])
            self.assertNotIn("unstakes", get_stake_info)
            db_info: dict = self._get_account_info(self._accounts[i])
            unstakes_info: list = db_info["stake"]._unstakes_info
            flag: CoinPartFlag = db_info["coin"].flags
            self.assertEqual(CoinPartFlag.NONE, flag)
            self.assertGreaterEqual(len(unstakes_info), 1)
            expired_unstake = 0
            for j, unstake_info in enumerate(expired_unstakes_info):
                expired_unstake += unstake_info[0]
                self.assertEqual(unstake_info[0], unstakes_info[j][0])
                self.assertEqual(unstake_info[1], unstakes_info[j][1])
            self.assertEqual(expired_icx, expired_unstake)

    def _check_expired_icx_release(self, account_count: int = 1):
        for i in range(account_count):
            get_stake_info: dict = self.get_stake(self._accounts[i])
            self.assertNotIn("unstakes", get_stake_info)
            db_info: dict = self._get_account_info(self._accounts[i])
            unstakes_info: list = db_info["stake"]._unstakes_info
            flag: CoinPartFlag = db_info["coin"].flags
            self.assertEqual(CoinPartFlag.NONE, flag)
            self.assertEqual(0, len(unstakes_info))

    def test_fix_bug_rev11_all_success(self):
        account_count: int = 5
        initial_balance: int = 150 * ICX_IN_LOOP
        stake: int = 100 * ICX_IN_LOOP
        unstakes_info_per_account: list = self._setup(
            init_balance=initial_balance,
            stake=stake,
            account_count=account_count
        )

        # delegation
        expired_icx: int = stake
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

        for i in range(account_count):
            fee = tx_results[i+1].step_used * tx_results[i+1].step_price
            expected_balance = self._accounts[i].balance - fee + expired_icx
            self.assertEqual(expected_balance, self.get_balance(self._accounts[i]))

        # check expired_icx 1
        account0_unstakes_info = unstakes_info_per_account[0]
        expired_unstake = (
            account0_unstakes_info[0]["unstake"],
            account0_unstakes_info[0]["unstakeBlockHeight"]
        )
        expired_unstakes_info = [expired_unstake]
        self._check_expired_icx(
            expired_icx=expired_icx,
            expired_unstakes_info=expired_unstakes_info,
            account_count=account_count
        )

        src: list = []
        for i in range(account_count):
            db_info: dict = self._get_account_info(self._accounts[0])
            stake_part: 'StakePart' = db_info["stake"]
            data: dict = {
                "address": str(self._accounts[i].address),
                "total_unstake": stake_part._stake + stake_part._total_unstake(),
                "old_unstake_format": False,
                "unstakes": [
                    [
                        stake_part._unstakes_info[0][0],
                        stake_part._unstakes_info[0][1]
                    ],
                ]
            }
            src.append(data)

        targets: List[Target] = [Target.from_dict(i) for i in src]
        patcher = UnstakePatcher(targets=targets)

        with patch.object(UnstakePatcher, 'from_path') as from_path_mock:
            from_path_mock.return_value = patcher

            self.set_revision(Revision.FIX_BALANCE_BUG.value)
            self._check_expired_icx_release(account_count=account_count)

        # Retry
        # sync balance
        for i in range(account_count):
            self._accounts[i].balance = self.get_balance(self._accounts[i])

        # set stake
        tx_list = []
        for i in range(account_count):
            tx = self.create_set_stake_tx(from_=self._accounts[i], value=stake)
            tx_list.append(tx)
        tx_results: List['TransactionResult'] = self.process_confirm_block_tx(tx_list=tx_list)

        for i in range(account_count):
            fee = tx_results[i+1].step_used * tx_results[i+1].step_price
            expected_balance = self._accounts[i].balance - stake - fee
            self.assertEqual(expected_balance, self.get_balance(self._accounts[i]))
            self._accounts[i].balance = expected_balance
        # Balance | Stake   | UnStake    | Expired_icx
        # 50 icx  | 100 icx | 0 icx      | 0 icx

        # unstake (unstake_count - 1) times
        tx_list = []
        unstake = stake // 1
        for i in range(1-1):
            for j in range(account_count):
                unstake_value = (i+1) * unstake
                tx = self.create_set_stake_tx(from_=self._accounts[j], value=stake - unstake_value)
                tx_list.append(tx)
            tx_results: List['TransactionResult'] = self.process_confirm_block_tx(tx_list=tx_list)

            for j in range(account_count):
                fee = tx_results[j+1].step_used * tx_results[j+1].step_price
                expected_balance = self._accounts[i].balance - fee
                self.assertEqual(expected_balance, self.get_balance(self._accounts[j]))
                self._accounts[i].balance = expected_balance

        # unstake all staked value
        tx_list = []
        for i in range(account_count):
            tx = self.create_set_stake_tx(from_=self._accounts[i], value=0)
            tx_list.append(tx)
        tx_results: List['TransactionResult'] = self.process_confirm_block_tx(tx_list=tx_list)

        for i in range(account_count):
            fee = tx_results[i+1].step_used * tx_results[i+1].step_price
            expected_balance = self._accounts[i].balance - fee
            self.assertEqual(expected_balance, self.get_balance(self._accounts[i]))
            self._accounts[i].balance = expected_balance

        # Balance | Stake   | UnStake    | Expired_icx
        # 50 icx  | 0 icx   | 100 icx    | 0 icx

        # wait expire unstake
        remaining_blocks = 0

        rets = []
        for i in range(account_count):
            unstakes_info: list = self.get_stake(self._accounts[0]).get("unstakes")
            rets.append(unstakes_info)
            unstake_info = unstakes_info[-1]
            remaining_blocks = unstake_info["remainingBlocks"]
        self.make_empty_blocks(remaining_blocks + 1)

        # delegation
        expired_icx: int = stake
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

        for i in range(account_count):
            fee = tx_results[i+1].step_used * tx_results[i+1].step_price
            expected_balance = self._accounts[i].balance - fee + expired_icx
            self.assertEqual(expected_balance, self.get_balance(self._accounts[i]))

        # check expired_icx 1
        account0_unstakes_info = unstakes_info_per_account[0]
        expired_unstake = (
            account0_unstakes_info[0]["unstake"],
            account0_unstakes_info[0]["unstakeBlockHeight"]
        )
        self._check_expired_icx_release(account_count=account_count)

    def test_fix_bug_rev11_all_success2(self):
        account_count: int = 5
        initial_balance: int = 150 * ICX_IN_LOOP
        stake: int = 100 * ICX_IN_LOOP
        unstakes_info_per_account: list = self._setup(
            init_balance=initial_balance,
            stake=stake,
            account_count=account_count
        )

        # delegation
        expired_icx: int = stake
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

        for i in range(account_count):
            fee = tx_results[i+1].step_used * tx_results[i+1].step_price
            expected_balance = self._accounts[i].balance - fee + expired_icx
            self.assertEqual(expected_balance, self.get_balance(self._accounts[i]))

        # check expired_icx 1
        account0_unstakes_info = unstakes_info_per_account[0]
        expired_unstake = (
            account0_unstakes_info[0]["unstake"],
            account0_unstakes_info[0]["unstakeBlockHeight"]
        )
        expired_unstakes_info = [expired_unstake]
        self._check_expired_icx(
            expired_icx=expired_icx,
            expired_unstakes_info=expired_unstakes_info,
            account_count=account_count
        )

        src: list = []
        for i in range(account_count):
            db_info: dict = self._get_account_info(self._accounts[0])
            stake_part: 'StakePart' = db_info["stake"]
            data: dict = {
                "address": str(self._accounts[i].address),
                "total_unstake": stake_part._stake + stake_part._total_unstake(),
                "old_unstake_format": False,
                "unstakes": [
                    [
                        stake_part._unstakes_info[0][0],
                        stake_part._unstakes_info[0][1]
                    ],
                ]
            }
            src.append(data)

        targets: List[Target] = [Target.from_dict(i) for i in src]
        patcher = UnstakePatcher(targets=targets)

        with patch.object(UnstakePatcher, 'from_path') as from_path_mock:
            from_path_mock.return_value = patcher

            self.set_revision(Revision.FIX_BALANCE_BUG.value)
            self._check_expired_icx_release(account_count=account_count)

    def test_fix_bug_rev11_all_fail(self):
        account_count: int = 5
        initial_balance: int = 150 * ICX_IN_LOOP
        stake: int = 100 * ICX_IN_LOOP
        unstakes_info_per_account: list = self._setup(
            init_balance=initial_balance,
            stake=stake,
            account_count=account_count
        )

        # delegation
        expired_icx: int = stake
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

        for i in range(account_count):
            fee = tx_results[i+1].step_used * tx_results[i+1].step_price
            expected_balance = self._accounts[i].balance - fee + expired_icx
            self.assertEqual(expected_balance, self.get_balance(self._accounts[i]))

        # check expired_icx 1
        account0_unstakes_info = unstakes_info_per_account[0]
        expired_unstake = (
            account0_unstakes_info[0]["unstake"],
            account0_unstakes_info[0]["unstakeBlockHeight"]
        )
        expired_unstakes_info = [expired_unstake]
        self._check_expired_icx(
            expired_icx=expired_icx,
            expired_unstakes_info=expired_unstakes_info,
            account_count=account_count
        )

        src: list = []
        for i in range(account_count):
            db_info: dict = self._get_account_info(self._accounts[0])
            stake_part: 'StakePart' = db_info["stake"]
            data: dict = {
                "address": str(self._accounts[i].address),
                "total_unstake": stake_part._stake + stake_part._total_unstake(),
                "old_unstake_format": False,
                "unstakes": [
                    [
                        stake_part._unstakes_info[0][0] - 1,
                        stake_part._unstakes_info[0][1]
                    ],
                ]
            }
            src.append(data)

        targets: List[Target] = [Target.from_dict(i) for i in src]
        patcher = UnstakePatcher(targets=targets)

        with patch.object(UnstakePatcher, 'from_path') as from_path_mock:
            from_path_mock.return_value = patcher

            self.set_revision(Revision.FIX_BALANCE_BUG.value)


class TestIISSUnStake3(TestIISSBase):
    def test_old_format1(self):
        self.init_decentralized()
        self.init_inv()

        init_balance: int = 150 * ICX_IN_LOOP
        stake: int = 100 * ICX_IN_LOOP
        # gain 150 icx
        self.distribute_icx(
            accounts=self._accounts[:1],
            init_balance=init_balance
        )

        self._accounts[0].balance = init_balance
        # Balance | Stake   | UnStake    | Expired_icx
        # 150 icx | 0 icx   | 0 icx      | 0 icx

        # set stake
        expired_icx: int = stake
        tx = self.create_set_stake_tx(from_=self._accounts[0], value=stake)
        tx_results: List['TransactionResult'] = self.process_confirm_block_tx(tx_list=[tx])
        fee = tx_results[1].step_used * tx_results[1].step_price
        expected_balance = self._accounts[0].balance - stake - fee
        self.assertEqual(expected_balance, self.get_balance(self._accounts[0]))
        self._accounts[0].balance = expected_balance

        # Balance | Stake   | UnStake    | Expired_icx
        # 50 icx  | 100 icx | 0 icx      | 0 icx

        # unstake all staked value
        tx = self.create_set_stake_tx(from_=self._accounts[0], value=0)
        tx_results: List['TransactionResult'] = self.process_confirm_block_tx(tx_list=[tx])
        fee = tx_results[1].step_used * tx_results[1].step_price
        expected_balance = self._accounts[0].balance - fee
        self.assertEqual(expected_balance, self.get_balance(self._accounts[0]))
        self._accounts[0].balance = expected_balance

        res: dict = self.get_stake(self._accounts[0])
        remaining_blocks: int = res["remainingBlocks"]
        unstake_block_height: int = res["unstakeBlockHeight"]
        self.make_empty_blocks(remaining_blocks + 1)
        # Balance | Stake   | UnStake    | Expired_icx
        # 50 icx  | 0 icx   | 100 icx(e) | 100 icx

        self.set_revision(Revision.MULTIPLE_UNSTAKE.value)

        # old format
        db_info: dict = self._get_account_info(self._accounts[0])
        coin_part: 'CoinPart' = db_info["coin"]
        stake_part: 'StakePart' = db_info["stake"]
        self.assertEqual(CoinPartFlag.HAS_UNSTAKE, coin_part._flags)
        self.assertEqual(0, stake_part._stake)
        self.assertEqual(expired_icx, stake_part._unstake)
        self.assertEqual(unstake_block_height, stake_part._unstake_block_height)

        tx_results: List["TransactionResult"] = self.set_delegation(
            from_=self._accounts[0],
            origin_delegations=[
                (
                    self._accounts[0],
                    0
                )
            ]
        )
        fee = tx_results[1].step_used * tx_results[1].step_price
        expected_balance = self._accounts[0].balance - fee + expired_icx
        self.assertEqual(expected_balance, self.get_balance(self._accounts[0]))
        self._accounts[0].balance = expected_balance

        # old format
        db_info: dict = self._get_account_info(self._accounts[0])
        coin_part: 'CoinPart' = db_info["coin"]
        stake_part: 'StakePart' = db_info["stake"]
        self.assertEqual(CoinPartFlag.NONE, coin_part._flags)
        self.assertEqual(0, stake_part._stake)
        self.assertEqual(expired_icx, stake_part._unstake)
        self.assertEqual(unstake_block_height, stake_part._unstake_block_height)

        # Check Fix logic
        data: list = [
            {
                "address": str(self._accounts[0].address),
                "total_unstake": stake_part._stake + stake_part._total_unstake(),
                "old_unstake_format": True,
                "unstakes": [
                    [
                        stake_part._unstake,
                        stake_part._unstake_block_height
                    ],
                ]
            },
        ]
        targets: List[Target] = [Target.from_dict(i) for i in data]
        patcher = UnstakePatcher(targets=targets)
        with patch.object(UnstakePatcher, 'from_path') as from_path_mock:
            from_path_mock.return_value = patcher

            self.set_revision(Revision.FIX_BALANCE_BUG.value)
            self._check_unstake_patch()

    def test_new_format(self):
        self.init_decentralized()
        self.init_inv()

        init_balance: int = 150 * ICX_IN_LOOP
        stake: int = 100 * ICX_IN_LOOP
        # gain 150 icx
        self.distribute_icx(
            accounts=self._accounts[:1],
            init_balance=init_balance
        )

        self._accounts[0].balance = init_balance
        # Balance | Stake   | UnStake    | Expired_icx
        # 150 icx | 0 icx   | 0 icx      | 0 icx

        # set stake
        expired_icx: int = stake
        tx = self.create_set_stake_tx(from_=self._accounts[0], value=stake)
        tx_results: List['TransactionResult'] = self.process_confirm_block_tx(tx_list=[tx])
        fee = tx_results[1].step_used * tx_results[1].step_price
        expected_balance = self._accounts[0].balance - stake - fee
        self.assertEqual(expected_balance, self.get_balance(self._accounts[0]))
        self._accounts[0].balance = expected_balance

        # Balance | Stake   | UnStake    | Expired_icx
        # 50 icx  | 100 icx | 0 icx      | 0 icx

        self.set_revision(Revision.MULTIPLE_UNSTAKE.value)

        # unstake all staked value
        tx = self.create_set_stake_tx(from_=self._accounts[0], value=0)
        tx_results: List['TransactionResult'] = self.process_confirm_block_tx(tx_list=[tx])
        fee = tx_results[1].step_used * tx_results[1].step_price
        expected_balance = self._accounts[0].balance - fee
        self.assertEqual(expected_balance, self.get_balance(self._accounts[0]))
        self._accounts[0].balance = expected_balance

        res: dict = self.get_stake(self._accounts[0])
        remaining_blocks: int = res["unstakes"][0]["remainingBlocks"]
        unstake_block_height: int = res["unstakes"][0]["unstakeBlockHeight"]
        self.make_empty_blocks(remaining_blocks + 1)
        # Balance | Stake   | UnStake    | Expired_icx
        # 50 icx  | 0 icx   | 100 icx(e) | 100 icx

        # new format
        db_info: dict = self._get_account_info(self._accounts[0])
        coin_part: 'CoinPart' = db_info["coin"]
        stake_part: 'StakePart' = db_info["stake"]
        self.assertEqual(CoinPartFlag.HAS_UNSTAKE, coin_part._flags)
        self.assertEqual(0, stake_part._stake)
        self.assertEqual(expired_icx, stake_part._unstakes_info[0][0])
        self.assertEqual(unstake_block_height, stake_part._unstakes_info[0][1])

        tx_results: List["TransactionResult"] = self.set_delegation(
            from_=self._accounts[0],
            origin_delegations=[
                (
                    self._accounts[0],
                    0
                )
            ]
        )
        fee = tx_results[1].step_used * tx_results[1].step_price
        expected_balance = self._accounts[0].balance - fee + expired_icx
        self.assertEqual(expected_balance, self.get_balance(self._accounts[0]))
        self._accounts[0].balance = expected_balance

        # new format
        db_info: dict = self._get_account_info(self._accounts[0])
        coin_part: 'CoinPart' = db_info["coin"]
        stake_part: 'StakePart' = db_info["stake"]
        self.assertEqual(CoinPartFlag.NONE, coin_part._flags)
        self.assertEqual(0, stake_part._stake)
        self.assertEqual(expired_icx, stake_part._unstakes_info[0][0])
        self.assertEqual(unstake_block_height, stake_part._unstakes_info[0][1])

        data: list = [
            {
                "address": str(self._accounts[0].address),
                "total_unstake": stake_part._stake + stake_part._total_unstake(),
                "old_unstake_format": False,
                "unstakes": [
                    [
                        stake_part._unstakes_info[0][0],
                        stake_part._unstakes_info[0][1]
                    ],
                ]
            },
        ]
        targets: List[Target] = [Target.from_dict(i) for i in data]
        patcher = UnstakePatcher(targets=targets)
        with patch.object(UnstakePatcher, 'from_path') as from_path_mock:
            from_path_mock.return_value = patcher

            self.set_revision(Revision.FIX_BALANCE_BUG.value)
            self._check_unstake_patch()

    def test_new_format_multi_1_of_2_expired(self):
        self.init_decentralized()
        self.init_inv()

        init_balance: int = 150 * ICX_IN_LOOP
        stake: int = 100 * ICX_IN_LOOP
        # gain 150 icx
        self.distribute_icx(
            accounts=self._accounts[:1],
            init_balance=init_balance
        )

        self._accounts[0].balance = init_balance
        # Balance | Stake   | UnStake    | Expired_icx
        # 150 icx | 0 icx   | 0 icx      | 0 icx

        # set stake
        expired_icx: int = stake // 2
        tx = self.create_set_stake_tx(from_=self._accounts[0], value=stake)
        tx_results: List['TransactionResult'] = self.process_confirm_block_tx(tx_list=[tx])
        fee = tx_results[1].step_used * tx_results[1].step_price
        expected_balance = self._accounts[0].balance - stake - fee
        self.assertEqual(expected_balance, self.get_balance(self._accounts[0]))
        self._accounts[0].balance = expected_balance

        # Balance | Stake   | UnStake    | Expired_icx
        # 50 icx  | 100 icx | 0 icx      | 0 icx

        self.set_revision(Revision.MULTIPLE_UNSTAKE.value)

        # unstake 1/2 of staked value
        unstake = stake // 2
        tx = self.create_set_stake_tx(from_=self._accounts[0], value=unstake)
        tx_results: List['TransactionResult'] = self.process_confirm_block_tx(tx_list=[tx])
        fee = tx_results[1].step_used * tx_results[1].step_price
        expected_balance = self._accounts[0].balance - fee
        self.assertEqual(expected_balance, self.get_balance(self._accounts[0]))
        self._accounts[0].balance = expected_balance

        # make empty some blocks for term between unstakes
        self.make_empty_blocks(5)

        # unstake the rest of staked value
        tx = self.create_set_stake_tx(from_=self._accounts[0], value=0)
        tx_results: List['TransactionResult'] = self.process_confirm_block_tx(tx_list=[tx])
        fee = tx_results[1].step_used * tx_results[1].step_price
        expected_balance = self._accounts[0].balance - fee
        self.assertEqual(expected_balance, self.get_balance(self._accounts[0]))
        self._accounts[0].balance = expected_balance

        res: dict = self.get_stake(self._accounts[0])
        unstakes_info = res["unstakes"]
        first_slot_remaining: int = unstakes_info[0]["remainingBlocks"]
        self.make_empty_blocks(first_slot_remaining + 1)
        # Balance | Stake   | UnStake    | Expired_icx
        # 50 icx  | 0 icx   | 50 icx(e) | 50 icx

        # new format
        db_info: dict = self._get_account_info(self._accounts[0])
        coin_part: 'CoinPart' = db_info["coin"]
        stake_part: 'StakePart' = db_info["stake"]
        self.assertEqual(CoinPartFlag.HAS_UNSTAKE, coin_part._flags)
        self.assertEqual(0, stake_part._stake)
        expired_unstake = 0
        current_block = self.get_last_block().height
        for i, unstake_info in enumerate(stake_part._unstakes_info):
            self.assertEqual(unstakes_info[i]["unstakeBlockHeight"], unstake_info[1])
            if unstake_info[1] < current_block:
                expired_unstake += unstake_info[0]
        self.assertEqual(expired_icx, expired_unstake)

        tx_results: List["TransactionResult"] = self.set_delegation(
            from_=self._accounts[0],
            origin_delegations=[
                (
                    self._accounts[0],
                    0
                )
            ]
        )
        fee = tx_results[1].step_used * tx_results[1].step_price
        expected_balance = self._accounts[0].balance - fee + expired_icx
        self.assertEqual(expected_balance, self.get_balance(self._accounts[0]))
        self._accounts[0].balance = expected_balance

        # new format
        db_info: dict = self._get_account_info(self._accounts[0])
        coin_part: 'CoinPart' = db_info["coin"]
        stake_part: 'StakePart' = db_info["stake"]
        self.assertEqual(CoinPartFlag.NONE, coin_part._flags)
        self.assertEqual(0, stake_part._stake)
        expected_expired_icx = stake_part._unstakes_info[0][0]
        self.assertEqual(expected_expired_icx, expired_icx)
        self.assertEqual(1, len(stake_part._unstakes_info))
        self.assertEqual(expired_icx, stake_part._unstakes_info[0][0])
        self.assertEqual(unstakes_info[-1]["unstakeBlockHeight"], stake_part._unstakes_info[0][1])

        data: list = [
            {
                "address": str(self._accounts[0].address),
                "total_unstake": stake_part._stake + stake_part._total_unstake(),
                "old_unstake_format": False,
                "unstakes": [
                    [
                        stake_part._unstakes_info[0][0],
                        stake_part._unstakes_info[0][1]
                    ],
                ]
            },
        ]
        targets: List[Target] = [Target.from_dict(i) for i in data]
        patcher = UnstakePatcher(targets=targets)
        with patch.object(UnstakePatcher, 'from_path') as from_path_mock:
            from_path_mock.return_value = patcher

            self.set_revision(Revision.FIX_BALANCE_BUG.value)
            self._check_unstake_patch()

    def test_new_format_multi_2_of_2_expired(self):
        self.init_decentralized()
        self.init_inv()

        init_balance: int = 150 * ICX_IN_LOOP
        stake: int = 100 * ICX_IN_LOOP
        # gain 150 icx
        self.distribute_icx(
            accounts=self._accounts[:1],
            init_balance=init_balance
        )

        self._accounts[0].balance = init_balance
        # Balance | Stake   | UnStake    | Expired_icx
        # 150 icx | 0 icx   | 0 icx      | 0 icx

        # set stake
        expired_icx: int = stake
        tx = self.create_set_stake_tx(from_=self._accounts[0], value=stake)
        tx_results: List['TransactionResult'] = self.process_confirm_block_tx(tx_list=[tx])
        fee = tx_results[1].step_used * tx_results[1].step_price
        expected_balance = self._accounts[0].balance - stake - fee
        self.assertEqual(expected_balance, self.get_balance(self._accounts[0]))
        self._accounts[0].balance = expected_balance

        # Balance | Stake   | UnStake    | Expired_icx
        # 50 icx  | 100 icx | 0 icx      | 0 icx

        self.set_revision(Revision.MULTIPLE_UNSTAKE.value)

        # unstake 1/2 of staked value
        unstake = stake // 2
        tx = self.create_set_stake_tx(from_=self._accounts[0], value=unstake)
        tx_results: List['TransactionResult'] = self.process_confirm_block_tx(tx_list=[tx])
        fee = tx_results[1].step_used * tx_results[1].step_price
        expected_balance = self._accounts[0].balance - fee
        self.assertEqual(expected_balance, self.get_balance(self._accounts[0]))
        self._accounts[0].balance = expected_balance

        # unstake the rest of staked value
        tx = self.create_set_stake_tx(from_=self._accounts[0], value=0)
        tx_results: List['TransactionResult'] = self.process_confirm_block_tx(tx_list=[tx])
        fee = tx_results[1].step_used * tx_results[1].step_price
        expected_balance = self._accounts[0].balance - fee
        self.assertEqual(expected_balance, self.get_balance(self._accounts[0]))
        self._accounts[0].balance = expected_balance

        res: dict = self.get_stake(self._accounts[0])
        unstakes_info = res["unstakes"]
        last_slot_remaining: int = unstakes_info[-1]["remainingBlocks"]
        self.make_empty_blocks(last_slot_remaining + 1)
        # Balance | Stake   | UnStake    | Expired_icx
        # 50 icx  | 0 icx   | 100 icx(e) | 100 icx

        # new format
        db_info: dict = self._get_account_info(self._accounts[0])
        coin_part: 'CoinPart' = db_info["coin"]
        stake_part: 'StakePart' = db_info["stake"]
        self.assertEqual(CoinPartFlag.HAS_UNSTAKE, coin_part._flags)
        self.assertEqual(0, stake_part._stake)
        expected_expired_icx = 0
        for i, unstake_info in enumerate(stake_part._unstakes_info):
            self.assertEqual(unstakes_info[i]["unstakeBlockHeight"], unstake_info[1])
            expected_expired_icx += unstake_info[0]
        self.assertEqual(expired_icx, expected_expired_icx)

        tx_results: List["TransactionResult"] = self.set_delegation(
            from_=self._accounts[0],
            origin_delegations=[
                (
                    self._accounts[0],
                    0
                )
            ]
        )
        fee = tx_results[1].step_used * tx_results[1].step_price
        expected_balance = self._accounts[0].balance - fee + expired_icx
        self.assertEqual(expected_balance, self.get_balance(self._accounts[0]))
        self._accounts[0].balance = expected_balance

        # new format
        db_info: dict = self._get_account_info(self._accounts[0])
        coin_part: 'CoinPart' = db_info["coin"]
        stake_part: 'StakePart' = db_info["stake"]
        self.assertEqual(CoinPartFlag.NONE, coin_part._flags)
        self.assertEqual(0, stake_part._stake)
        expected_expired_icx = 0
        for i, unstake_info in enumerate(stake_part._unstakes_info):
            self.assertEqual(unstakes_info[i]["unstakeBlockHeight"], unstake_info[1])
            expected_expired_icx += unstake_info[0]
        self.assertEqual(expired_icx, expected_expired_icx)

        data: list = [
            {
                "address": str(self._accounts[0].address),
                "total_unstake": stake_part._stake + stake_part._total_unstake(),
                "old_unstake_format": False,
                "unstakes": [
                    [
                        stake_part._unstakes_info[0][0],
                        stake_part._unstakes_info[0][1]
                    ],
                    [
                        stake_part._unstakes_info[1][0],
                        stake_part._unstakes_info[1][1]
                    ],
                ]
            },
        ]
        targets: List[Target] = [Target.from_dict(i) for i in data]
        patcher = UnstakePatcher(targets=targets)
        with patch.object(UnstakePatcher, 'from_path') as from_path_mock:
            from_path_mock.return_value = patcher
            self.set_revision(Revision.FIX_BALANCE_BUG.value)
            self._check_unstake_patch()

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

    def _check_unstake_patch(self):
        get_stake_info: dict = self.get_stake(self._accounts[0])
        self.assertNotIn("unstake", get_stake_info)
        db_info: dict = self._get_account_info(self._accounts[0])
        unstake: int = db_info["stake"]._unstake
        unstake_block_height: int = db_info["stake"]._unstake_block_height
        unstakes_info: list = db_info["stake"]._unstakes_info
        flag: CoinPartFlag = db_info["coin"].flags
        self.assertEqual(CoinPartFlag.NONE, flag)
        self.assertEqual(0, unstake)
        self.assertEqual(0, unstake_block_height)
        self.assertEqual(0, len(unstakes_info))


class TestIISSUnStakePatcher(TestIISSBase):
    PATH = os.path.join(os.path.dirname(__file__), "./invalid_expired_unstakes/test.json")

    def _make_init_config(self) -> dict:
        config: dict = super()._make_init_config()
        config[ConfigKey.INVALID_EXPIRED_UNSTAKES_PATH] = self.PATH
        return config

    def test_loader(self):
        self.init_decentralized()
        self.init_inv()
        self.set_revision(Revision.FIX_BALANCE_BUG.value)

        expected_data: dict = {
            "block_height": 100,
            "target_count": 3,
            "total_unstake": 50000,
            "targets": [
                {
                    "address": "hx001977f6b796a8f0e9c6b6ce3ae1c1a6851099e4",
                    "total_unstake": 20000,
                    "old_unstake_format": False,
                    "unstakes": [
                        [
                            10000,
                            5
                        ],
                        [
                            10000,
                            6
                        ]
                    ]
                },
                {
                    "address": "hx00aa98611e6993c907dcd9abf3e6f647fb641229",
                    "total_unstake": 10000,
                    "old_unstake_format": True,
                    "unstakes": [
                        [
                            10000,
                            10
                        ]
                    ]
                },
                {
                    "address": "hx0108a796980c03733ab3809f7a2be80ace2ceef3",
                    "total_unstake": 20000,
                    "old_unstake_format": False,
                    "unstakes": [
                        [
                            10000,
                            1
                        ],
                        [
                            10000,
                            2
                        ]
                    ]
                }
            ]
        }
        with open(self.PATH, "r") as f:
            actual_text = f.read()
            actual_data: dict = json.loads(actual_text)
        self.assertEqual(expected_data, actual_data)
