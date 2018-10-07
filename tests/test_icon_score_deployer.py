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
from tests import create_address, create_tx_hash

DIRECTORY_PATH = os.path.abspath(os.path.dirname(__file__))


class TestIconScoreDeployer(unittest.TestCase):

    def setUp(self):
        self.deployer = IconScoreDeployer('./')
        self.address = create_address(AddressPrefix.CONTRACT)
        self.archive_path = os.path.join(DIRECTORY_PATH, 'sample','valid.zip')
        self.archive_path2 = os.path.join(DIRECTORY_PATH, 'sample', 'invalid.zip')
        self.archive_path3 = os.path.join(DIRECTORY_PATH, 'sample', 'valid.zip')
        self.score_root_path = os.path.join(self.deployer.score_root_path, str(self.address.to_bytes().hex()))
        self.deployer2 = IconScoreDeployer('/')

    @staticmethod
    def read_zipfile_as_byte(archive_path: str) -> bytes:
        with open(archive_path, 'rb') as f:
            byte_data = f.read()
            return byte_data

    def test_install(self):
        # Case when the user install SCORE first time.
        tx_hash1 = create_tx_hash()
        self.deployer.deploy(self.address, self.read_zipfile_as_byte(self.archive_path), tx_hash1)
        converted_tx_hash = f'0x{bytes.hex(tx_hash1)}'
        install_path = os.path.join(self.score_root_path, converted_tx_hash)
        zip_file_info_gen = self.deployer._extract_files_gen(self.read_zipfile_as_byte(self.archive_path))
        file_path_list = [name for name, info, parent_dir in zip_file_info_gen]

        installed_contents = []
        for directory, dirs, filename in os.walk(install_path):
            parent_directory_index = directory.rfind('/')
            parent_dir_name = directory[parent_directory_index + 1:]
            for file in filename:
                if parent_dir_name == f'0x{bytes.hex(tx_hash1)}':
                    installed_contents.append(file)
                else:
                    installed_contents.append(f'{parent_dir_name}/{file}')
        self.assertEqual(True, os.path.exists(install_path))
        self.assertTrue(installed_contents.sort() == file_path_list.sort())

        # Case when the user install SCORE second time.
        with self.assertRaises(BaseException) as e:
            self.deployer.deploy(self.address, self.read_zipfile_as_byte(self.archive_path), tx_hash1)
        self.assertEqual(e.exception.code, ExceptionCode.INVALID_PARAMS)

        # Case when installing SCORE with badzipfile Data.
        tx_hash2 = create_tx_hash()
        with self.assertRaises(BaseException) as e:
            self.deployer.deploy(self.address, self.read_zipfile_as_byte(self.archive_path2), tx_hash2)
        self.assertEqual(e.exception.code, ExceptionCode.INVALID_PARAMS)
        converted_tx_hash = f'0x{bytes.hex(tx_hash2)}'
        install_path2 = os.path.join(self.score_root_path, converted_tx_hash)
        self.assertFalse(os.path.exists(install_path2))

        # Case when The user specifies an installation path that does not have permission.
        with self.assertRaises(BaseException) as e:
            self.deployer2.deploy(self.address, self.read_zipfile_as_byte(self.archive_path), tx_hash1)
        self.assertIsInstance(e.exception, PermissionError)

        # Case when the user try to install scores without directories.
        tx_hash3 = create_tx_hash()
        converted_tx_hash = f'0x{bytes.hex(tx_hash3)}'
        self.deployer.deploy(self.address, self.read_zipfile_as_byte(self.archive_path3), tx_hash3)
        install_path3 = os.path.join(self.score_root_path, converted_tx_hash)
        self.assertEqual(True, os.path.exists(install_path3))

    def test_remove_existing_score(self):
        tx_hash = create_tx_hash()
        converted_tx_hash = f'0x{bytes.hex(tx_hash)}'
        install_path = os.path.join(self.score_root_path, converted_tx_hash)
        self.deployer.deploy(self.address, self.read_zipfile_as_byte(self.archive_path), tx_hash)
        self.deployer.remove_existing_score(install_path)
        self.assertFalse(os.path.exists(install_path))

    def test_deploy_when_score_depth_is_different(self):
        """
        Reads all files from the depth lower than where the file 'package.json' is
        and test deploying successfully.
        """
        zip_list = ["valid.zip", "sample_token.zip", "sample_token01.zip", 'test_score01.zip',
                    'test_score02.zip', 'test_score02_2.zip']
        for zip in zip_list:
            self.deployer = IconScoreDeployer('./')
            self.address = create_address(AddressPrefix.CONTRACT)
            self.archive_path = os.path.join(DIRECTORY_PATH, 'sample', zip)
            self.score_root_path = os.path.join(self.deployer.score_root_path, str(self.address.to_bytes().hex()))
            tx_hash1 = create_tx_hash()
            self.deployer.deploy(self.address, self.read_zipfile_as_byte(self.archive_path), tx_hash1)
            converted_tx_hash = f'0x{bytes.hex(tx_hash1)}'
            install_path = os.path.join(self.score_root_path, converted_tx_hash)
            zip_file_info_gen = self.deployer._extract_files_gen(self.read_zipfile_as_byte(self.archive_path))
            file_path_list = [name for name, info, parent_dir in zip_file_info_gen]

            installed_contents = []
            for directory, dirs, filename in os.walk(install_path):
                parent_directory_index = directory.rfind('/')
                parent_dir_name = directory[parent_directory_index + 1:]
                for file in filename:
                    if parent_dir_name == f'0x{bytes.hex(tx_hash1)}':
                        installed_contents.append(file)
                    else:
                        installed_contents.append(f'{parent_dir_name}/{file}')
            self.assertEqual(True, os.path.exists(install_path))
            self.assertTrue(installed_contents.sort() == file_path_list.sort())
            IconScoreDeployer.remove_existing_score(self.score_root_path)

    def tearDown(self):
        IconScoreDeployer.remove_existing_score(self.score_root_path)


if __name__ == "__main__":
    unittest.main()
