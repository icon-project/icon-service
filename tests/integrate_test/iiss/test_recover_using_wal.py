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
import shutil
from enum import IntFlag, auto

from iconservice.database.db import KeyValueDatabase
from iconservice.database.wal import WriteAheadLogWriter, StateWAL, IissWAL, WALState
from iconservice.icon_constant import PREP_MAIN_PREPS, IISS_DB, IconScoreContextType
from iconservice.icon_service_engine import IconServiceEngine
from iconservice.iconscore.icon_score_context import IconScoreContext
from iconservice.iiss.reward_calc import RewardCalcStorage
from iconservice.iiss.reward_calc.msg_data import PRepsData, TxData, \
    TxType, Header, GovernanceVariable
from iconservice.precommit_data_manager import PrecommitData
from tests.integrate_test.iiss.test_iiss_base import TestIISSBase
from tests.integrate_test.test_integrate_base import EOAAccount


class RCDataCheckFlag(IntFlag):
    NONE = 0
    PREP = auto()
    UNREGISTER_TX = auto()
    DELEGATION_TX = auto()
    TX_INDEX = auto()

    VERSION = auto()
    HEADER = auto()
    GOVERNANCE = auto()

    ALL_ON_CALC = PREP | UNREGISTER_TX | DELEGATION_TX | TX_INDEX
    ALL_ON_START = ALL_ON_CALC | VERSION | HEADER | GOVERNANCE


