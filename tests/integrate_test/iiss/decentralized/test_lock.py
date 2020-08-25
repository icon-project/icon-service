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

from iconservice.base.address import GOVERNANCE_SCORE_ADDRESS
from iconservice.base.exception import AccessDeniedException, IconScoreException
from iconservice.icon_constant import ICX_IN_LOOP
from iconservice.iconscore.icon_score_event_log import EventLog
from tests.integrate_test.iiss.test_iiss_base import TestIISSBase

if TYPE_CHECKING:
    pass


class TestLock(TestIISSBase):
    def setUp(self):
        super().setUp()
        self.init_decentralized()

    def test_lock(self):
        self.update_governance(
            version="1_1_2",
            expected_status=True,
            root_path="sample_builtin_for_tests"
        )

        from_ = self._accounts[0]
        self.transfer_icx(from_=self._admin, to_=self._accounts[0], value=100 * ICX_IN_LOOP)

        self.score_call(
            from_=self._admin,
            to_=GOVERNANCE_SCORE_ADDRESS,
            func_name="lockAccount",
            params={
                "addresses": [str(self._accounts[0].address)],
                "locks": [hex(1)]
            },
            expected_status=True
        )

        # pass query
        self.get_balance(account=from_)

        # pass estimate
        tx = self.create_transfer_icx_tx(
            from_=from_,
            to_=self._admin,
            value=1 * ICX_IN_LOOP,
            disable_pre_validate=True
        )
        self.estimate_step(tx)

        tx_results: list = self.transfer_icx(
            from_=from_,
            to_=self._admin,
            value=1 * ICX_IN_LOOP,
            disable_pre_validate=True,
            expected_status=False
        )
        self.assertEqual(tx_results[1].failure.message, f"Lock Account: {self._accounts[0].address}")

        with self.assertRaises(AccessDeniedException) as e:
            self.set_stake(from_=from_, value=1 * ICX_IN_LOOP)
        self.assertEqual(e.exception.args[0], f"Lock Account: {self._accounts[0].address}")

        delegations: list = [(self._accounts[i], 0) for i in range(10)]
        with self.assertRaises(AccessDeniedException) as e:
            self.set_delegation(from_=self._accounts[0], origin_delegations=delegations)
            self.assertEqual(e.exception.args[0], f"Lock Account: {self._accounts[0].address}")

        # unlock
        self.score_call(
            from_=self._admin,
            to_=GOVERNANCE_SCORE_ADDRESS,
            func_name="lockAccount",
            params={
                "addresses": [str(self._accounts[0].address)],
                "locks": [hex(0)]
            },
            expected_status=True
        )

        self.transfer_icx(
            from_=from_,
            to_=self._admin,
            value=1 * ICX_IN_LOOP,
            disable_pre_validate=True,
            expected_status=True
        )

        self.set_stake(from_=from_, value=1 * ICX_IN_LOOP)

    def test_lock_multiple(self):
        multi_cnt: int = 10
        self.update_governance(
            version="1_1_2",
            expected_status=True,
            root_path="sample_builtin_for_tests"
        )

        for i in range(multi_cnt):
            self.transfer_icx(from_=self._admin, to_=self._accounts[i], value=100 * ICX_IN_LOOP)

        addresses: list = [str(self._accounts[i].address) for i in range(multi_cnt)]
        locks: list = [hex(1) for _ in range(multi_cnt)]

        tx_results: list = self.score_call(
            from_=self._admin,
            to_=GOVERNANCE_SCORE_ADDRESS,
            func_name="lockAccount",
            params={
                "addresses": addresses,
                "locks": locks
            },
            expected_status=True
        )

        for i in range(multi_cnt):
            event_log: 'EventLog' = tx_results[1].event_logs[i]
            self.assertEqual(GOVERNANCE_SCORE_ADDRESS, event_log.score_address)
            self.assertEqual(f'AccountLocked(Address,bool)', event_log.indexed[0])
            self.assertEqual(self._accounts[i].address, event_log.indexed[1])
            self.assertEqual(True, event_log.data[0])

        for i in range(multi_cnt):
            tx_results: list = self.transfer_icx(
                from_=self._accounts[i],
                to_=self._admin,
                value=1 * ICX_IN_LOOP,
                disable_pre_validate=True,
                expected_status=False
            )
            self.assertEqual(tx_results[1].failure.message, f"Lock Account: {self._accounts[i].address}")

        for i in range(multi_cnt):
            with self.assertRaises(AccessDeniedException) as e:
                self.set_stake(from_=self._accounts[i], value=1 * ICX_IN_LOOP)
            self.assertEqual(e.exception.args[0], f"Lock Account: {self._accounts[i].address}")

        for i in range(multi_cnt):
            delegations: list = [(self._accounts[i], 0) for i in range(multi_cnt)]
            with self.assertRaises(AccessDeniedException) as e:
                self.set_delegation(from_=self._accounts[i], origin_delegations=delegations)
            self.assertEqual(e.exception.args[0], f"Lock Account: {self._accounts[i].address}")

        addresses: list = [str(self._accounts[i].address) for i in range(multi_cnt)]
        locks: list = [hex(0) for _ in range(multi_cnt)]

        # unlock
        self.score_call(
            from_=self._admin,
            to_=GOVERNANCE_SCORE_ADDRESS,
            func_name="lockAccount",
            params={
                "addresses": addresses,
                "locks": locks
            },
            expected_status=True
        )

        for i in range(multi_cnt):
            self.transfer_icx(
                from_=self._accounts[i],
                to_=self._admin,
                value=1 * ICX_IN_LOOP,
                disable_pre_validate=True,
                expected_status=True
            )

        for i in range(multi_cnt):
            self.set_stake(from_=self._accounts[i], value=1 * ICX_IN_LOOP)

    def test_invalid_access(self):
        multi_cnt: int = 10

        self.update_governance(
            version="1_1_2",
            expected_status=True,
            root_path="sample_builtin_for_tests"
        )

        for i in range(multi_cnt):
            self.transfer_icx(from_=self._admin, to_=self._accounts[i], value=100 * ICX_IN_LOOP)

        addresses: list = [str(self._accounts[i].address) for i in range(multi_cnt)]
        locks: list = [hex(1) for _ in range(multi_cnt)]

        tx_results: list = self.score_call(
            from_=self._accounts[0],
            to_=GOVERNANCE_SCORE_ADDRESS,
            func_name="lockAccount",
            params={
                "addresses": addresses,
                "locks": locks
            },
            expected_status=False
        )

        self.assertEqual(tx_results[1].failure.message, f"No permission: {str(self._accounts[0].address)}")

    def test_overflow_account(self):
        multi_cnt: int = 10 + 1

        self.update_governance(
            version="1_1_2",
            expected_status=True,
            root_path="sample_builtin_for_tests"
        )

        for i in range(multi_cnt):
            self.transfer_icx(from_=self._admin, to_=self._accounts[i], value=100 * ICX_IN_LOOP)

        addresses: list = [str(self._accounts[i].address) for i in range(multi_cnt)]
        locks: list = [hex(1) for _ in range(multi_cnt)]

        tx_results: list = self.score_call(
            from_=self._admin,
            to_=GOVERNANCE_SCORE_ADDRESS,
            func_name="lockAccount",
            params={
                "addresses": addresses,
                "locks": locks
            },
            expected_status=False
        )

        self.assertEqual(tx_results[1].failure.message, f"Too many addresses")

    def test_mismatch_account(self):
        multi_cnt: int = 10 + 1

        self.update_governance(
            version="1_1_2",
            expected_status=True,
            root_path="sample_builtin_for_tests"
        )

        for i in range(multi_cnt):
            self.transfer_icx(from_=self._admin, to_=self._accounts[i], value=100 * ICX_IN_LOOP)

        addresses: list = [str(self._accounts[i].address) for i in range(multi_cnt)]
        invalid_locks: list = [hex(1)]

        tx_results: list = self.score_call(
            from_=self._admin,
            to_=GOVERNANCE_SCORE_ADDRESS,
            func_name="lockAccount",
            params={
                "addresses": addresses,
                "locks": invalid_locks
            },
            expected_status=False
        )

        self.assertEqual(tx_results[1].failure.message, f"Argument number mismatch")

    def test_query_locked_accounts(self):
        multi_cnt: int = 10

        self.update_governance(
            version="1_1_2",
            expected_status=True,
            root_path="sample_builtin_for_tests"
        )

        for i in range(multi_cnt):
            self.transfer_icx(from_=self._admin, to_=self._accounts[i], value=100 * ICX_IN_LOOP)

        addresses: list = [str(self._accounts[i].address) for i in range(multi_cnt)]
        locks: list = [hex(1) for _ in range(multi_cnt)]

        self.score_call(
            from_=self._admin,
            to_=GOVERNANCE_SCORE_ADDRESS,
            func_name="lockAccount",
            params={
                "addresses": addresses,
                "locks": locks
            },
            expected_status=True
        )

        ret = self.query_score(
            from_=self._admin.address,
            to_=GOVERNANCE_SCORE_ADDRESS,
            func_name="getLockedAccounts",
            params={}
        )
        self.assertEqual([self._accounts[i].address for i in range(multi_cnt)], ret)

        addresses: list = [str(self._accounts[i].address) for i in range(multi_cnt)]
        locks: list = [hex(0) for _ in range(multi_cnt)]

        self.score_call(
            from_=self._admin,
            to_=GOVERNANCE_SCORE_ADDRESS,
            func_name="lockAccount",
            params={
                "addresses": addresses,
                "locks": locks
            },
            expected_status=True
        )

        ret = self.query_score(
            from_=self._admin.address,
            to_=GOVERNANCE_SCORE_ADDRESS,
            func_name="getLockedAccounts",
            params={}
        )
        self.assertEqual([], ret)

    def test_locked_account_send_tx(self):
        self.update_governance(
            version="1_1_2",
            expected_status=True,
            root_path="sample_builtin_for_tests"
        )

        from_ = self._accounts[0]
        self.transfer_icx(from_=self._admin, to_=self._accounts[0], value=100 * ICX_IN_LOOP)

        self.score_call(
            from_=self._admin,
            to_=GOVERNANCE_SCORE_ADDRESS,
            func_name="lockAccount",
            params={
                "addresses": [str(self._accounts[0].address)],
                "locks": [hex(1)]
            },
            expected_status=True
        )

        tx_results: list = self.transfer_icx(
            from_=from_,
            to_=self._admin,
            value=1 * ICX_IN_LOOP,
            disable_pre_validate=True,
            expected_status=False
        )
        self.assertEqual(tx_results[1].failure.message, f"Lock Account: {self._accounts[0].address}")

        tx = self.create_set_stake_tx(from_=from_, value=1 * ICX_IN_LOOP, pre_validation_enabled=False)
        tx_results: list = self.process_confirm_block_tx([tx], expected_status=False)
        self.assertEqual(tx_results[1].failure.message, f"Lock Account: {self._accounts[0].address}")

        delegations: list = [(self._accounts[i], 0) for i in range(10)]
        tx = self.create_set_delegation_tx(from_=from_, origin_delegations=delegations, pre_validation_enabled=False)
        tx_results: list = self.process_confirm_block_tx([tx], expected_status=False)
        self.assertEqual(tx_results[1].failure.message, f"Lock Account: {self._accounts[0].address}")

        tx = self.create_claim_tx(from_=from_, pre_validation_enabled=False)
        tx_results: list = self.process_confirm_block_tx([tx], expected_status=False)
        self.assertEqual(tx_results[1].failure.message, f"Lock Account: {self._accounts[0].address}")

        tx = self.create_register_prep_tx(from_=from_, pre_validation_enabled=False)
        tx_results: list = self.process_confirm_block_tx([tx], expected_status=False)
        self.assertEqual(tx_results[1].failure.message, f"Lock Account: {self._accounts[0].address}")

        tx = self.create_deploy_score_tx(
            score_root="sample_scores",
            score_name="sample_array_db",
            from_=self._accounts[0],
            to_=GOVERNANCE_SCORE_ADDRESS,
            pre_validation_enabled=False
        )
        tx_results: list = self.process_confirm_block_tx([tx], expected_status=False)
        self.assertEqual(tx_results[1].failure.message, f"Lock Account: {self._accounts[0].address}")
