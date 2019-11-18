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

import unittest
import shutil
import os
from collections import OrderedDict
import hashlib

from iconservice.icon_constant import Revision
from iconservice.database.backup_manager import BackupManager
from iconservice.database.db import KeyValueDatabase
from iconservice.base.block import Block


def _create_db(path) -> 'KeyValueDatabase':
    db = KeyValueDatabase.from_path(path, create_if_missing=True)

    for i in range(5):
        postfix: bytes = i.to_bytes(1, "big", signed=False)
        key: bytes = b"key" + postfix
        value: bytes = b"value" + postfix

        db.put(key, value)

    return db


class TestBackupManager(unittest.TestCase):
    def setUp(self) -> None:
        state_db_root_path = "./test_backup_manager_db"
        shutil.rmtree(state_db_root_path, ignore_errors=True)

        os.mkdir(state_db_root_path)

        state_db_path = os.path.join(state_db_root_path, "icon_dex")
        rc_data_path = os.path.join(state_db_root_path, "iiss")

        icx_db = _create_db(state_db_path)

        self.backup_manager = BackupManager(
            state_db_root_path=state_db_root_path,
            rc_data_path=rc_data_path,
            icx_db=icx_db
        )

        self._state_db_root_path = state_db_root_path
        self._icx_db = icx_db
        self.rc_db = KeyValueDatabase.from_path(rc_data_path)

    def tearDown(self) -> None:
        if self._icx_db:
            self._icx_db.close()
            self._icx_db = None

        if self.rc_db:
            self.rc_db.close()
            self.rc_db = None

        shutil.rmtree(self._state_db_root_path, ignore_errors=True)

    def test_run(self):
        backup_manager = self.backup_manager
        block_hash: bytes = hashlib.sha3_256(b"block_hash").digest()
        prev_hash: bytes = hashlib.sha3_256(b"prev_hash").digest()
        instant_block_hash: bytes = hashlib.sha3_256(b"instant_block_hash").digest()

        revision = Revision.DECENTRALIZATION.value
        rc_db = self.rc_db
        last_block = Block(
            block_height=100,
            block_hash=block_hash,
            timestamp=0,
            prev_hash=prev_hash,
            cumulative_fee=0
        )
        block_batch = OrderedDict()
        block_batch[b"key0"] = b"new value0"
        block_batch[b"key1"] = None
        block_batch[b"key2"] = b"value2"

        is_calc_period_start_block = False

        rc_data = OrderedDict()
        rc_data[b"key0"] = b"value0"

        def iiss_wal():
            for key in rc_data:
                yield key, rc_data[key]

        backup_manager.run(revision=revision,
                           rc_db=rc_db,
                           prev_block=last_block,
                           block_batch=block_batch,
                           iiss_wal=iiss_wal(),
                           is_calc_period_start_block=is_calc_period_start_block,
                           instant_block_hash=instant_block_hash)
