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

from iconservice.icon_constant import Revision, PREP_MAIN_PREPS, ICX_IN_LOOP, ConfigKey
from tests.integrate_test.iiss.test_iiss_base import TestIISSBase


class TestChangedMinimumDelegate(TestIISSBase):
    def _make_init_config(self) -> dict:
        config: dict = super()._make_init_config()
        config[ConfigKey.DECENTRALIZE_TRIGGER] = 0
        return config

    def test_decentralized_minimum_delegation_set_zero(self):
        self.update_governance()
        # set Revision REV_IISS
        self.set_revision(Revision.IISS.value)

        # distribute icx for register PREP_MAIN_PREPS ~ PREP_MAIN_PREPS + PREP_MAIN_PREPS - 1
        self.distribute_icx(
            accounts=self._accounts[:PREP_MAIN_PREPS], init_balance=3000 * ICX_IN_LOOP
        )

        # register PRep
        tx_list: list = []
        for i, address in enumerate(self._accounts[:PREP_MAIN_PREPS]):
            tx: dict = self.create_register_prep_tx(address)
            tx_list.append(tx)
        self.process_confirm_block_tx(tx_list)

        # set Revision REV_IISS (decentralization)
        self.set_revision(Revision.DECENTRALIZATION.value)

        self.make_blocks_to_end_calculation()

        # get main prep
        response: dict = self.get_main_prep_list()
        expected_preps: list = []
        expected_total_delegated: int = 0
        for account in self._accounts[:PREP_MAIN_PREPS]:
            expected_preps.append({"address": account.address, "delegated": 0})
            expected_total_delegated += 0
        expected_response: dict = {"preps": expected_preps, "totalDelegated": 0}
        self.assertEqual(expected_response, response)
