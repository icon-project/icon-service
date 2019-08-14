# -*- coding: utf-8 -*-

# Copyright 2019 ICON Foundation
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
import os

from iconservice.database.db import ExternalDatabase
from iconservice.icon_constant import REV_IISS, ConfigKey, ICX_IN_LOOP, PREP_MAIN_PREPS, PREP_MAIN_AND_SUB_PREPS, \
    IISS_DB, REV_DECENTRALIZATION
from iconservice.iiss.reward_calc import RewardCalcStorage
from iconservice.iiss.reward_calc.msg_data import GovernanceVariable
from tests.integrate_test.iiss.test_iiss_base import TestIISSBase
from tests.integrate_test.test_integrate_base import TOTAL_SUPPLY


class TestRCDatabase(TestIISSBase):
    def _make_init_config(self) -> dict:
        config: dict = super()._make_init_config()
        config[ConfigKey.PREP_REGISTRATION_FEE] = 0
        return config

    def setUp(self):
        super().setUp()

    @staticmethod
    def get_last_rc_db_data(rc_data_path):
        return sorted([dir_name for dir_name in os.listdir(rc_data_path)
                       if dir_name.startswith(RewardCalcStorage._IISS_RC_DB_NAME_PREFIX)],
                      key=lambda rc_dir: int(rc_dir[len(RewardCalcStorage._IISS_RC_DB_NAME_PREFIX):]),
                      reverse=True)[0]

    def test_irep_when_iiss_rev_and_decentralized(self):
        # success case: should record 0 as irep
        rc_data_path: str = os.path.join(self._state_db_root_path, IISS_DB)

        # decentralized
        self.update_governance()

        # set Revision REV_IISS
        self.set_revision(REV_IISS)
        get_last_rc_db: str = self.get_last_rc_db_data(rc_data_path)
        rc_db = ExternalDatabase.from_path(os.path.join(rc_data_path, get_last_rc_db))
        for rc_data in rc_db.iterator():
            if rc_data[0][:2] == GovernanceVariable._PREFIX:
                gv: 'GovernanceVariable' = GovernanceVariable.from_bytes(rc_data[0], rc_data[1])
                expected_block_height = self._block_height
                expected_irep = 0
                expected_rrep = 1200 * 3
                self.assertEqual(expected_block_height, gv.block_height)
                self.assertEqual(expected_irep, gv.calculated_irep)
                self.assertEqual(expected_rrep, gv.reward_rep)

        total_supply = TOTAL_SUPPLY * ICX_IN_LOOP
        # Minimum_delegate_amount is 0.02 * total_supply
        # In this test delegate 0.03*total_supply because `Issue transaction` exists since REV_IISS
        minimum_delegate_amount_for_decentralization: int = total_supply * 2 // 1000 + 1
        init_balance: int = minimum_delegate_amount_for_decentralization * 2

        # distribute icx PREP_MAIN_PREPS ~ PREP_MAIN_PREPS + PREP_MAIN_PREPS - 1
        self.distribute_icx(accounts=self._accounts[PREP_MAIN_PREPS:PREP_MAIN_AND_SUB_PREPS],
                            init_balance=init_balance)

        # stake PREP_MAIN_PREPS ~ PREP_MAIN_PREPS + PREP_MAIN_PREPS - 1
        stake_amount: int = minimum_delegate_amount_for_decentralization
        tx_list: list = []
        for i in range(PREP_MAIN_PREPS):
            tx: dict = self.create_set_stake_tx(from_=self._accounts[PREP_MAIN_PREPS + i],
                                                value=stake_amount)
            tx_list.append(tx)
        self.process_confirm_block_tx(tx_list)

        # distribute icx PREP_MAIN_PREPS ~ PREP_MAIN_PREPS + PREP_MAIN_PREPS - 1
        self.distribute_icx(accounts=self._accounts[:PREP_MAIN_PREPS],
                            init_balance=10 * ICX_IN_LOOP)

        # register PRep
        tx_list: list = []
        for account in self._accounts[:PREP_MAIN_PREPS]:
            tx: dict = self.create_register_prep_tx(from_=account, value=0)
            tx_list.append(tx)
        self.process_confirm_block_tx(tx_list)

        # delegate to PRep
        tx_list: list = []
        for i in range(PREP_MAIN_PREPS):
            tx: dict = self.create_set_delegation_tx(from_=self._accounts[PREP_MAIN_PREPS + i],
                                                     origin_delegations=[
                                                         (
                                                             self._accounts[i],
                                                             minimum_delegate_amount_for_decentralization
                                                         )
                                                     ])
            tx_list.append(tx)
        self.process_confirm_block_tx(tx_list)

        block_height: int = self.make_blocks_to_end_calculation()
        get_last_rc_db: str = self.get_last_rc_db_data(rc_data_path)
        rc_db = ExternalDatabase.from_path(os.path.join(rc_data_path, get_last_rc_db))
        for rc_data in rc_db.iterator():
            if rc_data[0][:2] == GovernanceVariable._PREFIX:
                gv: 'GovernanceVariable' = GovernanceVariable.from_bytes(rc_data[0], rc_data[1])
                expected_block_height = block_height
                expected_irep = 0
                expected_rrep = 1078 * 3
                self.assertEqual(expected_block_height, gv.block_height)
                self.assertEqual(expected_irep, gv.calculated_irep)
                self.assertEqual(expected_rrep, gv.reward_rep)

        self.set_revision(REV_DECENTRALIZATION)

        self.make_blocks_to_end_calculation()
        block_height: int = self.make_blocks_to_end_calculation()
        get_last_rc_db: str = self.get_last_rc_db_data(rc_data_path)
        rc_db = ExternalDatabase.from_path(os.path.join(rc_data_path, get_last_rc_db))
        for rc_data in rc_db.iterator():
            if rc_data[0][:2] == GovernanceVariable._PREFIX:
                gv: 'GovernanceVariable' = GovernanceVariable.from_bytes(rc_data[0], rc_data[1])
                expected_block_height = block_height
                # calculated irep (irep: 50000 ICX)
                expected_irep = 19290123456790123
                expected_rrep = 1078 * 3
                self.assertEqual(expected_block_height, gv.block_height)
                self.assertEqual(expected_irep, gv.calculated_irep)
                self.assertEqual(expected_rrep, gv.reward_rep)


