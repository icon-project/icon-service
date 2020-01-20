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

from iconservice import ZERO_SCORE_ADDRESS
from iconservice.database.db import KeyValueDatabase
from iconservice.icon_constant import Revision, ConfigKey, ICX_IN_LOOP, PREP_MAIN_PREPS, PREP_MAIN_AND_SUB_PREPS, \
    IISS_DB
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
                       if dir_name.startswith(RewardCalcStorage.IISS_RC_DB_NAME_PREFIX)],
                      key=lambda rc_dir: int(rc_dir[len(RewardCalcStorage.IISS_RC_DB_NAME_PREFIX)+1:]),
                      reverse=True)[0]

    def _check_the_name_of_rc_db(self, actual_rc_db_name: str):
        expected_last_rc_db_name: str = f"{Storage.IISS_RC_DB_NAME_PREFIX}_{self._block_height - 1}"
        self.assertEqual(expected_last_rc_db_name, actual_rc_db_name)

    def test_all_rc_db_data_block_height(self):
        main_preps_address = [main_prep_account.address for main_prep_account in self._accounts[:PREP_MAIN_PREPS]]
        rc_data_path: str = os.path.join(self._state_db_root_path, IISS_DB)

        self.update_governance()

        # set Revision REV_IISS
        # ################## term 0 start #####################
        self.set_revision(Revision.IISS.value)
        self.make_blocks(self._block_height + 1)
        get_last_rc_db: str = self.get_last_rc_db_data(rc_data_path)
        expected_version: int = 0
        self._check_the_name_of_rc_db(get_last_rc_db)
        rc_db = KeyValueDatabase.from_path(os.path.join(rc_data_path, get_last_rc_db))

        expected_rc_db_data_count: int = 1
        expected_block_height_at_the_start_of_iiss = self._block_height - 1
        rc_data_count: int = 0
        self.assertIsNotNone(rc_db.get(Header.PREFIX))
        for rc_data in rc_db.iterator():
            # There is no GV at the first time
            if rc_data[0][:2] == Header.PREFIX:
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
        # ################## term 0 End #####################
        # ################## term 1 Start (decentralization) #####################
        self.make_blocks(self._block_height + 1,
                         prev_block_generator=main_preps_address[0],
                         prev_block_validators=main_preps_address[1:])

        get_last_rc_db: str = self.get_last_rc_db_data(rc_data_path)
        rc_db = KeyValueDatabase.from_path(os.path.join(rc_data_path, get_last_rc_db))

        expected_gv_block_height: int = expected_block_height_at_the_start_of_iiss
        expected_hd_block_height: int = block_height
        self.assertIsNotNone(rc_db.get(Header.PREFIX))
        for rc_data in rc_db.iterator():
            print(rc_data)
            if rc_data[0][:2] == Header.PREFIX:
                hd: 'Header' = Header.from_bytes(rc_data[1])
                expected_version = 0
                self.assertEqual(expected_version, hd.version)
                self.assertEqual(expected_hd_block_height, hd.block_height)

            if rc_data[0][:2] == GovernanceVariable.PREFIX:
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

        self.set_revision(Revision.DECENTRALIZATION.value)
        expected_gv_block_height = expected_hd_block_height
        expected_hd_block_height: int = self.make_blocks_to_end_calculation(prev_block_generator=main_preps_address[0],
                                                                            prev_block_validators=main_preps_address[1:])
        # ################## term 1 End #####################
        # ################## term 2 Start #####################
        self.make_blocks(self._block_height + 1,
                         prev_block_generator=main_preps_address[0],
                         prev_block_validators=main_preps_address[1:])
        get_last_rc_db: str = self.get_last_rc_db_data(rc_data_path)
        expected_version: int = 0
        self._check_the_name_of_rc_db(get_last_rc_db)
        rc_db = KeyValueDatabase.from_path(os.path.join(rc_data_path, get_last_rc_db))
        self.assertIsNotNone(rc_db.get(Header.PREFIX))
        for rc_data in rc_db.iterator():
            print(rc_data)
            if rc_data[0][:2] == Header.PREFIX:
                hd: 'Header' = Header.from_bytes(rc_data[1])
                expected_version = 0
                expected_revisions = 0
                self.assertEqual(expected_version, hd.version)
                self.assertEqual(expected_hd_block_height, hd.block_height)
                self.assertEqual(expected_revisions, hd.revision)

            if rc_data[0][:2] == GovernanceVariable.PREFIX:
                gv: 'GovernanceVariable' = GovernanceVariable.from_bytes(rc_data[0], rc_data[1])
                # calculated irep (irep: 50000 ICX)
                expected_irep = 0
                expected_main_prep_count = 0
                expected_sub_prep_count = 0
                expected_rrep = 1078 * 3
                expected_version = 0
                self.assertEqual(expected_gv_block_height, gv.block_height)
                self.assertEqual(expected_main_prep_count, gv.config_main_prep_count)
                self.assertEqual(expected_sub_prep_count, gv.config_sub_prep_count)
                self.assertEqual(expected_irep, gv.calculated_irep)
                self.assertEqual(expected_rrep, gv.reward_rep)
                self.assertEqual(expected_version, gv.version)

            if rc_data[0][:2] == BlockProduceInfoData.PREFIX:
                raise AssertionError

            if rc_data[0][:2] == PRepsData.PREFIX:
                raise AssertionError

        expected_gv_block_height: int = expected_hd_block_height
        expected_hd_block_height: int = self.make_blocks_to_end_calculation(prev_block_generator=main_preps_address[0],
                                                                            prev_block_validators=main_preps_address[1:])
        # ################## term 2 End #####################
        self.make_blocks(self._block_height + 1,
                         prev_block_generator=main_preps_address[0],
                         prev_block_validators=main_preps_address[1:])
        expected_pr_block_height: int = expected_gv_block_height
        get_last_rc_db: str = self.get_last_rc_db_data(rc_data_path)
        self._check_the_name_of_rc_db(get_last_rc_db)
        rc_db = KeyValueDatabase.from_path(os.path.join(rc_data_path, get_last_rc_db))

        expected_bp_block_height: int = expected_gv_block_height + 1
        self.assertIsNotNone(rc_db.get(Header.PREFIX))
        for rc_data in rc_db.iterator():
            if rc_data[0][:2] == Header.PREFIX:
                hd: 'Header' = Header.from_bytes(rc_data[1])
                expected_block_height = self._block_height
                expected_version = 2
                expected_revisions = Revision.DECENTRALIZATION.value
                self.assertEqual(expected_version, hd.version)
                self.assertEqual(expected_hd_block_height, hd.block_height)
                self.assertEqual(expected_revisions, hd.revision)

            if rc_data[0][:2] == GovernanceVariable.PREFIX:
                gv: 'GovernanceVariable' = GovernanceVariable.from_bytes(rc_data[0], rc_data[1])
                # calculated irep (irep: 50000 ICX)
                expected_irep = 19290123456790123
                expected_main_prep_count = 22
                expected_sub_prep_count = 100 - expected_main_prep_count
                expected_rrep = 1078 * 3
                expected_version = 2
                self.assertEqual(expected_gv_block_height, gv.block_height)
                self.assertEqual(expected_main_prep_count, gv.config_main_prep_count)
                self.assertEqual(expected_sub_prep_count, gv.config_sub_prep_count)
                self.assertEqual(expected_irep, gv.calculated_irep)
                self.assertEqual(expected_rrep, gv.reward_rep)
                self.assertEqual(expected_version, gv.version)

            if rc_data[0][:2] == PRepsData.PREFIX:
                pr: 'PRepsData' = PRepsData.from_bytes(rc_data[0], rc_data[1])
                self.assertEqual(expected_pr_block_height, pr.block_height)

            if rc_data[0][:2] == BlockProduceInfoData.PREFIX:
                bp: 'BlockProduceInfoData' = BlockProduceInfoData.from_bytes(rc_data[0], rc_data[1])
                self.assertEqual(expected_bp_block_height, bp.block_height)
                self.assertTrue(expected_gv_block_height < bp.block_height <= expected_hd_block_height)
                expected_bp_block_height += 1
        actual_last_bp_block_height: int = expected_bp_block_height - 1
        expected_last_bp_block_height: int = self._block_height - 1
        self.assertEqual(expected_last_bp_block_height, actual_last_bp_block_height)

    def test_change_revision(self):
        main_preps_address = [main_prep_account.address for main_prep_account in self._accounts[:PREP_MAIN_PREPS]]
        rc_data_path: str = os.path.join(self._state_db_root_path, IISS_DB)

        self.update_governance()

        # set Revision REV_IISS
        # ################## term 0 start #####################
        self.set_revision(Revision.IISS.value)
        self.make_blocks(self._block_height + 1)
        get_last_rc_db: str = self.get_last_rc_db_data(rc_data_path)
        self._check_the_name_of_rc_db(get_last_rc_db)
        rc_db = KeyValueDatabase.from_path(os.path.join(rc_data_path, get_last_rc_db))

        expected_rc_db_data_count: int = 1
        expected_block_height_at_the_start_of_iiss = self._block_height - 1
        rc_data_count: int = 0
        for rc_data in rc_db.iterator():
            # There is no GV at the first time
            if rc_data[0][:2] == Header.PREFIX:
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

        # set revision on calc first block height(REV_DECENTRALIZATION)
        expected_gv_block: int = self.make_blocks_to_end_calculation()
        self.set_revision(Revision.DECENTRALIZATION.value)

        # after next calc.
        expected_hd_block: int = self.make_blocks_to_end_calculation()
        self.make_blocks(self._block_height + 1)

        # expected Revision (REV_IISS)
        get_last_rc_db: str = self.get_last_rc_db_data(rc_data_path)
        rc_db = KeyValueDatabase.from_path(os.path.join(rc_data_path, get_last_rc_db))

        for rc_data in rc_db.iterator():
            if rc_data[0][:2] == Header.PREFIX:
                hd: 'Header' = Header.from_bytes(rc_data[1])
                expected_version = 0
                self.assertEqual(expected_hd_block, hd.block_height)
                self.assertEqual(expected_version, hd.version)
                # not support on VERSION 0
                # self.assertEqual(expected_revision, hd.revision)

            if rc_data[0][:2] == GovernanceVariable.PREFIX:
                gv: 'GovernanceVariable' = GovernanceVariable.from_bytes(rc_data[0], rc_data[1])
                expected_version = 0
                self.assertEqual(expected_gv_block, gv.block_height)
                self.assertEqual(expected_version, gv.version)

        expected_gv_block: int = expected_hd_block
        expected_hd_block: int = self.make_blocks_to_end_calculation()
        expected_prep_block: int = expected_gv_block

        # unregister prep on start term period
        tx: dict = self.create_score_call_tx(from_=main_preps_address[0],
                                             to_=ZERO_SCORE_ADDRESS,
                                             func_name="unregisterPRep",
                                             params={},
                                             value=0)
        self.process_confirm_block_tx([tx])

        # expected Revision (REV_DECENTRALIZATION)
        get_last_rc_db: str = self.get_last_rc_db_data(rc_data_path)
        rc_db = KeyValueDatabase.from_path(os.path.join(rc_data_path, get_last_rc_db))

        for rc_data in rc_db.iterator():
            if rc_data[0][:2] == PRepsData.PREFIX:
                preps: 'PRepsData' = PRepsData.from_bytes(rc_data[0], rc_data[1])
                self.assertEqual(expected_prep_block, preps.block_height)
                prep_addresses: list = [del_info.address for del_info in preps.prep_list]
                expected_prep_address = main_preps_address
                diff_cnt: int = 0
                self.assertEqual(diff_cnt, len(set(expected_prep_address) ^ set(prep_addresses)))
            if rc_data[0][:2] == Header.PREFIX:
                hd: 'Header' = Header.from_bytes(rc_data[1])
                expected_version = 2
                expected_revision = 6
                self.assertEqual(expected_hd_block, hd.block_height)
                self.assertEqual(expected_version, hd.version)
                self.assertEqual(expected_revision, hd.revision)

            if rc_data[0][:2] == GovernanceVariable.PREFIX:
                gv: 'GovernanceVariable' = GovernanceVariable.from_bytes(rc_data[0], rc_data[1])
                expected_version = 2
                self.assertEqual(expected_gv_block, gv.block_height)
                self.assertEqual(expected_version, gv.version)

        expected_gv_block: int = expected_hd_block
        expected_hd_block: int = self.make_blocks_to_end_calculation()
        expected_prep_block: int = expected_gv_block

        self.make_blocks(self._block_height + 1)
        get_last_rc_db: str = self.get_last_rc_db_data(rc_data_path)
        rc_db = KeyValueDatabase.from_path(os.path.join(rc_data_path, get_last_rc_db))

        for rc_data in rc_db.iterator():
            if rc_data[0][:2] == PRepsData.PREFIX:
                preps: 'PRepsData' = PRepsData.from_bytes(rc_data[0], rc_data[1])
                self.assertEqual(expected_prep_block, preps.block_height)
                prep_addresses: list = [del_info.address for del_info in preps.prep_list]
                if expected_gv_block == expected_prep_block:
                    # In case of term change
                    expected_prep_address = main_preps_address
                else:
                    # In case of unregister
                    expected_prep_address = main_preps_address[1:]
                diff_cnt: int = 0
                self.assertEqual(diff_cnt, len(set(expected_prep_address) ^ set(prep_addresses)))
                expected_prep_block += 1

            if rc_data[0][:2] == Header.PREFIX:
                hd: 'Header' = Header.from_bytes(rc_data[1])
                expected_version = 2
                expected_revision = 6
                self.assertEqual(expected_hd_block, hd.block_height)
                self.assertEqual(expected_version, hd.version)
                self.assertEqual(expected_revision, hd.revision)

            if rc_data[0][:2] == GovernanceVariable.PREFIX:
                gv: 'GovernanceVariable' = GovernanceVariable.from_bytes(rc_data[0], rc_data[1])
                expected_version = 2
                self.assertEqual(expected_gv_block, gv.block_height)
                self.assertEqual(expected_version, gv.version)

        # unregister on term
        self.make_blocks(self._block_height + 4)
        tx: dict = self.create_score_call_tx(from_=main_preps_address[1],
                                             to_=ZERO_SCORE_ADDRESS,
                                             func_name="unregisterPRep",
                                             params={},
                                             value=0)
        self.process_confirm_block_tx([tx])

        expected_gv_block: int = expected_hd_block
        self.make_blocks_to_end_calculation()
        expected_prep_block: int = expected_gv_block

        self.make_blocks(self._block_height + 1)
        get_last_rc_db: str = self.get_last_rc_db_data(rc_data_path)
        rc_db = KeyValueDatabase.from_path(os.path.join(rc_data_path, get_last_rc_db))

        for rc_data in rc_db.iterator():
            if rc_data[0][:2] == PRepsData.PREFIX:
                preps: 'PRepsData' = PRepsData.from_bytes(rc_data[0], rc_data[1])
                self.assertEqual(expected_prep_block, preps.block_height)
                prep_addresses: list = [del_info.address for del_info in preps.prep_list]
                if expected_gv_block == expected_prep_block:
                    # In case of term change
                    expected_prep_address = main_preps_address[1:]
                else:
                    # In case of unregister
                    expected_prep_address = main_preps_address[2:]
                diff_cnt: int = 0
                self.assertEqual(diff_cnt, len(set(expected_prep_address) ^ set(prep_addresses)))
                expected_prep_block += 6

    def test_bp_on_the_start_term(self):
        # Success case: Put valid bp info incase of below case
        # 1. at th start block of term
        # 2. invoke 2 blocks on the same block height
        # 3. commit the first invoked block
        # 4. committed block has different validator set compared to second block
        # Should record the first validator set on the iiss db
        main_preps_address = [main_prep_account.address for main_prep_account in self._accounts[:PREP_MAIN_PREPS]]
        rc_data_path: str = os.path.join(self._state_db_root_path, IISS_DB)

        self.update_governance()

        # ################## term 0 start #####################
        self.set_revision(Revision.IISS.value)
        self.make_blocks(self._block_height + 1)
        last_iiss_db: str = self.get_last_rc_db_data(rc_data_path)

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
        # ################## term 0 End #####################
        # ################## term 1 Start (decentralization) #####################
        self.make_blocks(self._block_height + 1,
                         prev_block_generator=main_preps_address[0],
                         prev_block_validators=main_preps_address[1:])

        last_iiss_db: str = self.get_last_rc_db_data(rc_data_path)
        iiss_db = KeyValueDatabase.from_path(os.path.join(rc_data_path, last_iiss_db))

        self.set_revision(Revision.DECENTRALIZATION.value)
        expected_hd_block_height: int = self.make_blocks_to_end_calculation(prev_block_generator=main_preps_address[0],
                                                                            prev_block_validators=main_preps_address[
                                                                                                  1:])
        # ################## term 1 End #####################
        # ################## term 2 Start #####################
        self.make_blocks_to_end_calculation(prev_block_generator=main_preps_address[0],
                                            prev_block_validators=main_preps_address[1:])
        # make 2 blocks which has different
        tx1 = self.create_transfer_icx_tx(self._admin, self._genesis, 0)
        tx2 = self.create_transfer_icx_tx(self._admin, self._genesis, 1)
        # Invoke block_1
        validator_1 = [main_preps_address[1]]
        block_1, hash_list_1 = self.make_and_req_block([tx1],
                                                       prev_block_generator=main_preps_address[0],
                                                       prev_block_validators=validator_1)
        # Invoke block_2
        validator_2 = [main_preps_address[2]]
        block_2, hash_list_2 = self.make_and_req_block([tx2],
                                                       prev_block_generator=main_preps_address[0],
                                                       prev_block_validators=validator_2)

        # Commit block_1
        self._write_precommit_state(block_1)

        # Check the latest iiss db and current db
        last_iiss_db: str = self.get_last_rc_db_data(rc_data_path)
        iiss_db = KeyValueDatabase.from_path(os.path.join(rc_data_path, last_iiss_db))

        calc_end_block: int = block_1.height - 1
        for rc_data in iiss_db.iterator():
            if rc_data[0][:2] == BlockProduceInfoData.PREFIX and \
                    int.from_bytes(rc_data[0][2:], 'big') == calc_end_block:
                bp = BlockProduceInfoData.from_bytes(rc_data[0], rc_data[1])
                self.assertEqual(validator_1, bp.block_validator_list)
                self.assertNotEqual(validator_2, bp.block_validator_list)

        current_db = KeyValueDatabase.from_path(os.path.join(rc_data_path, RewardCalcStorage.CURRENT_IISS_DB_NAME))
        for rc_data in current_db.iterator():
            if rc_data[0][:2] == GovernanceVariable.PREFIX:
                gv: 'GovernanceVariable' = GovernanceVariable.from_bytes(rc_data[0], rc_data[1])
                self.assertEqual(calc_end_block, gv.block_height)
            if rc_data[0][:2] == BlockProduceInfoData.PREFIX:
                raise AssertionError
