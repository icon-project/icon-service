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
import unittest

from iconservice.base.address import GOVERNANCE_SCORE_ADDRESS, Address, AddressPrefix
from iconservice.icon_constant import ConfigKey
from iconservice.icon_constant import REVISION_2, REVISION_3, LATEST_REVISION
from iconservice.iconscore.icon_score_result import TransactionResult
from tests.integrate_test.test_integrate_base import TestIntegrateBase


class TestIntegrateSendingIcx(TestIntegrateBase):

    def _make_init_config(self) -> dict:
        return {ConfigKey.SERVICE: {ConfigKey.SERVICE_FEE: True}}

    def _update_governance(self, version_path: str = "0_0_4"):
        tx = self._make_deploy_tx(
            "test_builtin",
            f"{version_path}/governance",
            self._admin,
            GOVERNANCE_SCORE_ADDRESS
        )
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)

        self._governance_updated = True

    def _set_revision_to_governance(self, revision: int, name: str):
        self.assertTrue(self._governance_updated)

        tx = self._make_score_call_tx(
            self._admin,
            GOVERNANCE_SCORE_ADDRESS,
            "setRevision",
            {"code": hex(revision), "name": name}
        )
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)

    def test_fail_icx_validator(self):
        icx = 3 * 10 ** 16
        tx = self._make_icx_send_tx(self._genesis, self._addr_array[0], icx, step_limit=1 * 10 ** 6)
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)

        response = self._query({"address": self._addr_array[0]}, 'icx_getBalance')
        self.assertEqual(icx, response)

        tx1 = self._make_icx_send_tx(self._addr_array[0], self._addr_array[1], 1 * 10 ** 16, support_v2=True)
        tx2 = self._make_icx_send_tx(self._addr_array[0], self._addr_array[1], 1 * 10 ** 16, support_v2=True)

        prev_block, tx_results = self._make_and_req_block([tx1, tx2])
        self._write_precommit_state(prev_block)

        self.assertEqual(tx_results[0].status, 1)
        self.assertEqual(tx_results[0].step_used, 1_000_000)

        self.assertEqual(tx_results[1].status, 1)
        # wrong!
        self.assertEqual(tx_results[1].step_used, 0)

    def test_fix_icx_validator(self):
        self._update_governance()
        self._set_revision_to_governance(REVISION_3, "1.1.2.7")

        icx = 3 * 10 ** 16
        tx = self._make_icx_send_tx(self._genesis, self._addr_array[0], icx, step_limit=1 * 10 ** 6)
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)

        response = self._query({"address": self._addr_array[0]}, 'icx_getBalance')
        self.assertEqual(icx, response)

        tx1 = self._make_icx_send_tx(self._addr_array[0], self._addr_array[1], 1 * 10 ** 16, support_v2=True)
        tx2 = self._make_icx_send_tx(self._addr_array[0], self._addr_array[1], 1 * 10 ** 16, support_v2=True)

        prev_block, tx_results = self._make_and_req_block([tx1, tx2])
        self._write_precommit_state(prev_block)

        self.assertEqual(tx_results[0].status, 1)
        self.assertEqual(tx_results[0].step_used, 1_000_000)

        self.assertEqual(tx_results[1].status, 0)

    def test_send_icx_without_data(self):
        step_price = 10 ** 10
        default_step_cost = 100_000
        input_step_cost = 200
        value = 10 ** 18

        self._update_governance("0_0_6")

        for revision in range(REVISION_2, LATEST_REVISION + 1):
            self._set_revision_to_governance(revision, name="")

            # Create a new to address every block
            to = Address.from_data(AddressPrefix.EOA, f"to{revision}".encode())

            genesis_balance0: int = self._query({"address": self._genesis}, 'icx_getBalance')
            self.assertTrue(genesis_balance0 > 0)

            # Check "to" address balance. It should be 0
            to_balance0: int = self._query({"address": to}, 'icx_getBalance')
            self.assertEqual(0, to_balance0)

            if revision == REVISION_3:
                # Check backward compatibility on TestNet Database
                # step_used increases by input_step_cost * len(json.dumps(None))
                # because of None parameter handling error on get_input_data_size()
                step_limit = default_step_cost + input_step_cost * len(json.dumps(None))
                self.assertEqual(default_step_cost + input_step_cost * 4, step_limit)
            else:
                step_limit = default_step_cost

            tx = self._make_icx_send_tx(self._genesis, to, value=value, step_limit=step_limit)
            prev_block, tx_results = self._make_and_req_block([tx])
            self._write_precommit_state(prev_block)

            tx_result: 'TransactionResult' = tx_results[0]
            self.assertEqual(1, tx_result.status)
            self.assertEqual(step_limit, tx_result.step_used)
            self.assertEqual(to, tx_result.to)
            self.assertIsNone(tx_result.failure)
            self.assertIsNone(tx_result.score_address)

            fee: int = tx_result.step_used * step_price
            self.assertTrue(fee > 0)

            to_balance: int = self._query({"address": to}, 'icx_getBalance')
            self.assertEqual(value, to_balance)

            genesis_balance1: int = self._query({"address": self._genesis}, 'icx_getBalance')
            self.assertEqual(genesis_balance0, genesis_balance1 + value + fee)


if __name__ == '__main__':
    unittest.main()
