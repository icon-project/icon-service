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
import random
import shutil
import unittest

from iconservice.icon_constant import BACKUP_FILES
from iconservice.rollback import get_backup_filename
from iconservice.rollback.backup_cleaner import BackupCleaner


def _get_backup_file_path(backup_root_path: str, block_height: int) -> str:
    filename = get_backup_filename(block_height)
    return os.path.join(backup_root_path, filename)


def _create_dummy_backup_files(
    backup_root_path: str, start_block_height: int, end_block_height: int
):
    for block_height in range(start_block_height, end_block_height + 1):
        if block_height < 0:
            break

        path: str = _get_backup_file_path(backup_root_path, block_height)
        _create_dummy_file(path)


def _create_dummy_file(path: str):
    open(path, "w").close()
    assert os.path.isfile(path)


def _check_if_backup_files_exists(
    backup_root_path: str,
    start_block_height: int,
    end_block_height: int,
    expected: bool,
):
    for block_height in range(start_block_height, end_block_height + 1):
        path: str = _get_backup_file_path(backup_root_path, block_height)
        assert os.path.exists(path) == expected


class TestBackupCleaner(unittest.TestCase):
    def setUp(self) -> None:
        backup_files = 10
        backup_root_path = os.path.join(os.path.dirname(__file__), "backup")

        shutil.rmtree(backup_root_path, ignore_errors=True)
        os.mkdir(backup_root_path)

        backup_cleaner = BackupCleaner(backup_root_path, backup_files)

        self.backup_files = backup_files
        self.backup_root_path = backup_root_path
        self.backup_cleaner = backup_cleaner

    def tearDown(self) -> None:
        shutil.rmtree(self.backup_root_path, ignore_errors=True)

    def test__init__(self):
        backup_cleaner = BackupCleaner("./haha", backup_files=-10)
        assert backup_cleaner._backup_files >= 0
        assert backup_cleaner._backup_files == BACKUP_FILES

    def test__get_block_height_from_filename(self):
        filenames = ["0123456789.bak", "tmp.bak", "12345.bak", "ff.bak", "011.bak"]
        expected_block_heights = [123456789, -1, 12345, -1, 11]

        for i in range(len(filenames)):
            block_height = BackupCleaner._get_block_height_from_filename(filenames[i])
            assert block_height == expected_block_heights[i]

    def test__is_backup_filename_valid(self):
        backup_root_path: str = self.backup_root_path
        backup_cleaner = BackupCleaner(backup_root_path, backup_files=10)

        filenames = [
            "0000000001.bak",
            "0123456789.bak",
            "tmp.bak",
            "12345.bak",
            "ff.bak",
            "000000001f.bak",
        ]
        expected_results = [True, True, False, False, False, False]

        for i in range(len(filenames)):
            result: bool = backup_cleaner._is_backup_filename_valid(filenames[i])
            assert result == expected_results[i]

    def test_run_on_commit_with_too_many_backup_files(self):
        current_block_height = 101
        backup_files = 10
        backup_root_path: str = self.backup_root_path
        backup_cleaner = BackupCleaner(backup_root_path, backup_files)

        # Create 20 dummy backup files: block-81.bak ... block-100.back
        _create_dummy_backup_files(backup_root_path, 81, 100)

        # Remove 0000000090.bak file only
        ret = backup_cleaner.run_on_commit(current_block_height)
        assert ret == 1

        # Check if 0000000090.bak is removed
        _check_if_backup_files_exists(backup_root_path, 90, 90, expected=False)

        _check_if_backup_files_exists(backup_root_path, 81, 89, expected=True)

        # Check if the latest backup files exist (block-91.bak ~ block-100.bak)
        _check_if_backup_files_exists(backup_root_path, 91, 100, expected=True)

    def test_run_on_commit_with_too_short_backup_files(self):
        current_block_height = 101
        backup_files = 10
        backup_root_path: str = self.backup_root_path
        backup_cleaner = BackupCleaner(backup_root_path, backup_files)

        # Create 5 dummy backup files: block-96.bak ... block-100.back
        _create_dummy_backup_files(backup_root_path, 96, 100)

        # No backup file will be removed
        ret = backup_cleaner.run_on_commit(current_block_height)
        assert ret == 0

        # Check if the latest backup files exist (block-96.bak ~ block-100.bak)
        _check_if_backup_files_exists(backup_root_path, 96, 100, expected=True)

    def test_run(self):
        backup_files = 10
        backup_root_path: str = self.backup_root_path
        backup_cleaner = BackupCleaner(backup_root_path, backup_files)

        # Create 100 dummy backup files: 101 ~ 200
        start_block_height = 101
        end_block_height = 200
        count = end_block_height - start_block_height + 1
        _create_dummy_backup_files(
            backup_root_path, start_block_height, end_block_height
        )

        # Remove all dummy backup files above: 101 ~ 200
        ret = backup_cleaner.run(start_block_height, end_block_height)
        assert ret == count

        # Check if the latest backup files exist (block-96.bak ~ block-100.bak)
        _check_if_backup_files_exists(
            backup_root_path, start_block_height, end_block_height, expected=False
        )

    def test_run_with_some_dropped_files(self):
        backup_files = 10
        backup_root_path: str = self.backup_root_path
        backup_cleaner = BackupCleaner(backup_root_path, backup_files)

        # Create 100 dummy backup files: 101 ~ 200
        start_block_height = 101
        end_block_height = 200
        count = end_block_height - start_block_height + 1
        _create_dummy_backup_files(
            backup_root_path, start_block_height, end_block_height
        )

        # Choose 5 block_heights randomly and remove them for test
        # Although block_heights are overlapped by accident, no problem
        dropped_block_heights = set()
        for _ in range(5):
            block_height = random.randint(start_block_height, end_block_height)
            dropped_block_heights.add(block_height)

        assert 0 < len(dropped_block_heights) <= 5

        for block_height in dropped_block_heights:
            path = _get_backup_file_path(backup_root_path, block_height)
            try:
                os.remove(path)
            except:
                pass

        # Remove all dummy backup files above: 101 ~ 200
        ret = backup_cleaner.run(start_block_height, end_block_height)
        assert ret == count - len(dropped_block_heights)

        # Check if the latest backup files exist (block-96.bak ~ block-100.bak)
        _check_if_backup_files_exists(
            backup_root_path, start_block_height, end_block_height, expected=False
        )

    def test_run_sanity_check(self):
        backup_files = 10
        backup_root_path: str = self.backup_root_path
        backup_cleaner = BackupCleaner(backup_root_path, backup_files)

        # Case 1: start_block_height < 0
        ret = backup_cleaner.run(start_block_height=-20, end_block_height=100)
        assert ret < 0

        # Case 2: end_block_height < 0
        ret = backup_cleaner.run(start_block_height=0, end_block_height=-1)
        assert ret < 0

        # Case 3: start_block_height > end_block_height
        ret = backup_cleaner.run(start_block_height=10, end_block_height=9)
        assert ret < 0

        # Case 4: start_block_height == end_block_height
        start_block_height = 10
        end_block_height = 10
        count = 1
        _create_dummy_backup_files(
            backup_root_path, start_block_height, end_block_height
        )

        ret = backup_cleaner.run(start_block_height, end_block_height)
        assert ret == count

        _check_if_backup_files_exists(
            backup_root_path, start_block_height, end_block_height, expected=False
        )

    def test_run_on_init(self):
        current_block_height = 101
        backup_files = 10
        backup_root_path: str = self.backup_root_path
        backup_cleaner = BackupCleaner(backup_root_path, backup_files)

        # Create 100 dummy backup files: 0 ~ 100
        _create_dummy_backup_files(backup_root_path, 0, 100)

        # Remove all stale backup files except for the latest ones: 91 ~ 100
        ret = backup_cleaner.run_on_init(current_block_height)
        assert ret == 91

        # Check if too old backup files are removed
        _check_if_backup_files_exists(backup_root_path, 0, 90, expected=False)

        # Check if the latest backup files exist (block-91.bak ~ block-100.bak)
        _check_if_backup_files_exists(backup_root_path, 91, 100, expected=True)

    def test_run_on_init_with_invalid_files(self):
        current_block_height = 101
        backup_files = 10
        backup_root_path: str = self.backup_root_path
        backup_cleaner = BackupCleaner(backup_root_path, backup_files)

        # Create 100 dummy backup files: 0 ~ 100
        _create_dummy_backup_files(backup_root_path, 81, 100)

        # Create invalid files
        filenames = [
            "10.bak",
            "tmp",
            "011.bak",
            "tmp123.bak",
            "000000001f.bak",
            "000000001F.bak",
        ]
        for filename in filenames:
            path = os.path.join(backup_root_path, filename)
            _create_dummy_file(path)

        # Remove all stale backup files except for the latest ones: 91 ~ 100
        ret = backup_cleaner.run_on_init(current_block_height)
        assert ret == 10

        # Check if too old backup files are removed
        _check_if_backup_files_exists(backup_root_path, 81, 90, expected=False)

        # Check if the latest backup files exist (block-91.bak ~ block-100.bak)
        _check_if_backup_files_exists(backup_root_path, 91, 100, expected=True)

        for filename in filenames:
            path = os.path.join(backup_root_path, filename)
            assert os.path.isfile(path)
