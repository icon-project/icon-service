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
import io
import logging
import os
import zipfile
import shutil

from icon.iconservice.base.address import Address
from icon.iconservice.base.exception import ScoreInstallException


class IconScoreInstaller(object):
    """Score installer.
    """

    def __init__(self, icon_score_root_path: 'str') -> 'None':
        self.icon_score_root_path = icon_score_root_path

    def install(self, address: 'Address', data: 'bytes', block_height: 'int', transaction_index: 'int') -> 'bool':
        """Install score.

        :param address: contract address
        :param data: The byte value of the zip file.
        :param block_height:
        :param transaction_index:
        :return:
        """
        str_block_height = str(block_height)
        str_transaction_index = str(transaction_index)
        str_address = str(address)
        score_id = str_block_height + "_" + str_transaction_index
        score_root_path = os.path.join(self.icon_score_root_path, str_address)
        install_path = os.path.join(score_root_path, score_id)
        try:
            if os.path.isfile(install_path):
                raise ScoreInstallException

            if not os.path.exists(install_path):
                os.makedirs(install_path)

            file_info_generator = IconScoreInstaller.extract_files_gen(data)

            for name, file_info, parent_directory in file_info_generator:
                if not os.path.exists(os.path.join(install_path, parent_directory)):
                    os.makedirs(os.path.join(install_path, parent_directory))
                with file_info as file_info_context, open(os.path.join(install_path, name), 'wb') as dest:
                    dest.write(file_info_context.read())
            return True
        except ScoreInstallException as e:
            print(e.message)
            return False
        except PermissionError as pe:
            print(pe)
            return False

    @staticmethod
    def extract_files_gen(data: 'bytes'):
        with zipfile.ZipFile(io.BytesIO(data)) as memory_zip:
            for zip_info in memory_zip.infolist():
                with memory_zip.open(zip_info) as file:
                    file_path = zip_info.filename
                    if file_path.find('__MACOSX') != -1:
                        continue
                    if file_path.find('__pycache__') != -1:
                        continue
                    file_name_start_index = file_path.rfind('/')
                    if file_name_start_index == len(file_path)-1:
                        # continue when 'file_path' is a directory.
                        continue
                    if file_path.find('/.') != -1:
                        # continue when 'file_path' is hidden directory or hidden file.
                        continue
                    parent_directory = file_path[:file_name_start_index]
                    yield zip_info.filename, file, parent_directory

    @staticmethod
    def remove_exists_archive(archive_path: 'str') -> 'None':
        """Remove archive file.

        :param archive_path: The path of SCORE archive.
        :return:
        """
        if os.path.isfile(archive_path):
            os.remove(archive_path)
        elif os.path.isdir(archive_path):
            shutil.rmtree(archive_path)

    # This method will be removed. written for test.
    @staticmethod
    def read_zipfile_as_byte(archive_path: 'str') -> 'bytes':
        with open(archive_path, 'rb') as f:
            byte_data = f.read()
            return byte_data


def main():
    installer = IconScoreInstaller('./')
    address = Address.from_string('cx1234123412341234123412341234123412342134')
    installer.install(address, IconScoreInstaller.read_zipfile_as_byte('effectivePython.zip'), 124, 12)


if __name__ == "__main__":
    main()
