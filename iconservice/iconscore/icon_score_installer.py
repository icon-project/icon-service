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
import os
import zipfile
import shutil

from icon.iconservice.base.address import Address

CONST_FILE_NOT_FOUND_ERROR_CODE = 912
CONST_IS_A_DIRECTORY_ERROR_CODE = 913
CONST_PERMISSION_ERROR_CODE = 914
CONST_NOT_A_DIRECTORY_ERROR_CODE = 915
CONST_BAD_ZIP_FILE_ERROR_CODE = 916
CONST_FILE_EXISTS_ERROR__CODE = 917


class IconScoreInstaller(object):
    """Score installer.
    """

    def __init__(self, icon_score_root_path: str) -> None:
        self.icon_score_root_path = icon_score_root_path

    def install(self, address: Address, data: bytes, block_height: int, transaction_index: int) -> None:
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
        install_path = os.path.join(self.icon_score_root_path, str_address, score_id)
        if not os.path.exists(str_address):
            os.makedirs(str_address)
        zip_path = IconScoreInstaller.write_zipfile_with_bytes(install_path, data)
        zip_root_directory_name = IconScoreInstaller.extract_files(self.icon_score_root_path, zip_path)

        IconScoreInstaller.remove_exists_archive(zip_path)
        shutil.move(os.path.join(self.icon_score_root_path, zip_root_directory_name),
                    os.path.join(self.icon_score_root_path, str(address)))

    @staticmethod
    def extract_files(install_path: str, archive_path: str) -> str:
        """Extract files from zip file.

        :param install_path: Path where score will be installed.
        :param archive_path: The archive_path of SCORE.
        :return:
        Will return root directory of SCORE.
        """
        try:
            zip_file = zipfile.ZipFile(archive_path, 'r')
            file_name_list = zip_file.namelist()
            file_name_prefix_list = [prefix.split('/')[0] for prefix in file_name_list
                                     if not prefix.startswith('__MACOSX')]
            is_zipfile_covered = all(a == file_name_prefix_list[0] for a in file_name_prefix_list)
            zip_root_name = file_name_list[0].split("/")[0]

            if is_zipfile_covered:
                IconScoreInstaller._extract_files(file_name_list, install_path, zip_file)
                return zip_root_name

            IconScoreInstaller._extract_files(file_name_list, install_path + '/temp', zip_file)
            return 'temp'

        except FileNotFoundError:
            print(f"{archive_path} not found. check file path.")
            return CONST_FILE_NOT_FOUND_ERROR_CODE
        except IsADirectoryError:
            print(f"{archive_path} is a directory. check file path.")
            return CONST_IS_A_DIRECTORY_ERROR_CODE
        except PermissionError:
            return CONST_PERMISSION_ERROR_CODE
        except NotADirectoryError:
            print(f"{install_path} is not a directory")
            return CONST_NOT_A_DIRECTORY_ERROR_CODE
        except zipfile.BadZipFile:
            print(f"{archive_path}, bad zip file.")
            return CONST_BAD_ZIP_FILE_ERROR_CODE
        finally:
            zip_file.close()

    @staticmethod
    def _extract_files(file_name_list: str, install_path: str, zip_file: object) -> None:
        """Methods used in the IconScoreInstaller.extract_files.

        :param file_name_list: List of file names inside the zip file.
        :param install_path: Path where score will be installed.
        :param zip_file: zipfile object.
        :return:
        """
        for file_name in file_name_list:
            if (not file_name.startswith("__MACOSX")) and file_name.find("__pycache__") == -1:
                zip_file.extract(file_name, install_path)

    @staticmethod
    def remove_exists_archive(archive_path: str) -> None:
        """Remove archive file.

        :param archive_path: The path of SCORE archive.
        :return:
        """
        if os.path.isfile(archive_path):
            os.remove(archive_path)
        elif os.path.isdir(archive_path):
            shutil.rmtree(archive_path)

    @staticmethod
    def write_zipfile_with_bytes(archive_path: str, byte_data: bytes):
        """Convert the bytes into a zip file.

        :param archive_path: The path of zip file.
        :param byte_data: The byte value of the zip file.
        :return:
        """
        if os.path.isfile(archive_path):
            print(f"{archive_path} file exists.")
            return CONST_FILE_EXISTS_ERROR__CODE
        try:
            with open(archive_path, 'wb') as f:
                f.write(byte_data)
            return archive_path
        except IsADirectoryError:
            print(f"{archive_path} is a directory. check file path.")
            return CONST_IS_A_DIRECTORY_ERROR_CODE
        except PermissionError:
            print(f"permission error")
            return CONST_PERMISSION_ERROR_CODE

    # This method will be removed. written for test.
    @staticmethod
    def read_zipfile_as_byte(archive_path: str) -> bytes:
        with open(archive_path, 'rb') as f:
            byte_data = f.read()
        return byte_data


def main():
    installer = IconScoreInstaller('./')
    address = Address.from_string("hx1234123412341234213412341234123412342134")
    installer.install(address, IconScoreInstaller.read_zipfile_as_byte('mock.zip'), 1234, 19)


if __name__ == "__main__":
    main()
