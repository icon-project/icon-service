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
from typing import TYPE_CHECKING, Tuple

from iconcommons.logger import Logger

from .backup_manager import WALBackupState, get_backup_filename
from .db import KeyValueDatabase
from .wal import WriteAheadLogReader, WALDBType
from ..base.exception import DatabaseException
from ..icon_constant import ROLLBACK_LOG_TAG
from ..iiss.reward_calc import RewardCalcStorage
from ..iiss.reward_calc.msg_data import make_block_produce_info_key

if TYPE_CHECKING:
    from .db import KeyValueDatabase


TAG = ROLLBACK_LOG_TAG


class RollbackManager(object):
    def __init__(self, icx_db: 'KeyValueDatabase', state_db_root_path: str, rc_data_path: str):
        self._icx_db: 'KeyValueDatabase' = icx_db
        self._rc_data_path = rc_data_path
        self._root_path = os.path.join(state_db_root_path, "backup")

    def run(self, block_height: int = -1) -> Tuple[int, bool]:
        """Rollback to the previous block state

        Called on self.open()

        :param block_height: the height of block to rollback to
        :return: the height of block which is rollback to
        """
        Logger.debug(tag=TAG, msg=f"rollback() start: BH={block_height}")

        if block_height < 0:
            Logger.debug(tag=TAG, msg="rollback() end")
            return -1, False

        path: str = self._get_backup_file_path(block_height)
        if not os.path.isfile(path):
            Logger.info(tag=TAG, msg=f"backup state file not found: {path}")
            return -1, False

        block_height = -1
        is_calc_period_end_block = False
        reader = WriteAheadLogReader()

        try:
            reader.open(path)
            is_calc_period_end_block = \
                bool(WALBackupState(reader.state) & WALBackupState.CALC_PERIOD_END_BLOCK)

            if reader.log_count == 2:
                self._rollback_rc_db(reader, is_calc_period_end_block)
                self._rollback_state_db(reader)
                block_height = reader.block.height

        except BaseException as e:
            Logger.debug(tag=TAG, msg=str(e))
        finally:
            reader.close()

        # Remove backup file after rollback is done
        self._remove_backup_file(path)

        Logger.debug(tag=TAG, msg=f"rollback() end: return={block_height}")

        return block_height, is_calc_period_end_block

    def _get_backup_file_path(self, block_height: int) -> str:
        """

        :param block_height: the height of block to rollback to
        :return: backup state file path
        """
        assert block_height >= 0

        filename = get_backup_filename(block_height)
        return os.path.join(self._root_path, filename)

    def _rollback_rc_db(self, reader: 'WriteAheadLogReader', is_calc_period_end_block: bool):
        """Rollback the state of rc_db to the previous one

        :param reader:
        :param is_calc_period_end_block:
        :return:
        """
        if is_calc_period_end_block:
            Logger.info(tag=TAG, msg=f"BH-{reader.block.height} is a calc period end block")
            self._rollback_rc_db_on_end_block(reader)
        else:
            db: 'KeyValueDatabase' = RewardCalcStorage.create_current_db(self._rc_data_path)
            db.write_batch(reader.get_iterator(WALDBType.RC.value))
            db.close()

    def _rollback_rc_db_on_end_block(self, reader: 'WriteAheadLogReader'):
        """

        :param reader:
        :return:
        """

        current_rc_db_path, standby_rc_db_path, iiss_rc_db_path = \
            RewardCalcStorage.scan_rc_db(self._rc_data_path)
        # Assume that standby_rc_db does not exist
        assert standby_rc_db_path == ""

        current_rc_db_exists = len(current_rc_db_path) > 0
        iiss_rc_db_exists = len(iiss_rc_db_path) > 0

        if current_rc_db_exists:
            if iiss_rc_db_exists:
                # Remove the next calc_period current_rc_db and rename iiss_rc_db to current_rc_db
                shutil.rmtree(current_rc_db_path)
                os.rename(iiss_rc_db_path, current_rc_db_path)
        else:
            if iiss_rc_db_exists:
                # iiss_rc_db -> current_rc_db
                os.rename(iiss_rc_db_path, current_rc_db_path)
            else:
                # If both current_rc_db and iiss_rc_db do not exist, raise error
                raise DatabaseException(f"RC DB not found")

        self._remove_block_produce_info(current_rc_db_path, reader.block.height)

    def _rollback_state_db(self, reader: 'WriteAheadLogReader'):
        self._icx_db.write_batch(reader.get_iterator(WALDBType.STATE.value))

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
    def _remove_block_produce_info(cls, db_path: str, block_height: int):
        """Remove block_produce_info of calc_period_end_block from current_db

        :param db_path:
        :param block_height:
        :return:
        """
        key: bytes = make_block_produce_info_key(block_height)

        db = KeyValueDatabase.from_path(db_path, create_if_missing=False)
        db.delete(key)
        db.close()
