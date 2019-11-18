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
from enum import Flag
from typing import TYPE_CHECKING, Optional

from iconcommons import Logger
from .wal import WriteAheadLogWriter
from ..database.db import KeyValueDatabase
from ..icon_constant import ROLLBACK_LOG_TAG

if TYPE_CHECKING:
    from .wal import IissWAL
    from ..base.block import Block
    from ..database.batch import BlockBatch
    from ..precommit_data_manager import PrecommitData


TAG = ROLLBACK_LOG_TAG


def get_backup_filename(block_height: int) -> str:
    """

    :param block_height: the height of the block where we want to go back
    :return:
    """
    return f"block-{block_height}.bak"


class WALBackupState(Flag):
    CALC_PERIOD_END_BLOCK = 1


class BackupManager(object):
    """Backup and rollback for the previous block state

    """

    def __init__(self, state_db_root_path: str, rc_data_path: str, icx_db: 'KeyValueDatabase'):
        Logger.debug(tag=TAG,
                     msg=f"__init__() start: state_db_root_path={state_db_root_path}, "
                         f"rc_data_path={rc_data_path}")

        self._rc_data_path = rc_data_path
        self._root_path = os.path.join(state_db_root_path, "backup")
        self._icx_db = icx_db

        Logger.info(tag=TAG, msg=f"backup_root_path={self._root_path}")

        try:
            os.mkdir(self._root_path)
        except FileExistsError:
            pass

        Logger.debug(tag=TAG, msg="__init__() end")

    def _get_backup_file_path(self, block_height: int) -> str:
        """

        :param block_height: the height of block to rollback to
        :return: backup state file path
        """
        assert block_height >= 0

        filename = get_backup_filename(block_height)
        return os.path.join(self._root_path, filename)

    def run(self,
            revision: int,
            rc_db: 'KeyValueDatabase',
            prev_block: 'Block',
            block_batch: 'BlockBatch',
            iiss_wal: 'IissWAL',
            is_calc_period_start_block: bool,
            instant_block_hash: bytes):
        """Backup the previous block state

        :param revision:
        :param rc_db:
        :param prev_block: the latest confirmed block height during commit
        :param block_batch:
        :param iiss_wal:
        :param is_calc_period_start_block:
        :param instant_block_hash:
        :return:
        """
        Logger.debug(tag=TAG, msg="backup() start")

        path: str = self._get_backup_file_path(prev_block.height)
        Logger.info(tag=TAG, msg=f"backup_file_path={path}")

        self._clear_backup_files()

        writer = WriteAheadLogWriter(
            revision, max_log_count=2, block=prev_block, instant_block_hash=instant_block_hash)
        writer.open(path)

        if is_calc_period_start_block:
            writer.write_state(WALBackupState.CALC_PERIOD_END_BLOCK.value)

        self._backup_rc_db(writer, rc_db, iiss_wal)
        self._backup_state_db(writer, self._icx_db, block_batch)

        writer.close()

        Logger.debug(tag=TAG, msg="backup() end")

    def _clear_backup_files(self):
        try:
            with os.scandir(self._root_path) as it:
                for entry in it:
                    if entry.is_file() \
                            and entry.name.startswith("block-") \
                            and entry.name.endswith(".bak"):
                        path = os.path.join(self._root_path, entry.name)
                        self._remove_backup_file(path)
        except BaseException as e:
            Logger.info(tag=TAG, msg=str(e))

    @classmethod
    def _remove_backup_file(cls, path: str):
        try:
            os.remove(path)
        except FileNotFoundError:
            pass
        except BaseException as e:
            Logger.debug(tag=TAG, msg=str(e))

    @classmethod
    def _backup_rc_db(cls, writer: 'WriteAheadLogWriter', db: 'KeyValueDatabase', iiss_wal: 'IissWAL'):
        def get_rc_db_generator():
            for key, _ in iiss_wal:
                value: Optional[bytes] = db.get(key)
                yield key, value

        writer.write_walogable(get_rc_db_generator())

    @classmethod
    def _backup_state_db(cls, writer: 'WriteAheadLogWriter', db: 'KeyValueDatabase', block_batch: 'BlockBatch'):
        if block_batch is None:
            block_batch = {}

        def get_state_db_generator():
            for key in block_batch:
                value: Optional[bytes] = db.get(key)
                yield key, value

        writer.write_walogable(get_state_db_generator())
