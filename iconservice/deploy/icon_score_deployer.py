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
import io
import os
import zipfile
import shutil
from iconservice.base.address import Address
from iconservice.base.exception import ScoreInstallException, ScoreInstallExtractException


class IconScoreDeployer(object):
    """Deployer installing and deploying SCORE"""
    def __init__(self, score_root_path: str):
        self.score_root_path = score_root_path

    def deploy(self, address: Address, data: bytes, tx_hash: bytes):
        """
        :param address: score address
        :param data: The byte value of the zip file.
        :param tx_hash:
        """
        score_root_path = os.path.join(self.score_root_path, address.to_bytes().hex())
        converted_tx_hash = f'0x{bytes.hex(tx_hash)}'
        install_path = os.path.join(score_root_path, converted_tx_hash)
        try:
            if os.path.isfile(install_path):
                raise ScoreInstallException(f'{install_path} is a file. Check your path.')
            if os.path.isdir(install_path):
                raise ScoreInstallException(f'{install_path} is a directory. Check {install_path}')
            if not os.path.exists(install_path):
                os.makedirs(install_path)

            file_info_generator = IconScoreDeployer._extract_files_gen(data)
            for name, file_info, parent_dir in file_info_generator:
                if not os.path.exists(os.path.join(install_path, parent_dir)):
                    os.makedirs(os.path.join(install_path, parent_dir))
                with file_info as file_info_context, open(os.path.join(install_path, name), 'wb') as dest:
                    contents = file_info_context.read()
                    dest.write(contents)
        except BaseException as e:
            shutil.rmtree(install_path, ignore_errors=True)
            raise e

    @staticmethod
    def _extract_files_gen(data: bytes):
        """
        Reads all files from the depth lower than where the file 'package.json' is and make the generator.
        The generator has tuples with a filename, file info, parent dir.

        :param data: Bytes of the zip file.
        """
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as memory_zip:
                memory_zip_infolist = memory_zip.infolist()
                matched_file_path = ""
                # Finds the depth having the file 'package.json'.
                for zip_info in memory_zip_infolist:
                    with memory_zip.open(zip_info) as file:
                        file_path = zip_info.filename
                        if "package.json" in file_path:
                            matched_file_path = file_path[:len(file_path)-len("package.json")]
                            break

                for zip_info in memory_zip_infolist:
                    with memory_zip.open(zip_info) as file:
                        file_path = zip_info.filename
                        if (
                                file_path.find('__MACOSX') < 0
                                and file_path.find('__pycache__') < 0
                                and not file_path.startswith('.')
                                and file_path.find('/.') < 0
                                and matched_file_path in file_path
                        ):
                            file_path = file_path.replace(matched_file_path, '')
                            parent_directory = os.path.dirname(file_path)
                            if file_path and file_path[-1] != '/':
                                yield file_path, file, parent_directory
        except zipfile.BadZipFile:
            raise ScoreInstallExtractException("Bad zip file.")
        except zipfile.LargeZipFile:
            raise ScoreInstallExtractException("Zip file is too Large.")
        except Exception as e:
            raise ScoreInstallExtractException(f'Error raising from extract_files_gen: {e}')

    @staticmethod
    def remove_existing_score(archive_path: str):
        """Remove SCORE

        :param archive_path: The path of SCORE archive.
        """
        if os.path.isfile(archive_path):
            os.remove(archive_path)
        elif os.path.isdir(archive_path):
            shutil.rmtree(archive_path)
