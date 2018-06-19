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
from iconservice.base.address import ICX_ENGINE_ADDRESS
from iconservice.base.block import Block
from iconservice.base.message import Message
from iconservice.base.transaction import Transaction
from iconservice.database.factory import DatabaseFactory
from iconservice.iconscore.icon_score_context import IconScoreContextFactory
from iconservice.iconscore.icon_score_context import IconScoreContextType
from iconservice.deploy.icon_score_deploy_engine import IconScoreDeployEngine
from iconservice.iconscore.icon_score_info_mapper import IconScoreInfoMapper
from iconservice.iconscore.icon_score_loader import IconScoreLoader
from iconservice.deploy.icon_score_deployer import IconScoreDeployer
from iconservice.icx.icx_storage import IcxStorage
from iconservice.icx.icx_engine import IcxEngine

TEST_ROOT_PATH = os.path.abspath(os.path.dirname(__file__))


class TestIconZipDeploy(unittest.TestCase):
    _ROOT_SCORE_PATH = 'tests/score'
    _TEST_DB_PATH = 'tests/test_db'

    def setUp(self):
        db_path = os.path.join(TEST_ROOT_PATH, self._TEST_DB_PATH)
        score_path = os.path.join(TEST_ROOT_PATH, self._ROOT_SCORE_PATH)

        self.__ensure_dir(db_path)
        self._db_factory = DatabaseFactory(db_path)
        self._icx_db = self._db_factory.create_by_name('icon_dex')
        self._icx_db.address = ICX_ENGINE_ADDRESS
        self._icx_storage = IcxStorage(self._icx_db)

        self._icon_score_loader = IconScoreLoader(score_path)
        self._icon_score_mapper = IconScoreInfoMapper(
            self._icx_storage, self._db_factory, self._icon_score_loader)

        self._engine = IconScoreDeployEngine(
            icon_score_root_path=score_path,
            flags=IconScoreDeployEngine.Flag.NONE,
            icx_storage=self._icx_storage,
            icon_score_mapper=self._icon_score_mapper)

        self.from_address = create_address(AddressPrefix.EOA, b'from')

        self.sample_token_address = create_address(
            AddressPrefix.CONTRACT, b'sample_token')

        self._factory = IconScoreContextFactory(max_size=1)
        self._context = self._factory.create(IconScoreContextType.GENESIS)
        self._context.msg = Message(self.from_address, 0)
        self._context.tx = Transaction('test_01', origin=self.from_address)
        self._context.block = Block(1, 'block_hash', 0)
        self._context.icon_score_mapper = self._icon_score_mapper
        self._context.icx = IcxEngine()
        self._context.icx.open(self._icx_storage)

        self._one_icx = 1 * 10 ** 18
        self._one_icx_to_token = 1

    def tearDown(self):
        self._engine = None
        info = self._icon_score_mapper.get(self.sample_token_address)
        if info is not None and not self._context.readonly:
            score = info.icon_score
            score.db._context_db.close(self._context)
        self._factory.destroy(self._context)

        remove_path = os.path.join(TEST_ROOT_PATH, 'tests')
        IconScoreDeployer.remove_existing_score(remove_path)
        remove_path = os.path.join(TEST_ROOT_PATH, self._TEST_DB_PATH)
        IconScoreDeployer.remove_existing_score(remove_path)
        remove_path = os.path.join(TEST_ROOT_PATH, self.from_address.body.hex())
        IconScoreDeployer.remove_existing_score(remove_path)

    @staticmethod
    def __ensure_dir(dir_path):
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)

    @staticmethod
    def read_zipfile_as_byte(archive_path: str) -> bytes:
        with open(archive_path, 'rb') as f:
            byte_data = f.read()
            return byte_data

    def test_deploy_on_invoke(self):
        content: bytes = self.read_zipfile_as_byte(
            os.path.join(TEST_ROOT_PATH, 'test.zip'))

        data_type = 'install'
        data = {
            "contentType": "application/zip",
            "content": f'0x{content.hex()}'
        }
        self._engine._deploy_on_invoke(
            self._context, self.from_address, data_type, data)
        self.assertTrue(
            os.path.join(TEST_ROOT_PATH, self.from_address.body.hex()))
