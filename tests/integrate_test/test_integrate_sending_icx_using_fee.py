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
from typing import TYPE_CHECKING, List

from iconservice.base.address import Address
from iconservice.icon_constant import ConfigKey, FIXED_FEE, ICX_IN_LOOP
from iconservice.icon_constant import REVISION
from tests import create_address
from tests.integrate_test.test_integrate_base import TestIntegrateBase

if TYPE_CHECKING:
    from iconservice.iconscore.icon_score_result import TransactionResult


class TestIntegrateSendingIcx(TestIntegrateBase):

    def _make_init_config(self) -> dict:
        return {ConfigKey.SERVICE: {ConfigKey.SERVICE_FEE: True}}

    def test_fail_icx_validator(self):
        icx = 3 * FIXED_FEE
        self.transfer_icx(from_=self._admin,
                          to_=self._accounts[0],
                          value=icx)

        self.assertEqual(icx, self.get_balance(self._accounts[0]))

        tx1 = self.create_transfer_icx_tx(from_=self._accounts[0],
                                          to_=self._accounts[1],
                                          value=1 * FIXED_FEE,
                                          support_v2=True)
        tx2 = self.create_transfer_icx_tx(from_=self._accounts[0],
                                          to_=self._accounts[1],
                                          value=1 * FIXED_FEE,
                                          support_v2=True)
        tx_results: List['TransactionResult'] = self.process_confirm_block_tx([tx1, tx2])

        self.assertEqual(tx_results[0].step_used, 1_000_000)
        # wrong!
        self.assertEqual(tx_results[1].step_used, 0)

    def test_fix_icx_validator(self):
        self.update_governance()
        self.set_revision(REVISION.THREE.value)

        icx = 3 * FIXED_FEE
        self.transfer_icx(from_=self._admin,
                          to_=self._accounts[0],
                          value=icx)

        self.assertEqual(icx, self.get_balance(self._accounts[0]))

        tx1 = self.create_transfer_icx_tx(from_=self._accounts[0],
                                          to_=self._accounts[1],
                                          value=1 * FIXED_FEE,
                                          support_v2=True)
        tx2 = self.create_transfer_icx_tx(from_=self._accounts[0],
                                          to_=self._accounts[1],
                                          value=1 * FIXED_FEE,
                                          support_v2=True)

        prev_block, hash_list = self.make_and_req_block([tx1, tx2])
        self._write_precommit_state(prev_block)

        tx_results: List['TransactionResult'] = self.get_tx_results(hash_list)
        self.assertEqual(tx_results[0].step_used, 1_000_000)
        self.assertEqual(tx_results[1].status, 0)

    def test_send_icx_without_data(self):
        step_price = 10 ** 10
        default_step_cost = 100_000
        input_step_cost = 200
        value = 1 * ICX_IN_LOOP

        self.update_governance()

        for revision in range(REVISION.TWO.value, REVISION.LATEST.value + 1):
            self.set_revision(revision)

            # Create a new to address every block
            balance0: int = self.get_balance(self._admin)
            self.assertTrue(balance0 > 0)

            # Check "to" address balance. It should be 0
            to: 'Address' = create_address()
            to_balance: int = self.get_balance(to)
            self.assertEqual(0, to_balance)

            if revision == REVISION.THREE.value:
                # Check backward compatibility on TestNet Database
                # step_used increases by input_step_cost * len(json.dumps(None))
                # because of None parameter handling error on get_input_data_size()
                step_limit = default_step_cost + input_step_cost * len(json.dumps(None))
                self.assertEqual(default_step_cost + input_step_cost * 4, step_limit)
            else:
                step_limit = default_step_cost

            tx_results: List['TransactionResult'] = self.transfer_icx(from_=self._admin,
                                                                      to_=to,
                                                                      value=value,
                                                                      step_limit=step_limit)
            self.assertEqual(step_limit, tx_results[0].step_used)
            self.assertEqual(to, tx_results[0].to)
            self.assertIsNone(tx_results[0].failure)
            self.assertIsNone(tx_results[0].score_address)

            fee: int = tx_results[0].step_used * step_price
            self.assertTrue(fee > 0)

            to_balance: int = self._query({"address": to}, 'icx_getBalance')
            self.assertEqual(value, to_balance)

            balance: int = self.get_balance(self._admin)
            self.assertEqual(balance0, balance + value + fee)
