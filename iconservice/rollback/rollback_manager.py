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
from typing import TYPE_CHECKING, Iterable, Optional, Tuple

from iconcommons.logger import Logger
from .backup_manager import get_backup_filename
from ..base.exception import InvalidParamsException, InternalServiceErrorException
from ..database.db import KeyValueDatabase
from ..database.wal import WriteAheadLogReader, WALDBType
from ..icon_constant import ROLLBACK_LOG_TAG
from ..iiss.reward_calc import RewardCalcStorage
from ..iiss.reward_calc.msg_data import make_block_produce_info_key

if TYPE_CHECKING:
    from iconservice.database.db import KeyValueDatabase


TAG = ROLLBACK_LOG_TAG


class RollbackManager(object):
    """Rollback the current state to the one block previous one with a backup file

    Assume that the rollback of Reward Calculator has been already done
    Related databases: state_db, iiss_db
    """

    def __init__(self, backup_root_path: str, rc_data_path: str, state_db: 'KeyValueDatabase'):
        self._backup_root_path = backup_root_path
        self._rc_data_path = rc_data_path
        self._state_db = state_db

    def run(self, last_block_height: int, rollback_block_height: int, term_start_block_height: int):
        """Rollback to the previous block state

        :param last_block_height: the last confirmed block height
        :param rollback_block_height: the height of block to rollback to
        :param term_start_block_height: the start block height of the current term
        """
        Logger.info(tag=TAG, msg=f"run() start: "
                                 f"last_block_height={last_block_height} "
                                 f"rollback_block_height={rollback_block_height} "
                                 f"term_start_block_height={term_start_block_height}")

        self._validate_block_heights(last_block_height, rollback_block_height, term_start_block_height)

        term_change_exists = \
            self._term_change_exists(last_block_height, rollback_block_height, term_start_block_height)
        calc_end_block_height = term_start_block_height - 1
        reader = WriteAheadLogReader()
        state_db_batch = {}
        iiss_db_batch = {}

        for block_height in range(last_block_height - 1, rollback_block_height - 1, -1):
            # Make backup file with a given block_height
            path: str = self._get_backup_file_path(block_height)
            if not os.path.isfile(path):
                raise InternalServiceErrorException(f"Backup file not found: {path}")

            reader.open(path)

            # Merge backup data into state_db_batch
            self._write_batch(reader.get_iterator(WALDBType.STATE.value), state_db_batch)

            # Merge backup data into iiss_db_batch
            if not (term_change_exists and block_height > calc_end_block_height):
                self._write_batch(reader.get_iterator(WALDBType.RC.value), iiss_db_batch)

            reader.close()

        # If a term change is detected during rollback, handle the exceptions below
        if term_change_exists:
            self._remove_block_produce_info(iiss_db_batch, calc_end_block_height)
            self._rename_iiss_db_to_current_db(calc_end_block_height)

        # Commit write_batch to db
        self._commit_batch(state_db_batch, self._state_db)
        iiss_db = RewardCalcStorage.create_current_db(self._rc_data_path)
        self._commit_batch(iiss_db_batch, iiss_db)
        iiss_db.close()

        Logger.info(tag=TAG, msg="run() end")

    @staticmethod
    def _validate_block_heights(last_block_height: int, rollback_block_height: int, term_start_block_height: int):
        if last_block_height < 0:
            raise InvalidParamsException(f"Invalid lastBlockHeight: {last_block_height}")

        if rollback_block_height < 0:
            raise InvalidParamsException(f"Invalid rollbackBlockHeight: {rollback_block_height}")

        if term_start_block_height < 0:
            raise InvalidParamsException(f"Invalid termStartBlockHeight: {term_start_block_height}")

        if rollback_block_height >= last_block_height:
            raise InvalidParamsException(
                f"lastBlockHeight({last_block_height}) <= rollbackBlockHeight({rollback_block_height}")
        
    @staticmethod        
    def _term_change_exists(last_block_height: int, rollback_block_height: int, term_start_block_height: int) -> bool:
        return rollback_block_height < term_start_block_height <= last_block_height

    @staticmethod
    def _write_batch(it: Iterable[Tuple[bytes, Optional[bytes]]], batch: dict):
        for key, value in it:
            batch[key] = value

    @staticmethod
    def _commit_batch(batch: dict, db: 'KeyValueDatabase'):
        db.write_batch(batch.items())

    def _get_backup_file_path(self, block_height: int) -> str:
        """

        :param block_height: the height of block to rollback to
        :return: backup state file path
        """
        assert block_height >= 0

        filename = get_backup_filename(block_height)
        return os.path.join(self._backup_root_path, filename)

    @classmethod
    def _remove_backup_file(cls, path: str):
        try:
            os.remove(path)
        except FileNotFoundError:
            pass
        except BaseException as e:
            Logger.debug(tag=TAG, msg=str(e))

    def _rename_iiss_db_to_current_db(self, calc_end_block_height: int):
        """Rename iiss_db to current_db

        """
        Logger.debug(tag=TAG,
                     msg=f"_rename_iiss_db_to_current_db() start: calc_end_block_height={calc_end_block_height}")

        filename = RewardCalcStorage.get_iiss_rc_db_name(calc_end_block_height)
        src_path = os.path.join(self._rc_data_path, filename)
        dst_path = os.path.join(self._rc_data_path, RewardCalcStorage.CURRENT_IISS_DB_NAME)
        Logger.info(tag=TAG, msg=f"rename_iiss_db: src_path={src_path} dst_path={dst_path}")

        # Consider the case that renaming iiss_db to current_db has been already done
        if os.path.isdir(src_path):
            # Remove a new current_db
            shutil.rmtree(dst_path, ignore_errors=True)
            # Rename iiss_rc_db_{BH} to current_db
            shutil.move(src_path, dst_path)

        Logger.debug(tag=TAG, msg="_rename_iiss_db_to_current_db() end")

    @classmethod
    def _remove_block_produce_info(cls, iiss_db_batch: dict, block_height: int):
        """Remove block_produce_info of calc_period_end_block from current_db

        :param iiss_db_batch:
        :param block_height: the end block of the previous term
        :return:
        """
        Logger.debug(tag=TAG,
                     msg=f"_remove_block_produce_info() start: block_height={block_height}")

        # Remove the end calc block from iiss_db
        key: bytes = make_block_produce_info_key(block_height)
        iiss_db_batch[key] = None

        Logger.debug(tag=TAG, msg="_remove_block_produce_info() end")