# In this test, do not check about the IPC
class TestRecoverUsingWAL(TestIISSBase):
    def setUp(self):
        super().setUp()
        self.init_decentralized()

        self.prep_to_be_unregistered: 'EOAAccount' = self._accounts[1]
        self.transfer_icx(self._admin, self.prep_to_be_unregistered, 100 * 10 ** 18)

        self.delegated_prep: 'EOAAccount' = self._accounts[0]
        self.delegate_amount: int = 100

        self.delegator: 'EOAAccount' = self._accounts[PREP_MAIN_PREPS]
        self.transfer_icx(self._admin, self.delegator, 100 * 10 ** 18)
        self.set_stake(self.delegator, self.delegate_amount)

        self.staker: 'EOAAccount' = self._admin
        self.stake_amount: int = 100
        self.log_path: str = self.icon_service_engine._get_write_ahead_log_path()
        self.rc_data_path: str = os.path.join(self._state_db_root_path, IISS_DB)

    def tearDown(self):
        super().tearDown()
        if os.path.exists(self.log_path):
            os.remove(self.log_path)
        pass

    def _get_precommit_data_after_invoke(self) -> 'PrecommitData':
        # Invoke the transactions and changed state is going be written to WAL.
        # To make manipulated WAL, return precommit data
        # Transactions are samely used to each tests
        stake_tx = self.create_set_stake_tx(self.staker, self.stake_amount)
        unregister_tx = self.create_unregister_prep_tx(self.prep_to_be_unregistered)
        delegation_tx = self.create_set_delegation_tx(self.delegator, [(self.delegated_prep, self.delegate_amount)])
        block, hash_list = self.make_and_req_block([stake_tx, unregister_tx, delegation_tx])
        precommit_data = self.icon_service_engine._get_updated_precommit_data(block.hash, block.hash)
        return precommit_data

    def _get_wal_writer(self, precommit_data: 'PrecommitData', is_calc_period_start_block: bool):
        wal_writer: 'WriteAheadLogWriter' = WriteAheadLogWriter(precommit_data.revision,
                                                                max_log_count=2,
                                                                block=precommit_data.block,
                                                                instant_block_hash=precommit_data.block.hash)
        wal_writer.open(self.log_path)

        state_wal: 'StateWAL' = StateWAL(precommit_data.block_batch)
        revision: int = precommit_data.rc_db_revision if is_calc_period_start_block else -1
        tx_index: int = IconScoreContext.storage.rc.get_tx_index(is_calc_period_start_block)
        iiss_wal: 'IissWAL' = IissWAL(precommit_data.rc_block_batch, tx_index, revision)
        return wal_writer, state_wal, iiss_wal

    def _write_batch_to_wal(self,
                            wal_writer: 'WriteAheadLogWriter',
                            state_wal: 'StateWAL',
                            iiss_wal: 'IissWAL',
                            is_calc_period_start_block: bool):
        if is_calc_period_start_block:
            wal_writer.write_state(WALState.CALC_PERIOD_START_BLOCK.value, add=False)

        wal_writer.write_walogable(iiss_wal)
        wal_writer.write_walogable(state_wal)
        wal_writer.flush()

    def _get_last_block_from_icon_service(self) -> 'Block':
        return self.icon_service_engine._get_last_block().height

    def _get_commit_context(self, block: 'block'):
        return self.icon_service_engine._context_factory.create(IconScoreContextType.DIRECT, block)

    def _close_and_reopen_iconservice(self):
        self.icon_service_engine.close()
        self.icon_service_engine = IconServiceEngine()
        self.icon_service_engine.open(self._config)

    def _check_the_state_and_rc_db_after_recover(self, block_height: int, is_calc_period_start_block: bool):
        # Check if state is updated
        unregister_status: int = 1
        self.assertEqual(unregister_status, self.get_prep(self.prep_to_be_unregistered)["status"])
        del_info: list = self.get_delegation(self.delegator)['delegations']
        self.assertEqual(self.delegated_prep.address, del_info[0]['address'])
        self.assertEqual(self.delegate_amount, del_info[0]['value'])
        self.assertEqual(self.stake_amount, self.get_stake(self.staker)['stake'])

        # Check if rc db is updated
        rc_data_path: str = os.path.join(self._state_db_root_path, IISS_DB)
        # Get_last_rc_db: str = TestRCDatabase.get_last_rc_db_data(rc_data_path)
        cuerent_rc_db = KeyValueDatabase.from_path(os.path.join(rc_data_path, "current_db"))
        rc_data_flag = RCDataCheckFlag(0)
        for rc_data in cuerent_rc_db.iterator():
            if rc_data[0][:2] == PRepsData.PREFIX:
                pr: 'PRepsData' = PRepsData.from_bytes(rc_data[0], rc_data[1])
                if pr.block_height == block_height:
                    rc_data_flag |= RCDataCheckFlag.PREP
            if rc_data[0][:2] == TxData.PREFIX:
                tx: 'TxData' = TxData.from_bytes(rc_data[1])
                expected_index: int = -1
                tx_index: int = int.from_bytes(rc_data[0][2:], 'big')
                if tx.type == TxType.PREP_UNREGISTER:
                    expected_index: int = 0
                    rc_data_flag |= RCDataCheckFlag.UNREGISTER_TX
                elif tx.type == TxType.DELEGATION:
                    expected_index: int = 1
                    rc_data_flag |= RCDataCheckFlag.DELEGATION_TX
                self.assertEqual(expected_index, tx_index)
                self.assertEqual(block_height, tx.block_height)
            if rc_data[0] == RewardCalcStorage.KEY_FOR_GETTING_LAST_TRANSACTION_INDEX:
                rc_data_flag |= RCDataCheckFlag.TX_INDEX

            # In case of the start of calc, should check if version, header and gv has been put correctly
            if is_calc_period_start_block and rc_data[0] == RewardCalcStorage.KEY_FOR_VERSION_AND_REVISION:
                rc_data_flag |= RCDataCheckFlag.VERSION
            if is_calc_period_start_block and rc_data[0][:2] == Header.PREFIX:
                rc_data_flag |= RCDataCheckFlag.HEADER
            if is_calc_period_start_block and rc_data[0][:2] == GovernanceVariable.PREFIX:
                rc_data_flag |= RCDataCheckFlag.GOVERNANCE

        if is_calc_period_start_block:
            self.assertEqual(RCDataCheckFlag.ALL_ON_START, rc_data_flag)
            self.assertTrue(os.path.exists(os.path.join(rc_data_path,
                                                        f"{RewardCalcStorage.IISS_RC_DB_NAME_PREFIX}{block_height - 1}_2")))
        else:
            self.assertEqual(RCDataCheckFlag.ALL_ON_CALC, rc_data_flag)

    def _check_the_db_after_recover(self, last_block_before_close: int, is_calc_period_start_block: bool):
        last_block_after_open: int = self._get_last_block_from_icon_service()
        self.assertEqual(last_block_before_close + 1, last_block_after_open)
        self.assertFalse(os.path.exists(self.log_path))
        self._check_the_state_and_rc_db_after_recover(last_block_after_open, is_calc_period_start_block)

    def _remove_all_iiss_db_before_reopen(self):
        # For make same environment, remove all iiss_db
        for dir_name in os.listdir(self.rc_data_path):
            if dir_name.startswith(RewardCalcStorage.IISS_RC_DB_NAME_PREFIX):
                shutil.rmtree(os.path.join(self.rc_data_path, dir_name),
                              ignore_errors=False,
                              onerror=None)

    def test_remove_wal(self):
        # Success case: if WAL is incomplete, should remove the WAL
        last_block_before_close: int = self._get_last_block_from_icon_service()
        precommit_data: 'PrecommitData' = self._get_precommit_data_after_invoke()
        wal_writer, state_wal, iiss_wal = self._get_wal_writer(precommit_data, False)

        wal_writer.write_walogable(iiss_wal)
        wal_writer.close()

        self._close_and_reopen_iconservice()
        last_block_after_open: int = self._get_last_block_from_icon_service()

        self.assertFalse(os.path.exists(self.log_path))
        self.assertEqual(last_block_before_close, last_block_after_open)

    def test_close_during_writing_rc_db_on_calc_period(self):
        # Success case: when iconservice is closed during writing rc data to rc db, should write state db when open
        self.make_blocks(self._get_last_block_from_icon_service() + 1)
        is_start_block: bool = False
        last_block_before_close: int = self._get_last_block_from_icon_service()

        precommit_data: 'PrecommitData' = self._get_precommit_data_after_invoke()
        context: 'IconScoreContext' = self._get_commit_context(precommit_data.block)
        wal_writer, state_wal, iiss_wal = self._get_wal_writer(precommit_data, is_start_block)
        self._write_batch_to_wal(wal_writer, state_wal, iiss_wal, is_start_block)

        # write rc data to rc db
        # do not write state of wal (which means overwriting the rc data to db)
        self.icon_service_engine._process_iiss_commit(context, precommit_data, iiss_wal, is_start_block)

        self._close_and_reopen_iconservice()

        self._check_the_db_after_recover(last_block_before_close, is_start_block)

    def test_close_after_writing_rc_db_on_calc_period(self):
        # Success case: when iconservice is closed after writing rc data to rc db, should write state db when open
        self.make_blocks(self._get_last_block_from_icon_service() + 1)
        is_start_block: bool = False
        last_block_before_close: int = self._get_last_block_from_icon_service()

        precommit_data: 'PrecommitData' = self._get_precommit_data_after_invoke()
        context: 'IconScoreContext' = self._get_commit_context(precommit_data.block)
        wal_writer, state_wal, iiss_wal = self._get_wal_writer(precommit_data, is_start_block)
        self._write_batch_to_wal(wal_writer, state_wal, iiss_wal, is_start_block)

        # write rc data to rc db
        self.icon_service_engine._process_iiss_commit(context, precommit_data, iiss_wal, is_start_block)
        wal_writer.write_state(WALState.WRITE_RC_DB.value, add=True)

        self._close_and_reopen_iconservice()

        self._check_the_db_after_recover(last_block_before_close, is_start_block)

    def test_close_before_change_current_to_standby_on_the_start(self):
        # Success case: Iconservice is closed before changing current db to standby db,
        # should change current db to iiss db and create new current db (That is before commit data to rc db)
        self.make_blocks_to_end_calculation()
        is_start_block: bool = True
        last_block_before_close: int = self._get_last_block_from_icon_service()

        precommit_data: 'PrecommitData' = self._get_precommit_data_after_invoke()
        wal_writer, state_wal, iiss_wal = self._get_wal_writer(precommit_data, is_start_block)
        self._write_batch_to_wal(wal_writer, state_wal, iiss_wal, is_start_block)

        # remove all iiss_db
        self._remove_all_iiss_db_before_reopen()
        self._close_and_reopen_iconservice()

        self._check_the_db_after_recover(last_block_before_close, is_start_block)

    def test_close_only_standby_exists_on_the_start(self):
        # Success case: Iconservice is closed after changing current db to standby db,
        # should change stanby db to iiss db and create new current db (That is before commit data to rc db)
        self.make_blocks_to_end_calculation()
        is_start_block: bool = True
        last_block_before_close: int = self._get_last_block_from_icon_service()
        rc_version: int = 2

        precommit_data: 'PrecommitData' = self._get_precommit_data_after_invoke()
        wal_writer, state_wal, iiss_wal = self._get_wal_writer(precommit_data, is_start_block)
        self._write_batch_to_wal(wal_writer, state_wal, iiss_wal, is_start_block)
        # Change the current_db to standby_db
        RewardCalcStorage.rename_current_db_to_standby_db(self.rc_data_path, last_block_before_close, rc_version)

        # Remove all iiss_db
        self._remove_all_iiss_db_before_reopen()
        self._close_and_reopen_iconservice()

        self._check_the_db_after_recover(last_block_before_close, is_start_block)

    def test_close_standby_and_current_exists_on_the_start(self):
        # Success case: Iconservice is closed after changing current db to standby db and create new current db,
        # should change standby db to iiss db  (That is before commit data to rc db)
        self.make_blocks_to_end_calculation()
        is_start_block: bool = True
        last_block_before_close: int = self._get_last_block_from_icon_service()
        rc_version: int = 2

        precommit_data: 'PrecommitData' = self._get_precommit_data_after_invoke()
        wal_writer, state_wal, iiss_wal = self._get_wal_writer(precommit_data, is_start_block)
        self._write_batch_to_wal(wal_writer, state_wal, iiss_wal, is_start_block)
        # Change the current_db to standby_db
        RewardCalcStorage.rename_current_db_to_standby_db(self.rc_data_path, last_block_before_close, rc_version)
        RewardCalcStorage.create_current_db(self.rc_data_path)

        # Remove all iiss_db
        self._remove_all_iiss_db_before_reopen()
        self._close_and_reopen_iconservice()

        self._check_the_db_after_recover(last_block_before_close, is_start_block)

    def test_close_before_sending_calculate_on_the_start(self):
        # Success case: Iconservice is closed after changing current db to iiss db and create new current db,
        # should not recover.
        self.make_blocks_to_end_calculation()
        is_start_block: bool = True
        last_block_before_close: int = self._get_last_block_from_icon_service()
        rc_version: int = 2

        precommit_data: 'PrecommitData' = self._get_precommit_data_after_invoke()
        context: 'IconScoreContext' = self._get_commit_context(precommit_data.block)
        wal_writer, state_wal, iiss_wal = self._get_wal_writer(precommit_data, is_start_block)
        self._write_batch_to_wal(wal_writer, state_wal, iiss_wal, is_start_block)

        # Finish the iiss commit
        standby_db_path = self.icon_service_engine._process_iiss_commit(context,
                                                                        precommit_data,
                                                                        iiss_wal,
                                                                        is_start_block)
        wal_writer.write_state(WALState.WRITE_RC_DB.value, add=True)
        wal_writer.flush()

        # Finish the state commit
        self.icon_service_engine._process_state_commit(context, precommit_data, state_wal)
        wal_writer.write_state(WALState.WRITE_STATE_DB.value, add=True)
        wal_writer.flush()

        # Remove all iiss_db
        self._remove_all_iiss_db_before_reopen()
        # Change the standby db to iiss_db
        RewardCalcStorage.rename_standby_db_to_iiss_db(standby_db_path.path)
        self._close_and_reopen_iconservice()

        self._check_the_db_after_recover(last_block_before_close, is_start_block)
