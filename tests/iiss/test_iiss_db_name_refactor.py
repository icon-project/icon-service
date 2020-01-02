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
from typing import Optional

from iconservice.iiss.reward_calc.storage import IissDBNameRefactor


class TestIissDBNameRefactor(unittest.TestCase):
    RC_DATA_PATH = "./for_iiss_db_name_refactor_test"

    def setUp(self) -> None:
        os.mkdir(self.RC_DATA_PATH)

        revision = random.randint(0, 10)
        block_height = random.randint(100, 10000000000)

        self.rc_data_path = self.RC_DATA_PATH
        self.new_name = self._get_new_db_name(block_height)
        self.old_name = self._get_old_db_name(block_height, revision)

    def tearDown(self) -> None:
        shutil.rmtree(self.RC_DATA_PATH, ignore_errors=True)

    def test_run(self):
        term_period = 43120
        rc_data_path = self.rc_data_path
        start_block_height = 12_690_545
        revision = 0
        size = 5

        # Make the directories whose name is old-fashioned
        for i in range(size):
            block_height = start_block_height + term_period * i

            old_name = self._get_old_db_name(block_height, revision)
            path = os.path.join(rc_data_path, old_name)
            os.mkdir(path)

        ret = IissDBNameRefactor.run(rc_data_path)
        assert ret == size

        # Check whether old-fashioned iiss_db names are changed to the new one
        for i in range(size):
            block_height = start_block_height + term_period * i

            new_name = self._get_new_db_name(block_height)
            path = os.path.join(rc_data_path, new_name)
            assert os.path.isdir(path)

    def test_run_with_already_renamed_db(self):
        term_period = 43120
        rc_data_path = self.rc_data_path
        start_block_height = 12_690_545
        size = 5

        # Make the directories whose name is old-fashioned
        for i in range(size):
            block_height = start_block_height + term_period * i

            name = self._get_new_db_name(block_height)
            path = os.path.join(rc_data_path, name)
            os.mkdir(path)

        # Make a new-fashioned db
        new_name = self._get_new_db_name(start_block_height + term_period * size)
        path = os.path.join(rc_data_path, new_name)
        os.mkdir(path)

        ret = IissDBNameRefactor.run(rc_data_path)
        assert ret == 0

        # Check whether old-fashioned iiss_db names are changed to the new one
        for i in range(size):
            block_height = start_block_height + term_period * i

            name = self._get_new_db_name(block_height)
            path = os.path.join(rc_data_path, name)
            assert os.path.isdir(path)

    def test__get_db_name_without_revision(self):
        new_name = self.new_name
        old_name = self.old_name

        name: Optional[str] = IissDBNameRefactor._get_db_name_without_revision(new_name)
        assert name is None

        name: Optional[str] = IissDBNameRefactor._get_db_name_without_revision(old_name)
        assert name == new_name

    def test__change_db_name_success(self):
        rc_data_path = self.rc_data_path
        old_name = self.old_name
        new_name = self.new_name

        old_path = os.path.join(rc_data_path, old_name)
        new_path = os.path.join(rc_data_path, new_name)

        os.mkdir(old_path)
        assert os.path.isdir(old_path)

        # Success case
        IissDBNameRefactor._change_db_name(rc_data_path, old_name, new_name)
        assert not os.path.exists(old_path)
        assert os.path.isdir(new_path)

    def test__change_db_name_failure(self):
        rc_data_path = self.rc_data_path
        old_name = self.old_name
        new_name = self.new_name

        old_path = os.path.join(rc_data_path, old_name)
        new_path = os.path.join(rc_data_path, new_name)

        os.mkdir(old_path)
        assert os.path.isdir(old_path)

        # Failure case 1: rename non-existent dir to new_name
        IissDBNameRefactor._change_db_name(rc_data_path, "no_dir", new_name)
        assert os.path.isdir(old_path)
        assert not os.path.exists(new_path)

        # Failure case 2: rename a dir to the same name
        IissDBNameRefactor._change_db_name(rc_data_path, old_name, old_name)
        assert os.path.isdir(old_path)
        assert not os.path.exists(new_path)

    @staticmethod
    def _get_old_db_name(block_height: int, revision: int) -> str:
        return f"{IissDBNameRefactor._DB_NAME_PREFIX}_{block_height}_{revision}"

    @staticmethod
    def _get_new_db_name(block_height: int) -> str:
        return f"{IissDBNameRefactor._DB_NAME_PREFIX}_{block_height}"
