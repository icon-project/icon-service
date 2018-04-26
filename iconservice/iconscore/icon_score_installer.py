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
import logging
import os
import zipfile
import shutil
import pip

from ..base.address import Address
from ..base.exception import ScoreInstallException, ScoreInstallExtractException
from ..base.exception import ScoreInstallWriteZipfileException

CONST_SCORE_EXISTS_ERROR_CODE = 918
CONST_WRITE_ZIPFILE_ERROR_CODE = 919
CONST_EXTRACT_FILES_ERROR_CODE = 920
CONST_SUCCESS_INSTALL_SCORE = 910
CONST_PERMISSION_ERROR_CODE = 911


class IconScoreInstaller(object):
    """Score installer.
    """

    def __init__(self, icon_score_root_path: str) -> None:
        self.icon_score_root_path = icon_score_root_path

    def install(self, address: Address, data: bytes, block_height: int, transaction_index: int) -> int:
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
        zip_path = install_path + ".zip"
        try:
            if not os.path.exists(score_root_path):
                os.makedirs(score_root_path)
            if os.path.exists(install_path):
                raise ScoreInstallException(f"You already have a SCORE of this version.")
            zip_path = IconScoreInstaller.write_zipfile_with_bytes(zip_path, data)
            zip_root_directory_name = IconScoreInstaller.extract_files(self.icon_score_root_path, zip_path)

            IconScoreInstaller.remove_exists_archive(zip_path)
            shutil.move(os.path.join(self.icon_score_root_path, zip_root_directory_name),
                        install_path)
            # IconScoreInstaller.install_requirements(install_path)
            return CONST_SUCCESS_INSTALL_SCORE
        except ScoreInstallException as e:
            logging.debug(e.message)
            return CONST_SCORE_EXISTS_ERROR_CODE
        except ScoreInstallWriteZipfileException:
            return CONST_WRITE_ZIPFILE_ERROR_CODE
        except ScoreInstallExtractException:
            return CONST_EXTRACT_FILES_ERROR_CODE
        except PermissionError as pe:
            logging.debug(pe)
            return CONST_PERMISSION_ERROR_CODE

    @staticmethod
    def install_requirements(install_path: str):
        for current_dir, dirs, file_list in os.walk(install_path):
            if 'requirements.txt' in file_list:
                with open(os.path.join(install_path, 'requirements.txt'), 'r') as requires:
                    requirements_list_str = requires.read()
                for package in requirements_list_str.split("\n"):
                    if bool(package):
                        pip.main(['install', package])

    @staticmethod
    def extract_files(install_path: str, archive_path: str) -> str:
        """Extract files from zip file.

        :param install_path: Path where score will be installed.
        :param archive_path: The archive_path of SCORE.
        :return:
        Will return root directory of SCORE.
        """
        try:
            if zipfile.is_zipfile(archive_path) is False:
                IconScoreInstaller.remove_exists_archive(archive_path)
                raise ScoreInstallExtractException("The data you sent is not a zip file.")
            else:
                with zipfile.ZipFile(archive_path, 'r') as z:
                    file_name_list = z.namelist()
                    file_name_prefix_list = [prefix.split('/')[0] for prefix in file_name_list
                                             if not prefix.startswith('__MACOSX')]
                    is_zipfile_covered = all(a == file_name_prefix_list[0] for a in file_name_prefix_list)
                    zip_root_name = file_name_list[0].split("/")[0]

                    if is_zipfile_covered:
                        IconScoreInstaller._extract_files(file_name_list, install_path, z)
                        return zip_root_name
                    IconScoreInstaller._extract_files(file_name_list, install_path + '/temp', z)
                    return 'temp'

        except FileNotFoundError:
            logging.debug(f"{archive_path} not found. check file path.")
            raise ScoreInstallExtractException(f"{archive_path} not found. check file path.")
        except IsADirectoryError:
            logging.debug(f"{archive_path} is a directory. check file path.")
            raise ScoreInstallExtractException(f"{archive_path} is a directory. check file path.")
        except PermissionError:
            raise ScoreInstallExtractException("Permission error")
        except NotADirectoryError:
            logging.debug(f"{install_path} is not a directory")
            raise ScoreInstallExtractException(f"{install_path} is not a directory")
        except zipfile.BadZipFile:
            logging.debug(f"{archive_path} is bad zip file.")
            raise ScoreInstallExtractException(f"{archive_path} is bad zip file.")
        except zipfile.LargeZipFile:
            logging.debug(f"{archive_path} is too Large Zipfile.")
            raise ScoreInstallExtractException(f"{archive_path} is too Large file.")
        except Exception as e:
            logging.debug(e)
            raise ScoreInstallExtractException("Exception occurred while extracting zip file.")

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
            logging.debug(f"{archive_path} file exists.")
            raise ScoreInstallWriteZipfileException(f"{archive_path} file exists.")
        try:
            with open(archive_path, 'wb') as f:
                f.write(byte_data)
            return archive_path
        except IsADirectoryError:
            logging.debug(f"{archive_path} is a directory. check file path.")
            raise ScoreInstallWriteZipfileException(f"{archive_path} is a directory. check file path.")
        except PermissionError:
            logging.debug(f"permission error")
            print(archive_path)
            return ScoreInstallWriteZipfileException(f"permission error")

    # This method will be removed. written for test.
    @staticmethod
    def read_zipfile_as_byte(archive_path: str) -> bytes:
        with open(archive_path, 'rb') as f:
            byte_data = f.read()
            return byte_data
