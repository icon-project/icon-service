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
import os
import shutil

from iconservice.rollback.backup_cleaner import BackupCleaner
from iconservice.rollback import get_backup_filename
from iconservice.icon_constant import BACKUP_FILES


def _create_dummy_backup_files(backup_root_path: str, current_block_height: int, backup_files: int):
    for i in range(backup_files):
        block_height = current_block_height - i - 1
        if block_height < 0:
            break

        filename = get_backup_filename(block_height)
        path: str = os.path.join(backup_root_path, filename)
        open(path, "w").close()

        assert os.path.isfile(path)


def _check_if_backup_files_exists(backup_root_path: str, start_block_height, count, expected: bool):
    for i in range(count):
        block_height = start_block_height + i
        filename = get_backup_filename(block_height)
        path = os.path.join(backup_root_path, filename)

        assert os.path.exists(path) == expected


class TestBackupCleaner(unittest.TestCase):
    def setUp(self) -> None:
        backup_files = 10
        backup_root_path = os.path.join(os.path.dirname(__file__), "backup")
        os.mkdir(backup_root_path)

        backup_cleaner = BackupCleaner(backup_root_path, backup_files)

        self.backup_files = backup_files
        self.backup_root_path = backup_root_path
        self.backup_cleaner = backup_cleaner

    def tearDown(self) -> None:
        shutil.rmtree(self.backup_root_path)

    def test__init__(self):
        backup_cleaner = BackupCleaner("./haha", backup_files=-10)
        assert backup_cleaner._backup_files >= 0
        assert backup_cleaner._backup_files == BACKUP_FILES

    def test_run_with_too_many_backup_files(self):
        current_block_height = 101
        dummy_backup_files = 20
        backup_files = 10
        backup_root_path: str = self.backup_root_path
        backup_cleaner = BackupCleaner(backup_root_path, backup_files)

        # Create 20 dummy backup files: block-81.bak ... block-100.back
        _create_dummy_backup_files(backup_root_path, current_block_height, dummy_backup_files)

        # Remove block-81.bak ~ block-90.bak
        backup_cleaner.run(current_block_height)

        # Check if too old backup files are removed
        _check_if_backup_files_exists(backup_root_path, 81, 10, expected=False)

        # Check if the latest backup files exist (block-91.bak ~ block-100.bak)
        _check_if_backup_files_exists(backup_root_path, 91, 10, expected=True)

    def test_run_with_too_short_backup_files(self):
        current_block_height = 101
        dummy_backup_files = 5
        backup_files = 10
        backup_root_path: str = self.backup_root_path
        backup_cleaner = BackupCleaner(backup_root_path, backup_files)

        # Create 5 dummy backup files: block-96.bak ... block-100.back
        _create_dummy_backup_files(backup_root_path, current_block_height, dummy_backup_files)

        # No backup file will be removed
        backup_cleaner.run(current_block_height)

        # Check if the latest backup files exist (block-96.bak ~ block-100.bak)
        _check_if_backup_files_exists(backup_root_path, 96, 5, expected=True)


if __name__ == '__main__':
    unittest.main()
