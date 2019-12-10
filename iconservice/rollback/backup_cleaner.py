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
        self._backup_files = backup_files if backup_files >= 0 else BACKUP_FILES

    def run(self, current_block_height: int) -> int:
        """Clean up old backup files

        :param: current_block_height
        :param: func: function to remove a file with path
        :return: the number of removed files
        """
        Logger.debug(tag=_TAG, msg=f"run() start: current_block_height={current_block_height}")

        ret = 0
        start = current_block_height - self._backup_files - 1

        try:
            for block_height in range(start, -1, -1):
                filename: str = get_backup_filename(block_height)
                path: str = os.path.join(self._backup_root_path, filename)
                os.remove(path)
                ret += 1
        except FileNotFoundError:
            pass
        except BaseException as e:
            Logger.debug(tag=_TAG, msg=str(e))

        Logger.info(tag=_TAG, msg=f"Clean up old backup files: start={start} count={ret}")
        Logger.debug(tag=_TAG, msg="run() end")

        return ret
