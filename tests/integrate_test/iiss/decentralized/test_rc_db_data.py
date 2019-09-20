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

from iconservice.database.db import KeyValueDatabase
from iconservice.icon_constant import REV_IISS, ConfigKey, ICX_IN_LOOP, PREP_MAIN_PREPS, PREP_MAIN_AND_SUB_PREPS, \
    IISS_DB, REV_DECENTRALIZATION
from iconservice.iiss.reward_calc import RewardCalcStorage
from iconservice.iiss.reward_calc.msg_data import GovernanceVariable, Header, PRepsData, BlockProduceInfoData
from iconservice.iiss.reward_calc.storage import Storage
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
        rc_db = KeyValueDatabase.from_path(os.path.join(rc_data_path, get_last_rc_db))
        for rc_data in rc_db.iterator():
            # There is no GV at the first time
            if rc_data[0][:2] == Header._PREFIX:
                hd: 'Header' = Header.from_bytes(rc_data[1])
                expected_block_height = self._block_height
                expected_version = 0
                self.assertEqual(expected_version, hd.version)
                self.assertEqual(expected_block_height, hd.block_height)

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
        rc_db = KeyValueDatabase.from_path(os.path.join(rc_data_path, get_last_rc_db))
        for rc_data in rc_db.iterator():
            if rc_data[0][:2] == GovernanceVariable._PREFIX:
                gv: 'GovernanceVariable' = GovernanceVariable.from_bytes(rc_data[0], rc_data[1])
                expected_irep = 0
                expected_main_prep_count = 0
                expected_sub_prep_count = 0
                expected_rrep = 1200 * 3
                self.assertEqual(expected_block_height, gv.block_height)
                self.assertEqual(expected_main_prep_count, gv.config_main_prep_count)
                self.assertEqual(expected_sub_prep_count, gv.config_sub_prep_count)
                self.assertEqual(expected_irep, gv.calculated_irep)
                self.assertEqual(expected_rrep, gv.reward_rep)

        self.set_revision(REV_DECENTRALIZATION)
        expected_gv_block_height = block_height
        expected_hd_block_height: int = self.make_blocks_to_end_calculation()
        get_last_rc_db: str = self.get_last_rc_db_data(rc_data_path)
        rc_db = KeyValueDatabase.from_path(os.path.join(rc_data_path, get_last_rc_db))
        for rc_data in rc_db.iterator():
            if rc_data[0][:2] == Header._PREFIX:
                hd: 'Header' = Header.from_bytes(rc_data[1])
                expected_version = 0
                expected_revisions = 0
                self.assertEqual(expected_version, hd.version)
                self.assertEqual(expected_hd_block_height, hd.block_height)
                self.assertEqual(expected_revisions, hd.revision)

            if rc_data[0][:2] == GovernanceVariable._PREFIX:
                gv: 'GovernanceVariable' = GovernanceVariable.from_bytes(rc_data[0], rc_data[1])
                # calculated irep (irep: 50000 ICX)
                expected_irep = 0
                expected_main_prep_count = 0
                expected_sub_prep_count = 0
                expected_rrep = 1078 * 3
                self.assertEqual(expected_gv_block_height, gv.block_height)
                self.assertEqual(expected_main_prep_count, gv.config_main_prep_count)
                self.assertEqual(expected_sub_prep_count, gv.config_sub_prep_count)
                self.assertEqual(expected_irep, gv.calculated_irep)
                self.assertEqual(expected_rrep, gv.reward_rep)

        expected_gv_block_height = expected_hd_block_height
        expected_hd_block_height: int = self.make_blocks_to_end_calculation()
        get_last_rc_db: str = self.get_last_rc_db_data(rc_data_path)
        rc_db = KeyValueDatabase.from_path(os.path.join(rc_data_path, get_last_rc_db))
        for rc_data in rc_db.iterator():
            if rc_data[0][:2] == Header._PREFIX:
                hd: 'Header' = Header.from_bytes(rc_data[1])
                expected_block_height = self._block_height
                expected_version = 2
                expected_revisions = REV_DECENTRALIZATION
                self.assertEqual(expected_version, hd.version)
                self.assertEqual(expected_hd_block_height, hd.block_height)
                self.assertEqual(expected_revisions, hd.revision)

            if rc_data[0][:2] == GovernanceVariable._PREFIX:
                gv: 'GovernanceVariable' = GovernanceVariable.from_bytes(rc_data[0], rc_data[1])
                # calculated irep (irep: 50000 ICX)
                expected_irep = 19290123456790123
                expected_main_prep_count = 22
                expected_sub_prep_count = 100 - expected_main_prep_count
                expected_rrep = 1078 * 3
                self.assertEqual(expected_gv_block_height, gv.block_height)
                self.assertEqual(expected_main_prep_count, gv.config_main_prep_count)
                self.assertEqual(expected_sub_prep_count, gv.config_sub_prep_count)
                self.assertEqual(expected_irep, gv.calculated_irep)
                self.assertEqual(expected_rrep, gv.reward_rep)

    def _check_the_name_of_rc_db(self, actual_rc_db_name):
        # Todo: this method should be changed after CALCULATE time is changed to starting of calc
        expected_last_rc_db_name: str = Storage._IISS_RC_DB_NAME_PREFIX + str(self._block_height)
        self.assertEqual(expected_last_rc_db_name, actual_rc_db_name)

    def test_all_rc_db_data_block_height(self):
        main_preps_address = [main_prep_account.address for main_prep_account in self._accounts[:PREP_MAIN_PREPS]]
        rc_data_path: str = os.path.join(self._state_db_root_path, IISS_DB)

        # decentralized
        self.update_governance()

        # set Revision REV_IISS
        # ################## term 0 start #####################
        self.set_revision(REV_IISS)
        get_last_rc_db: str = self.get_last_rc_db_data(rc_data_path)
        self._check_the_name_of_rc_db(get_last_rc_db)
        rc_db = KeyValueDatabase.from_path(os.path.join(rc_data_path, get_last_rc_db))

        expected_rc_db_data_count: int = 1
        expected_block_height_at_the_start_of_iiss = self._block_height
        rc_data_count: int = 0
        for rc_data in rc_db.iterator():
            # There is no GV at the first time
            if rc_data[0][:2] == Header._PREFIX:
                hd: 'Header' = Header.from_bytes(rc_data[1])
                expected_version = 0
                self.assertEqual(expected_version, hd.version)
                self.assertEqual(expected_block_height_at_the_start_of_iiss, hd.block_height)
            rc_data_count += 1
        expected_rc_db_data_count: int = 1
        self.assertEqual(expected_rc_db_data_count, rc_data_count)

        total_supply = TOTAL_SUPPLY * ICX_IN_LOOP
        # Minimum_delegate_amount is 0.02 * total_supply
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

        block_height: int = self.make_blocks_to_end_calculation(prev_block_generator=main_preps_address[0],
                                                                prev_block_validators=main_preps_address[1:])
        get_last_rc_db: str = self.get_last_rc_db_data(rc_data_path)
        rc_db = KeyValueDatabase.from_path(os.path.join(rc_data_path, get_last_rc_db))
        # ################## term 0 End #####################
        expected_gv_block_height: int = expected_block_height_at_the_start_of_iiss
        expected_hd_block_height: int = self._block_height
        for rc_data in rc_db.iterator():
            print(rc_data)
            if rc_data[0][:2] == Header._PREFIX:
                hd: 'Header' = Header.from_bytes(rc_data[1])
                expected_version = 0
                self.assertEqual(expected_version, hd.version)
                self.assertEqual(expected_hd_block_height, hd.block_height)

            if rc_data[0][:2] == GovernanceVariable._PREFIX:
                gv: 'GovernanceVariable' = GovernanceVariable.from_bytes(rc_data[0], rc_data[1])
                expected_irep = 0
                expected_main_prep_count = 0
                expected_sub_prep_count = 0
                expected_rrep = 1200 * 3
                self.assertEqual(expected_gv_block_height, gv.block_height)
                self.assertEqual(expected_main_prep_count, gv.config_main_prep_count)
                self.assertEqual(expected_sub_prep_count, gv.config_sub_prep_count)
                self.assertEqual(expected_irep, gv.calculated_irep)
                self.assertEqual(expected_rrep, gv.reward_rep)

        # ################## term 1 Start (decentralization) #####################
        self.set_revision(REV_DECENTRALIZATION)
        expected_gv_block_height = expected_hd_block_height
        expected_hd_block_height: int = self.make_blocks_to_end_calculation(prev_block_generator=main_preps_address[0],
                                                                            prev_block_validators=main_preps_address[1:])
        get_last_rc_db: str = self.get_last_rc_db_data(rc_data_path)
        self._check_the_name_of_rc_db(get_last_rc_db)
        rc_db = KeyValueDatabase.from_path(os.path.join(rc_data_path, get_last_rc_db))
        # ################## term 1 End #####################
        for rc_data in rc_db.iterator():
            print(rc_data)
            if rc_data[0][:2] == Header._PREFIX:
                hd: 'Header' = Header.from_bytes(rc_data[1])
                expected_version = 0
                expected_revisions = 0
                self.assertEqual(expected_version, hd.version)
                self.assertEqual(expected_hd_block_height, hd.block_height)
                self.assertEqual(expected_revisions, hd.revision)

            if rc_data[0][:2] == GovernanceVariable._PREFIX:
                gv: 'GovernanceVariable' = GovernanceVariable.from_bytes(rc_data[0], rc_data[1])
                # calculated irep (irep: 50000 ICX)
                expected_irep = 0
                expected_main_prep_count = 0
                expected_sub_prep_count = 0
                expected_rrep = 1078 * 3
                self.assertEqual(expected_gv_block_height, gv.block_height)
                self.assertEqual(expected_main_prep_count, gv.config_main_prep_count)
                self.assertEqual(expected_sub_prep_count, gv.config_sub_prep_count)
                self.assertEqual(expected_irep, gv.calculated_irep)
                self.assertEqual(expected_rrep, gv.reward_rep)

            if rc_data[0][:2] == PRepsData._PREFIX:
                raise AssertionError

        # ################## term 2 Start #####################
        expected_gv_block_height: int = expected_hd_block_height
        expected_hd_block_height: int = self.make_blocks_to_end_calculation(prev_block_generator=main_preps_address[0],
                                                                            prev_block_validators=main_preps_address[1:])
        expected_pr_block_height: int = expected_gv_block_height
        get_last_rc_db: str = self.get_last_rc_db_data(rc_data_path)
        self._check_the_name_of_rc_db(get_last_rc_db)
        rc_db = KeyValueDatabase.from_path(os.path.join(rc_data_path, get_last_rc_db))
        # ################## term 2 End #####################
        expected_bp_block_height: int = expected_gv_block_height + 1
        for rc_data in rc_db.iterator():
            print(rc_data)
            if rc_data[0][:2] == Header._PREFIX:
                hd: 'Header' = Header.from_bytes(rc_data[1])
                expected_block_height = self._block_height
                expected_version = 2
                expected_revisions = REV_DECENTRALIZATION
                self.assertEqual(expected_version, hd.version)
                self.assertEqual(expected_hd_block_height, hd.block_height)
                self.assertEqual(expected_revisions, hd.revision)

            if rc_data[0][:2] == GovernanceVariable._PREFIX:
                gv: 'GovernanceVariable' = GovernanceVariable.from_bytes(rc_data[0], rc_data[1])
                # calculated irep (irep: 50000 ICX)
                expected_irep = 19290123456790123
                expected_main_prep_count = 22
                expected_sub_prep_count = 100 - expected_main_prep_count
                expected_rrep = 1078 * 3
                self.assertEqual(expected_gv_block_height, gv.block_height)
                self.assertEqual(expected_main_prep_count, gv.config_main_prep_count)
                self.assertEqual(expected_sub_prep_count, gv.config_sub_prep_count)
                self.assertEqual(expected_irep, gv.calculated_irep)
                self.assertEqual(expected_rrep, gv.reward_rep)

            if rc_data[0][:2] == PRepsData._PREFIX:
                pr: 'PRepsData' = PRepsData.from_bytes(rc_data[0], rc_data[1])
                self.assertEqual(expected_pr_block_height, pr.block_height)

            if rc_data[0][:2] == BlockProduceInfoData._PREFIX:
                bp: 'BlockProduceInfoData' = BlockProduceInfoData.from_bytes(rc_data[0], rc_data[1])
                self.assertEqual(expected_bp_block_height, bp.block_height)
                self.assertTrue(expected_gv_block_height < bp.block_height <= expected_hd_block_height)
                expected_bp_block_height += 1
        # Todo: after implement IS-831, should pass the below tests
        # self.assertEqual(expected_bp_block_height, expected_hd_block_height + 1)
        # Todo: implement tests about in term prep change

