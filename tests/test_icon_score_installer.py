# -*- coding: utf-8 -*-

# Copyright 2017-2018 theloop Inc.
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
from iconservice.iconscore.icon_score_installer import *
from iconservice.base.address import Address


class TestIConScoreInstaller(unittest.TestCase):
    def setUp(self):
        self.installer = IconScoreInstaller('./')
        self.address = Address.from_string('cx' + '1'*40)
        self.archive_path = "tests/test.zip"
        self.archive_path2 = "tests/test_bad.zip"
        self.archive_path3 = "tests/test_uncovered.zip"
        self.score_root_path = os.path.join(self.installer.icon_score_root_path, str(self.address))

        self.installer2 = IconScoreInstaller('/')

    def tearDown(self):
        IconScoreInstaller.remove_existing_score(self.score_root_path)

    @staticmethod
    def read_zipfile_as_byte(archive_path: 'str') -> 'bytes':
        with open(archive_path, 'rb') as f:
            byte_data = f.read()
            return byte_data

    def test_install(self):
        # Case when the user install SCORE first time.
        block_height1, transaction_index1 = 1234, 12
        score_id = str(block_height1) + "_" + str(transaction_index1)
        ret1 = self.installer.install(self.address, self.read_zipfile_as_byte(self.archive_path),
                                      block_height1, transaction_index1)
        install_path = os.path.join(self.score_root_path, score_id)
        zip_file_info_gen = self.installer.extract_files_gen(self.read_zipfile_as_byte(self.archive_path))
        file_path_list = [name for name, info, parent_dir in zip_file_info_gen]

        installed_contents = []
        for directory, dirs, filename in os.walk(install_path):
            parent_directory_index = directory.rfind('/')
            parent_dir_name = directory[parent_directory_index+1:]
            for file in filename:
                if parent_dir_name == score_id:
                    installed_contents.append(file)
                else:
                    installed_contents.append(f'{parent_dir_name}/{file}')
        self.assertEqual(True, os.path.exists(install_path))
        self.assertTrue(ret1)
        self.assertTrue(installed_contents.sort() == file_path_list.sort())

        # Case when the user install SCORE second time.
        ret2 = self.installer.install(self.address, self.read_zipfile_as_byte(self.archive_path),
                                      block_height1, transaction_index1)
        self.assertFalse(ret2)

        # Case when installing SCORE with badzipfile Data.
        block_height2, transaction_index2 = 123, 13
        score_id2 = str(block_height2) + "_" + str(transaction_index2)
        ret3 = self.installer.install(self.address, self.read_zipfile_as_byte(self.archive_path2),
                                      block_height2, transaction_index2)
        install_path2 = os.path.join(self.score_root_path, score_id2)
        self.assertFalse(ret3)
        self.assertFalse(os.path.exists(install_path2))

        # Case when The user specifies an installation path that does not have permission.
        ret4 = self.installer2.install(self.address, self.read_zipfile_as_byte(self.archive_path),
                                       block_height1, transaction_index1)
        self.assertFalse(ret4)


        # Case when the user try to install scores without directories.

        ret5 = self.installer.install(self.address, self.read_zipfile_as_byte(self.archive_path3),
                                      block_height1, transaction_index2)
        score_id3 = str(block_height1) + "_" + str(transaction_index2)
        install_path3 = os.path.join(self.score_root_path, score_id3)
        self.assertEqual(True, os.path.exists(install_path3))

    def test_remove_existing_score(self):
        block_height1, transaction_index1 = 1234, 12
        score_id = str(block_height1) + "_" + str(transaction_index1)
        install_path = os.path.join(self.score_root_path, score_id)
        self.installer.install(self.address, self.read_zipfile_as_byte(self.archive_path),
                               block_height1, transaction_index1)
        self.installer.remove_existing_score(install_path)
        self.assertFalse(os.path.exists(install_path))


if __name__ == "__main__":
    unittest.main()
