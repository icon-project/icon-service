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

from . import rmtree
from iconservice.base.address import AddressPrefix, create_address
from iconservice.base.address import ICX_ENGINE_ADDRESS
from iconservice.base.block import Block
from iconservice.base.message import Message
from iconservice.base.transaction import Transaction
from iconservice.database.factory import DatabaseFactory
from iconservice.iconscore.icon_score_context import IconScoreContextFactory
from iconservice.iconscore.icon_score_context import IconScoreContextType
from iconservice.iconscore.icon_score_engine import IconScoreEngine
from iconservice.iconscore.icon_score_info_mapper import IconScoreInfoMapper
from iconservice.iconscore.icon_score_loader import IconScoreLoader
from iconservice.iconscore.icon_score_deployer import IconScoreDeployer
from iconservice.icx.icx_storage import IcxStorage

TEST_ROOT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../'))


class MockScore(object):
    def __init__(self, test_case: unittest.TestCase):
        self._test_case = test_case

    def on_install(self, params):
        self._test_case.assertIsNotNone(params)
        self._test_case.assertTrue(isinstance(params, dict))


class TestIconScoreEngine(unittest.TestCase):
    _ROOT_SCORE_PATH = os.path.join(TEST_ROOT_PATH, 'score')
    _TEST_DB_PATH = 'tests/test_db/'

    def setUp(self):
        rmtree(self._ROOT_SCORE_PATH)
        rmtree(self._TEST_DB_PATH)

        archive_path = 'tests/score.zip'
        archive_path = os.path.join(TEST_ROOT_PATH, archive_path)
        zip_bytes = self.read_zipfile_as_byte(archive_path)
        install_path = os.path.join(TEST_ROOT_PATH, self._ROOT_SCORE_PATH)
        self.__unpack_zip_file(install_path, zip_bytes)

        db_path = os.path.join(TEST_ROOT_PATH, self._TEST_DB_PATH)
        self.__ensure_dir(db_path)
        self._db_factory = DatabaseFactory(db_path)
        self._icx_storage = self._create_icx_storage(self._db_factory)
        self._icon_score_loader = IconScoreLoader(self._ROOT_SCORE_PATH)
        self._icon_score_mapper = IconScoreInfoMapper(self._icx_storage,
                                                      self._db_factory,
                                                      self._icon_score_loader)
        self._icon_score_deployer = IconScoreDeployer('./')
        self._engine = IconScoreEngine(
            self._icx_storage,
            self._icon_score_mapper,
            self._icon_score_deployer
        )

        self._from = create_address(AddressPrefix.EOA, b'from')
        self._icon_score_address = create_address(AddressPrefix.CONTRACT,
                                                  b'SampleToken')

        self._factory = IconScoreContextFactory(max_size=1)
        self._context = self._factory.create(IconScoreContextType.GENESIS)
        self._context.msg = Message(self._from, 0)
        self._context.tx = Transaction(
            'test_01',
            origin=create_address(AddressPrefix.EOA, b'owner'))
        self._context.block = Block(1, 'block_hash', 0)

    def tearDown(self):
        self._engine = None
        info = self._icon_score_mapper.get(self._icon_score_address)
        if info is not None and not self._context.readonly:
            score = info.icon_score
            score.db._context_db.close(self._context)
        self._factory.destroy(self._context)

        remove_path = os.path.join(TEST_ROOT_PATH, self._ROOT_SCORE_PATH)
        IconScoreDeployer.remove_existing_score(remove_path)
        remove_path = os.path.join(TEST_ROOT_PATH, self._TEST_DB_PATH)
        IconScoreDeployer.remove_existing_score(remove_path)

    @staticmethod
    def _create_icx_storage(db_factory: DatabaseFactory) -> 'IcxStorage':
        """Create IcxStorage instance

        :param db_factory: ContextDatabase Factory
        """
        db = db_factory.create_by_name('icon_dex')
        db.address = ICX_ENGINE_ADDRESS

        return IcxStorage(db)

    @staticmethod
    def read_zipfile_as_byte(archive_path: str) -> bytes:
        with open(archive_path, 'rb') as f:
            byte_data = f.read()
            return byte_data

    @staticmethod
    def __unpack_zip_file(install_path: str, data: bytes):
        file_info_generator = IconScoreDeployer.extract_files_gen(data)
        for name, file_info, parent_directory in file_info_generator:
            if not os.path.exists(os.path.join(install_path, parent_directory)):
                os.makedirs(os.path.join(install_path, parent_directory))
            with file_info as file_info_context,\
                    open(os.path.join(install_path, name), 'wb') as dest:
                contents = file_info_context.read()
                dest.write(contents)
        return True

    @staticmethod
    def __ensure_dir(file_path):
        directory = os.path.dirname(file_path)
        if not os.path.exists(directory):
            os.makedirs(directory)

    def test_install(self):
        proj_name = 'test_score'
        path = os.path.join(TEST_ROOT_PATH, 'tests/tmp/{}'.format(proj_name))
        install_data = {'content_type': 'application/tbears', 'content': path}
        self._engine.invoke(
            self._context, self._icon_score_address, 'install', install_data)
        self._engine.commit(self._context)

    def test_call_method(self):
        calldata = {'method': 'total_supply', 'params': {}}

        proj_name = 'test_score'
        path = os.path.join(TEST_ROOT_PATH, 'tests/tmp/{}'.format(proj_name))
        install_data = {'content_type': 'application/tbears', 'content': path}
        self._engine.invoke(
            self._context, self._icon_score_address, 'install', install_data)
        self._engine.commit(self._context)
        self._context.type = IconScoreContextType.QUERY
        ret = self._engine.query(
            self._context, self._icon_score_address, 'call', calldata)
        self.assertEqual(1000 * 10 ** 18, ret)

    def test_call_on_init_of_score(self):
        params = {}
        score = MockScore(self)
        self._engine._call_on_init_of_score(None, score.on_install, params)
