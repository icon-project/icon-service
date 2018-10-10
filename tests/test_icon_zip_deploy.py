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

"""IconScoreEngine testcase
"""


import os
import unittest

from unittest.mock import Mock

from iconservice.base.address import AddressPrefix, ZERO_SCORE_ADDRESS
from iconservice.base.address import ICX_ENGINE_ADDRESS
from iconservice.base.block import Block
from iconservice.base.message import Message
from iconservice.base.transaction import Transaction
from iconservice.database.factory import ContextDatabaseFactory
from iconservice.deploy.icon_score_deploy_engine import IconScoreDeployEngine
from iconservice.deploy.icon_score_deploy_storage import IconScoreDeployStorage
from iconservice.deploy.icon_score_deployer import IconScoreDeployer
from iconservice.icon_constant import DEFAULT_BYTE_SIZE
from iconservice.iconscore.icon_score_context import ContextContainer
from iconservice.iconscore.icon_score_context import IconScoreContext
from iconservice.iconscore.icon_score_context import IconScoreContextFactory
from iconservice.iconscore.icon_score_context import IconScoreContextType
from iconservice.iconscore.icon_score_mapper import IconScoreMapper
from iconservice.iconscore.icon_score_loader import IconScoreLoader
from iconservice.icx.icx_engine import IcxEngine
from iconservice.icx.icx_storage import IcxStorage
from tests import create_address, create_block_hash, create_tx_hash

TEST_ROOT_PATH = os.path.abspath(os.path.dirname(__file__))


class TestIconZipDeploy(unittest.TestCase):
    _ROOT_SCORE_PATH = 'tests/score'
    _TEST_DB_PATH = 'tests/test_db'
    _ZERO_SCORE_ID = bytes(DEFAULT_BYTE_SIZE)

    @classmethod
    def setUpClass(cls):
        db_path = os.path.join(TEST_ROOT_PATH, cls._TEST_DB_PATH)
        ContextDatabaseFactory.open(
            db_path, ContextDatabaseFactory.Mode.SINGLE_DB)

    @classmethod
    def tearDownClass(cls):
        ContextDatabaseFactory.close()

    def setUp(self):
        db_path = os.path.join(TEST_ROOT_PATH, self._TEST_DB_PATH)
        score_path = os.path.join(TEST_ROOT_PATH, self._ROOT_SCORE_PATH)

        self._tx_index = 0
        self.__ensure_dir(db_path)

        self._icx_db = ContextDatabaseFactory.create_by_name('icx_db')
        self._icx_db.address = ICX_ENGINE_ADDRESS
        self._icx_storage = IcxStorage(self._icx_db)
        self._icon_deploy_storage = IconScoreDeployStorage(self._icx_db)

        self._engine = IconScoreDeployEngine()
        self._icon_score_loader = IconScoreLoader(score_path)
        IconScoreMapper.icon_score_loader = self._icon_score_loader
        IconScoreMapper.deploy_storage = self._icon_deploy_storage
        self._icon_score_mapper = IconScoreMapper()

        IconScoreContext.get_owner = Mock()

        self._engine.open(
            score_root_path=score_path,
            icon_deploy_storage=self._icon_deploy_storage)

        self.from_address = create_address(AddressPrefix.EOA)

        self.sample_token_address = create_address(AddressPrefix.CONTRACT)

        self._factory = IconScoreContextFactory(max_size=1)
        self.make_context()

        self._one_icx = 1 * 10 ** 18
        self._one_icx_to_token = 1

    def make_context(self):
        self._tx_index += 1
        self._context = self._factory.create(IconScoreContextType.DIRECT)
        self._context.msg = Message(self.from_address, 0)

        tx_hash = create_tx_hash()
        self._context.new_icon_score_mapper = IconScoreMapper()
        self._context.tx = Transaction(tx_hash, origin=self.from_address)
        self._context.block = Block(1, create_block_hash(), 0, None)
        self._context.icon_score_mapper = self._icon_score_mapper
        self._context.icx = IcxEngine()
        self._context.icx.open(self._icx_storage)
        ContextContainer._push_context(self._context)
        self._context.validate_deployer = Mock()
        self._context.validate_score_blacklist = Mock()
        self._context.is_service_flag_on = Mock(return_value=False)

    def tearDown(self):
        self._engine = None
        ContextContainer._pop_context()
        self._icon_score_mapper.close()
        self._factory.destroy(self._context)

        remove_path = os.path.join(TEST_ROOT_PATH, 'tests')
        IconScoreDeployer.remove_existing_score(remove_path)
        remove_path = os.path.join(TEST_ROOT_PATH, self._TEST_DB_PATH)
        IconScoreDeployer.remove_existing_score(remove_path)
        remove_path = os.path.join(
            TEST_ROOT_PATH, self.sample_token_address.to_bytes().hex())
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

    def test_deploy(self):
        content: bytes = self.read_zipfile_as_byte(
            os.path.join(TEST_ROOT_PATH, 'sample', 'valid.zip'))

        data = {
            "contentType": "application/zip",
            "content": f'0x{bytes.hex(content)}'
        }
        self._icon_deploy_storage.get_next_tx_hash = Mock(return_value=self._ZERO_SCORE_ID)

        self._engine.invoke(
            self._context, ZERO_SCORE_ADDRESS, self.sample_token_address, data)

        self.assertTrue(
            os.path.join(
                TEST_ROOT_PATH, self.sample_token_address.to_bytes().hex()))
