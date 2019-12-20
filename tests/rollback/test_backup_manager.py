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

import hashlib
import os
import shutil
import unittest
from collections import OrderedDict

from iconservice.base.block import Block
from iconservice.rollback.backup_manager import BackupManager
from iconservice.database.db import KeyValueDatabase
from iconservice.rollback.rollback_manager import RollbackManager
from iconservice.database.wal import WriteAheadLogReader, WALDBType
from iconservice.icon_constant import Revision
from iconservice.iiss.reward_calc.storage import Storage as RewardCalcStorage


def _create_dummy_data(count: int) -> OrderedDict:
    data = OrderedDict()

    for i in range(count):
        key: bytes = f"key{i}".encode()
        value: bytes = f"value{i}".encode()
        data[key] = value

    return data


def _create_rc_db(rc_data_path: str) -> 'KeyValueDatabase':
    return RewardCalcStorage.create_current_db(rc_data_path)


class TestBackupManager(unittest.TestCase):
    def setUp(self) -> None:
        state_db_root_path = "./test_backup_manager_db"
        shutil.rmtree(state_db_root_path, ignore_errors=True)

        state_db_path = os.path.join(state_db_root_path, "icon_dex")
        rc_data_path = os.path.join(state_db_root_path, "iiss")
        backup_root_path = os.path.join(state_db_root_path, "backup")

        os.mkdir(state_db_root_path)
        os.mkdir(rc_data_path)
        os.mkdir(backup_root_path)

        org_state_db_data = _create_dummy_data(3)
        icx_db = KeyValueDatabase.from_path(state_db_path, create_if_missing=True)
        icx_db.write_batch(org_state_db_data.items())

        org_rc_db_data = _create_dummy_data(0)
        rc_db = _create_rc_db(rc_data_path)
        rc_db.write_batch(org_rc_db_data.items())

        self.backup_manager = BackupManager(
            backup_root_path=backup_root_path,
            rc_data_path=rc_data_path
        )

        self.rollback_manager = RollbackManager(
            backup_root_path=backup_root_path,
            rc_data_path=rc_data_path,
            state_db=icx_db
        )

        self.state_db_root_path = state_db_root_path
        self.backup_root_path = backup_root_path
        self.rc_data_path = rc_data_path

        self.state_db = icx_db
        self.org_state_db_data = org_state_db_data

        self.rc_db = rc_db
        self.org_rc_db_data = org_rc_db_data

    def tearDown(self) -> None:
        if self.state_db:
            self.state_db.close()
            self.state_db = None

        if self.rc_db:
            self.rc_db.close()
            self.rc_db = None

        shutil.rmtree(self.state_db_root_path, ignore_errors=True)

    def test_run(self):
        backup_manager = self.backup_manager
        block_hash: bytes = hashlib.sha3_256(b"block_hash").digest()
        prev_hash: bytes = hashlib.sha3_256(b"prev_hash").digest()
        instant_block_hash: bytes = hashlib.sha3_256(b"instant_block_hash").digest()

        revision = Revision.DECENTRALIZATION.value
        last_block = Block(
            block_height=100,
            block_hash=block_hash,
            timestamp=0,
            prev_hash=prev_hash,
            cumulative_fee=0
        )
        block_batch = OrderedDict()
        block_batch[b"key0"] = b"new value0"    # Update
        block_batch[b"key1"] = None             # Delete
        block_batch[b"key2"] = b"value2"        # Update with the same value
        block_batch[b"key3"] = b"value3"        # Add a new entry

        is_calc_period_start_block = False

        rc_batch = OrderedDict()
        rc_batch[b"key0"] = b"hello"

        backup_manager.run(icx_db=self.state_db,
                           rc_db=self.rc_db,
                           revision=revision,
                           prev_block=last_block,
                           block_batch=block_batch,
                           iiss_wal=rc_batch.items(),
                           is_calc_period_start_block=is_calc_period_start_block,
                           instant_block_hash=instant_block_hash)

        self._commit_state_db(self.state_db, block_batch)
        self._commit_rc_db(self.rc_db, rc_batch)
        self._rollback(last_block)
        self._check_if_rollback_is_done(self.rc_db, self.org_rc_db_data)
        self._check_if_rollback_is_done(self.state_db, self.org_state_db_data)

        self._commit_state_db(self.state_db, block_batch)
        self._commit_rc_db(self.rc_db, rc_batch)
        self.rc_db.close()
        self.rc_db = None
        self._rollback_with_rollback_manager(last_block)

        self.rc_db = _create_rc_db(self.rc_data_path)
        self._check_if_rollback_is_done(self.rc_db, self.org_rc_db_data)
        self._check_if_rollback_is_done(self.state_db, self.org_state_db_data)

    @staticmethod
    def _commit_state_db(db: 'KeyValueDatabase', block_batch: OrderedDict):
        db.write_batch(block_batch.items())

        for key in block_batch:
            assert block_batch[key] == db.get(key)

    @staticmethod
    def _commit_rc_db(db: 'KeyValueDatabase', rc_batch: OrderedDict):
        db.write_batch(rc_batch.items())

        count = 0
        for key in rc_batch:
            assert rc_batch[key] == db.get(key)
            count += 1

        assert len(rc_batch) == count

    def _rollback(self, last_block: 'Block'):
        backup_path = os.path.join(self.backup_root_path, f"block-{last_block.height}.bak")

        reader = WriteAheadLogReader()
        reader.open(backup_path)

        self.rc_db.write_batch(reader.get_iterator(WALDBType.RC.value))
        self.state_db.write_batch(reader.get_iterator(WALDBType.STATE.value))

        reader.close()

    @staticmethod
    def _check_if_rollback_is_done(db: 'KeyValueDatabase', prev_state: OrderedDict):
        i = 0
        for key, value in db.iterator():
            assert value == prev_state[key]
            i += 1

        assert i == len(prev_state)

    def _rollback_with_rollback_manager(self, last_block: 'Block'):
        rollback_manager = self.rollback_manager
        last_block_height = last_block.height + 1
        rollback_block_height = last_block.height

        # One block rollback
        ret = rollback_manager.run(
            last_block_height,
            rollback_block_height,
            term_start_block_height=rollback_block_height - 1)
        assert ret is None
