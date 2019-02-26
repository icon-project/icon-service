# -*- coding: utf-8 -*-

# Copyright 2018 ICON Foundation
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
import unittest

from iconservice.base.address import AddressPrefix
from iconservice.base.exception import ExceptionCode
from iconservice.deploy.icon_score_deployer import IconScoreDeployer
from iconservice.deploy.utils import remove_path, get_score_path, get_score_deploy_path
from iconservice.icon_constant import REVISION_2, REVISION_3
from tests import create_address, create_tx_hash

DIRECTORY_PATH = os.path.abspath(os.path.dirname(__file__))


class TestIconScoreDeployer(unittest.TestCase):

    def setUp(self):
        self.score_root_path = './'
        self.address: 'Address' = create_address(AddressPrefix.CONTRACT)
        self.score_path = get_score_path(self.score_root_path, self.address)

    @staticmethod
    def read_zipfile_as_byte(archive_path: str) -> bytes:
        with open(archive_path, 'rb') as f:
            byte_data = f.read()
            return byte_data

    def test_install(self):
        self.normal_score_path = os.path.join(DIRECTORY_PATH, 'sample', 'normal_score.zip')
        self.badzipfile_path = os.path.join(DIRECTORY_PATH, 'sample', 'badzipfile.zip')
        self.innerdir_path = os.path.join(DIRECTORY_PATH, 'sample', 'innerdir.zip')

        # Case when the user install SCORE first time.
        tx_hash1 = create_tx_hash()
        score_deploy_path: str = get_score_deploy_path(self.score_root_path, self.address, tx_hash1)
        IconScoreDeployer.deploy(score_deploy_path, self.read_zipfile_as_byte(self.normal_score_path))

        zip_file_info_gen = IconScoreDeployer._extract_files_gen(self.read_zipfile_as_byte(self.normal_score_path))
        file_path_list = [name for name, info, parent_dir in zip_file_info_gen]

        installed_contents = []
        for directory, dirs, filename in os.walk(score_deploy_path):
            parent_directory_index = directory.rfind('/')
            parent_dir_name = directory[parent_directory_index + 1:]
            for file in filename:
                if parent_dir_name == f'0x{bytes.hex(tx_hash1)}':
                    installed_contents.append(file)
                else:
                    installed_contents.append(f'{parent_dir_name}/{file}')
        self.assertEqual(True, os.path.exists(score_deploy_path))
        self.assertTrue(installed_contents.sort() == file_path_list.sort())

        # Case when the user install SCORE second time.(revision < 2)
        with self.assertRaises(BaseException) as e:
            IconScoreDeployer.deploy_legacy(score_deploy_path, self.read_zipfile_as_byte(self.normal_score_path))
        self.assertEqual(e.exception.code, ExceptionCode.INVALID_PARAMS)

        # Case when installing SCORE with badzipfile Data.
        tx_hash2 = create_tx_hash()
        score_deploy_path: str = get_score_deploy_path(self.score_root_path, self.address, tx_hash2)

        with self.assertRaises(BaseException) as e:
            IconScoreDeployer.deploy(score_deploy_path, self.read_zipfile_as_byte(self.badzipfile_path))
        self.assertEqual(e.exception.code, ExceptionCode.INVALID_PARAMS)
        self.assertFalse(os.path.exists(score_deploy_path))

        # Case when the user specifies an installation path that does not have permission.
        score_deploy_path: str = get_score_deploy_path('/', self.address, tx_hash1)
        with self.assertRaises(BaseException) as e:
            IconScoreDeployer.deploy(score_deploy_path, self.read_zipfile_as_byte(self.normal_score_path))
        self.assertIsInstance(e.exception, PermissionError)

        # Case when the user try to install scores inner directories.
        tx_hash3 = create_tx_hash()
        score_deploy_path: str = get_score_deploy_path(self.score_root_path, self.address, tx_hash3)
        IconScoreDeployer.deploy(score_deploy_path, self.read_zipfile_as_byte(self.innerdir_path))
        self.assertEqual(True, os.path.exists(score_deploy_path))

    def test_remove_existing_score(self):
        tx_hash: bytes = create_tx_hash()
        score_deploy_path: str = get_score_deploy_path(self.score_root_path, self.address, tx_hash)

        self.normal_score_path = os.path.join(DIRECTORY_PATH, 'sample', 'normal_score.zip')
        IconScoreDeployer.deploy(score_deploy_path, self.read_zipfile_as_byte(self.normal_score_path))
        remove_path(score_deploy_path)
        self.assertFalse(os.path.exists(score_deploy_path))

    def test_deploy_when_score_depth_is_different(self):
        """
        Reads all files from the depth lower than where the file 'package.json' is
        and test deploying successfully.
        """
        zip_list = ['score_registry.zip', 'fakedir.zip']

        for zip_item in zip_list:
            address: 'Address' = create_address(AddressPrefix.CONTRACT)
            self.archive_path = os.path.join(DIRECTORY_PATH, 'sample', zip_item)
            tx_hash1 = create_tx_hash()
            score_deploy_path: str = get_score_deploy_path(self.score_root_path, address, tx_hash1)

            IconScoreDeployer.deploy(score_deploy_path, self.read_zipfile_as_byte(self.archive_path))

            zip_file_info_gen = IconScoreDeployer._extract_files_gen(self.read_zipfile_as_byte(self.archive_path))
            file_path_list = [name for name, info, parent_dir in zip_file_info_gen]

            installed_contents = []
            for directory, dirs, filename in os.walk(score_deploy_path):
                parent_directory_index = directory.rfind('/')
                parent_dir_name = directory[parent_directory_index + 1:]
                for file in filename:
                    if parent_dir_name == f'0x{bytes.hex(tx_hash1)}':
                        installed_contents.append(file)
                    else:
                        installed_contents.append(f'{parent_dir_name}/{file}')

            self.assertEqual(True, os.path.exists(score_deploy_path))
            self.assertTrue(installed_contents.sort() == file_path_list.sort())

            score_path: str = get_score_path(self.score_root_path, address)
            remove_path(score_path)

    def test_deploy_replace_once(self):
        """
        Test for replacing the first occurrence only of the path which is upper than package.json
        by using count on the function `replace`. It is supported on revision_3_or_more.
        """
        revision_list = [REVISION_2, REVISION_3]
        for revision in revision_list:
            address: 'Address' = create_address(AddressPrefix.CONTRACT)
            self.archive_path = os.path.join(DIRECTORY_PATH, 'sample', 'score_registry.zip')
            zip_file_info_gen = IconScoreDeployer._extract_files_gen(self.read_zipfile_as_byte(self.archive_path), revision)
            file_path_list = [name for name, info, parent_dir in zip_file_info_gen]
            file_path_list.sort()
            file_path_list_for_revision_2 = ["__init__.py", "score_registry.py"]
            file_path_list_for_revision_3_or_more = ["score_registry/__init__.py", "score_registry/score_registry.py"]
            if revision == REVISION_2:
                target_file_path_list_only_for_revision_2 = [file_path for file_path in file_path_list if file_path in file_path_list_for_revision_2]
                self.assertEqual(file_path_list_for_revision_2, target_file_path_list_only_for_revision_2)
                target_file_path_list = [file_path for file_path in file_path_list
                                         if file_path not in file_path_list_for_revision_3_or_more]
            else:
                target_file_path_list_only_for_revision_3_or_more = [file_path for file_path in file_path_list if file_path in file_path_list_for_revision_3_or_more]
                self.assertEqual(file_path_list_for_revision_3_or_more, target_file_path_list_only_for_revision_3_or_more)
                target_file_path_list = [file_path for file_path in file_path_list
                                         if file_path not in file_path_list_for_revision_2]
            self.assertEqual(file_path_list, target_file_path_list)
            score_path: str = get_score_path(self.score_root_path, address)
            remove_path(score_path)

    def tearDown(self):
        remove_path(self.score_path)


if __name__ == "__main__":
    unittest.main()
