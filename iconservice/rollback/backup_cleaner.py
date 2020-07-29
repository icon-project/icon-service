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

__all__ = "BackupCleaner"

import os
import re

from iconcommons.logger import Logger
from . import get_backup_filename
from ..icon_constant import BACKUP_LOG_TAG, BACKUP_FILES

_TAG = BACKUP_LOG_TAG


class BackupCleaner(object):
    """Remove old backup files to rollback

    """

    def __init__(self, backup_root_path: str, backup_files: int):
        """

        :param backup_root_path: the directory where backup files are placed
        :param backup_files: the maximum backup files to keep
        """
        self._backup_root_path = backup_root_path
        self._backup_files = backup_files if backup_files > 0 else BACKUP_FILES
        self._regex_object = re.compile("^[\d]{10}.bak$")

    def run_on_init(self, current_block_height: int) -> int:
        """Clean up all stale backup files on iconservice startup

        :param current_block_height:
        :return:
        """
        Logger.debug(tag=_TAG, msg=f"run_on_init() start")

        ret = 0
        start_block_height = max(0, current_block_height - self._backup_files)

        with os.scandir(self._backup_root_path) as it:
            for entry in it:
                # backup filename: ex) 0000012345.bak
                if entry.is_file() and self._is_backup_filename_valid(entry.name):
                    block_height: int = self._get_block_height_from_filename(entry.name)
                    if block_height < 0:
                        continue

                    # Do nothing for the latest backup files
                    if start_block_height <= block_height < current_block_height:
                        continue

                    # Remove stale backup files
                    if self._remove_file(entry.path):
                        ret += 1

        Logger.debug(tag=_TAG, msg=f"run_on_init() end: ret={ret}")
        return ret

    @staticmethod
    def _get_block_height_from_filename(filename: str) -> int:
        try:
            return int(filename[:-4])
        except:
            pass

        return -1

    def _is_backup_filename_valid(self, filename: str) -> bool:
        return len(filename) == 14 and bool(self._regex_object.match(filename))

    def run_on_commit(self, current_block_height: int) -> int:
        """Remove the oldest backup file on commit

        :param: current_block_height
        :param: func: function to remove a file with path
        :return: the number of removed files
        """
        Logger.debug(tag=_TAG,
                     msg=f"run() start: current_block_height={current_block_height} "
                         f"backup_files={self._backup_files}")

        # Remove the oldest backup file only
        start_block_height = current_block_height - self._backup_files - 1
        ret = self.run(start_block_height, end_block_height=start_block_height)

        Logger.debug(tag=_TAG, msg="run() end")

        return ret

    def run(self, start_block_height: int, end_block_height: int) -> int:
        """Remove block backup files ranging from start_block_height to end_block_height inclusive

        :param start_block_height:
        :param end_block_height:
        :return: The number of removed files
        """
        Logger.debug(tag=_TAG, msg=f"run() start: start={start_block_height} end={end_block_height}")

        # Parameters sanity check
        if start_block_height < 0 or start_block_height > end_block_height:
            Logger.warning(tag=_TAG, msg=f"Invalid range: start={start_block_height} end={end_block_height}")
            return -1

        ret = 0

        # Remove block backup files ranging from start_block_height to end_block_height inclusive
        for block_height in range(start_block_height, end_block_height + 1):
            filename: str = get_backup_filename(block_height)
            path: str = os.path.join(self._backup_root_path, filename)

            # Remove a file ignoring any exceptions
            if self._remove_file(path):
                ret += 1

        Logger.info(tag=_TAG,
                    msg=f"Clean up old backup files: "
                        f"start={start_block_height} end={end_block_height} count={ret}")
        Logger.debug(tag=_TAG, msg=f"run() end: ret={ret}")

        return ret

    @staticmethod
    def _remove_file(path: str) -> bool:
        try:
            os.remove(path)
            return True
        except FileNotFoundError:
            pass
        except BaseException as e:
            Logger.warning(tag=_TAG, msg=str(e))

        return False
