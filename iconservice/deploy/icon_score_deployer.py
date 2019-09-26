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
import shutil
import zipfile

from ..base.exception import InvalidPackageException
from ..icon_constant import Revision, PACKAGE_JSON_FILE


class IconScoreDeployer(object):

    @staticmethod
    def deploy(path: str, data: bytes, revision: int = 0):
        """Deploy SCORE; Stores SCORE on the root path

        :param path: the path of directory where score is deployed
        :param data: Bytes of the zip file.
        :param revision: Revision num
        """
        shutil.rmtree(path, ignore_errors=True)
        os.makedirs(path)

        file_info_generator = IconScoreDeployer._extract_files_gen(data, revision)
        for name, file_info, parent_dir in file_info_generator:
            if not os.path.exists(os.path.join(path, parent_dir)):
                os.makedirs(os.path.join(path, parent_dir))
            with file_info as file_info_context, open(os.path.join(path, name), 'wb') as dest:
                contents = file_info_context.read()
                dest.write(contents)

    @staticmethod
    def _extract_files_gen(data: bytes, revision: int = 0):
        """
        Reads all files from the depth lower than where the file 'package.json' is and make the generator.
        The generator has tuples with a filename, file info, parent dir.
        When revision is 2 or more, this method is used.

        :param data: Bytes of the zip file.
        :param revision: Revision num.
        """

        try:
            with zipfile.ZipFile(io.BytesIO(data)) as memory_zip:
                memory_zip_infolist = memory_zip.infolist()
                common_prefix = ""
                has_package = False
                # Finds the depth having the file 'package.json'.
                for zip_info in memory_zip_infolist:
                    file_path = zip_info.filename
                    file_name = os.path.basename(file_path)
                    if PACKAGE_JSON_FILE == file_name:
                        common_prefix = os.path.dirname(file_path)
                        has_package = True
                        break

                if revision >= Revision.THREE.value and has_package is False:
                    raise InvalidPackageException("package.json not found")

                for zip_info in memory_zip_infolist:
                    with memory_zip.open(zip_info) as file:
                        file_path = zip_info.filename
                        if (
                                file_path.startswith(common_prefix)
                                and not zip_info.is_dir()
                                and file_path.find('__MACOSX') < 0
                                and file_path.find('__pycache__') < 0
                                and not file_path.startswith('.')
                                and file_path.find('/.') < 0
                        ):
                            if revision >= Revision.THREE.value:
                                file_path = os.path.relpath(file_path, common_prefix)
                                parent_directory = os.path.dirname(file_path)
                                if file_path:
                                    yield file_path, file, parent_directory
                            else:
                                # legacy for revision 2
                                legacy_common_prefix = f"{common_prefix}/"
                                file_path = file_path.replace(legacy_common_prefix, '')
                                parent_directory = os.path.dirname(file_path)
                                if file_path and file_path[-1] != '/':
                                    yield file_path, file, parent_directory
        except zipfile.BadZipFile:
            raise InvalidPackageException("Bad zip file.")
        except zipfile.LargeZipFile:
            raise InvalidPackageException("Zip file is too Large.")
        except Exception as e:
            raise InvalidPackageException(f'Error raised from extract_files_gen: {e}')

    @staticmethod
    def deploy_legacy(path: str, data: bytes):
        """Install score.
        Use 'address', 'block_height', and 'transaction_index' to specify the path where 'Score' will be installed.

        :param path: the path of directory where score is deployed
        :param data: The byte value of the zip file.
        """
        shutil.rmtree(path, ignore_errors=True)
        if not os.path.exists(path):
            os.makedirs(path)

        file_info_generator = IconScoreDeployer._extract_files_gen_legacy(data)
        for name, file_info, parent_directory in file_info_generator:
            if not os.path.exists(os.path.join(path, parent_directory)):
                os.makedirs(os.path.join(path, parent_directory))
            with file_info as file_info_context, open(os.path.join(path, name), 'wb') as dest:
                contents = file_info_context.read()
                dest.write(contents)

    @staticmethod
    def _extract_files_gen_legacy(data: bytes):
        """Yield (filename, file_information, parent_directory_name) tuple.

        :param data: The byte value of the zip file.
        :return:
        """
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as memory_zip:
                memory_zip_infolist = memory_zip.infolist()
                memory_zip_files_path_gen = (path.filename for path in memory_zip_infolist)
                common_path_len = len(os.path.commonpath(memory_zip_files_path_gen))
                start_index = common_path_len
                if common_path_len == 0:
                    start_index = -1
                for zip_info in memory_zip.infolist():
                    with memory_zip.open(zip_info) as file:
                        file_path = zip_info.filename[start_index + 1:]
                        file_name_start_index = file_path.rfind('/')
                        parent_directory = file_path[:file_name_start_index]
                        if file_path.find('__MACOSX') != -1:
                            continue
                        if file_path.find('__pycache__') != -1:
                            continue
                        if file_name_start_index == len(file_path) - 1:
                            # continue when 'file_path' is a directory.
                            continue
                        if file_path.startswith('.') or file_path.find('/.') != -1:
                            # continue when 'file_path' is hidden directory or hidden file.
                            continue

                        if file_name_start_index == -1:
                            yield file_path, file, ''
                        else:
                            yield file_path, file, parent_directory
        except zipfile.BadZipFile:
            raise InvalidPackageException("Bad zip file.")
        except zipfile.LargeZipFile:
            raise InvalidPackageException("Large zip file.")
        except Exception as e:
            raise InvalidPackageException(f'extract_files_gen error -> exception: {e}')
