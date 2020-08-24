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
from iconservice.base.exception import AccessDeniedException
from iconservice.icon_constant import ICX_IN_LOOP
from tests.integrate_test.iiss.test_iiss_base import TestIISSBase

if TYPE_CHECKING:
    pass


class TestLock(TestIISSBase):
    def setUp(self):
        super().setUp()
        self.init_decentralized()

    def test_lock(self):
        self.update_governance(
            version="1_1_1",
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
                "address": str(self._accounts[0].address),
                "lock": hex(1)
            },
            expected_status=True
        )

        with self.assertRaises(AccessDeniedException) as e:
            self.get_balance(account=from_)
        self.assertEqual(e.exception.args[0], f"Lock Account: {self._accounts[0].address}")

        with self.assertRaises(AccessDeniedException) as e:
            tx = self.create_transfer_icx_tx(
                from_=from_,
                to_=self._admin,
                value=1 * ICX_IN_LOOP,
            )
            self.estimate_step(tx)
        self.assertEqual(e.exception.args[0], f"Lock Account: {self._accounts[0].address}")

        with self.assertRaises(AccessDeniedException) as e:
            tx = self.create_transfer_icx_tx(
                from_=from_,
                to_=self._admin,
                value=1 * ICX_IN_LOOP
            )
            self.estimate_step(tx)
        self.assertEqual(e.exception.args[0], f"Lock Account: {self._accounts[0].address}")

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

        # unlock
        self.score_call(
            from_=self._admin,
            to_=GOVERNANCE_SCORE_ADDRESS,
            func_name="lockAccount",
            params={
                "address": str(self._accounts[0].address),
                "lock": hex(0)
            },
            expected_status=True
        )

        self.get_balance(account=from_)

        tx = self.create_transfer_icx_tx(
            from_=from_,
            to_=self._admin,
            value=1 * ICX_IN_LOOP,
        )
        self.estimate_step(tx)

        tx = self.create_transfer_icx_tx(
            from_=from_,
            to_=self._admin,
            value=1 * ICX_IN_LOOP
        )
        self.estimate_step(tx)

        self.transfer_icx(
            from_=from_,
            to_=self._admin,
            value=1 * ICX_IN_LOOP,
            disable_pre_validate=True,
            expected_status=True
        )

        self.set_stake(from_=from_, value=1 * ICX_IN_LOOP)
