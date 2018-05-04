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

"""IconScoreEngine testcase
"""


import unittest
import os
from iconservice.base.address import AddressPrefix, create_address
from iconservice.base.message import Message
from iconservice.base.transaction import Transaction
from iconservice.database.factory import DatabaseFactory
from iconservice.iconscore.icon_score_context import IconScoreContextFactory, IconScoreContextType
from iconservice.iconscore.icon_score_engine import IconScoreEngine
from iconservice.iconscore.icon_score_info_mapper import IconScoreInfoMapper
from iconservice.iconscore.icon_score_loader import ICON_ROOT_PATH
from iconservice.iconscore.icon_score_installer import IconScoreInstaller

TEST_ROOT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../'))


class TestIconScoreEngine(unittest.TestCase):
    _ROOT_SCORE_PATH = 'score'
    _TEST_DB_PATH = 'tests/test_db/'

    def setUp(self):
        archive_path = 'tests/score.zip'
        archive_path = os.path.join(ICON_ROOT_PATH, archive_path)
        zip_bytes = self.read_zipfile_as_byte(archive_path)
        install_path = os.path.join(ICON_ROOT_PATH, self._ROOT_SCORE_PATH)
        self.__unpack_zip_file(install_path, zip_bytes)

        db_path = os.path.join(TEST_ROOT_PATH, self._TEST_DB_PATH)
        self.__ensure_dir(db_path)
        self._db_factory = DatabaseFactory(db_path)
        self._icon_score_mapper = IconScoreInfoMapper()
        self._icx_storage = None

        self._engine = IconScoreEngine(
            self._ROOT_SCORE_PATH,
            self._icx_storage,
            self._icon_score_mapper,
            self._db_factory)

        self._from = create_address(AddressPrefix.EOA, b'from')
        self._icon_score_address = create_address(AddressPrefix.CONTRACT, b'test')

        self._factory = IconScoreContextFactory(max_size=1)
        self._context = self._factory.create(IconScoreContextType.GENESIS)
        self._context.msg = Message(self._from, 0)
        self._context.tx = Transaction('test_01')

    def tearDown(self):
        self._engine = None
        score = self._icon_score_mapper[self._icon_score_address].icon_score
        score.db._IconScoreDatabase__context_db.close(self._context)
        self._factory.destroy(self._context)

        remove_path = os.path.join(ICON_ROOT_PATH, self._ROOT_SCORE_PATH)
        IconScoreInstaller.remove_existing_score(remove_path)
        remove_path = os.path.join(TEST_ROOT_PATH, self._TEST_DB_PATH)
        IconScoreInstaller.remove_existing_score(remove_path)

    @staticmethod
    def read_zipfile_as_byte(archive_path: str) -> bytes:
        with open(archive_path, 'rb') as f:
            byte_data = f.read()
            return byte_data

    @staticmethod
    def __unpack_zip_file(install_path: str, data: bytes):
        file_info_generator = IconScoreInstaller.extract_files_gen(data)
        for name, file_info, parent_directory in file_info_generator:
            if not os.path.exists(os.path.join(install_path, parent_directory)):
                os.makedirs(os.path.join(install_path, parent_directory))
            with file_info as file_info_context, open(os.path.join(install_path, name), 'wb') as dest:
                contents = file_info_context.read()
                dest.write(contents)
        return True

    @staticmethod
    def __ensure_dir(file_path):
        directory = os.path.dirname(file_path)
        if not os.path.exists(directory):
            os.makedirs(directory)

    def test_install(self):
        self._engine.invoke(self._icon_score_address, None, 'install', dict())

    def test_call_method(self):
        calldata = {'method': 'total_supply', 'params': dict()}

        self._engine.invoke(self._icon_score_address, None, 'install', dict())
        self.assertEqual(1000000000000000000000, self._engine.query(self._icon_score_address, None, 'call', calldata))