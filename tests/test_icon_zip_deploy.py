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
from iconservice.deploy import DeployEngine, DeployStorage
from iconservice.deploy.utils import remove_path
from iconservice.icon_constant import ZERO_TX_HASH
from iconservice.iconscore.context.context import ContextContainer
from iconservice.iconscore.icon_score_context import IconScoreContext
from iconservice.iconscore.icon_score_context import IconScoreContextType
from iconservice.iconscore.icon_score_context_util import IconScoreContextUtil
from iconservice.iconscore.icon_score_mapper import IconScoreMapper
from iconservice.icx import IcxEngine, IcxStorage
from iconservice.utils import ContextStorage
from tests import create_address, create_block_hash, create_tx_hash

TEST_ROOT_PATH = os.path.abspath(os.path.dirname(__file__))


VALIDATE_SCORE_BLACK_LIST = IconScoreContextUtil.validate_score_blacklist
GET_OWNER = IconScoreContextUtil.get_owner
GET_ICON_SCORE = IconScoreContextUtil.get_icon_score
IS_SERVICE_FLAG_ON = IconScoreContextUtil.is_service_flag_on


class TestIconZipDeploy(unittest.TestCase):
    _SCORE_ROOT_PATH = 'tests/score'
    _TEST_DB_PATH = 'tests/test_db'

    @classmethod
    def setUpClass(cls):
        db_path = os.path.join(TEST_ROOT_PATH, cls._TEST_DB_PATH)
        ContextDatabaseFactory.open(
            db_path, ContextDatabaseFactory.Mode.SINGLE_DB)

    @classmethod
    def tearDownClass(cls):
        ContextDatabaseFactory.close()

    def setUp(self):
        db_path: str = os.path.join(TEST_ROOT_PATH, self._TEST_DB_PATH)
        # score_root_path: str = os.path.join(TEST_ROOT_PATH, self._SCORE_ROOT_PATH)

        self._tx_index = 0
        self.__ensure_dir(db_path)

        self._icx_db = ContextDatabaseFactory.create_by_name('icx_db')
        self._icx_db.address = ICX_ENGINE_ADDRESS
        self._icx_storage = IcxStorage(self._icx_db)
        self._icon_deploy_storage = DeployStorage(self._icx_db)

        self._icon_score_mapper = IconScoreMapper()

        IconScoreContextUtil.validate_score_blacklist = Mock()
        IconScoreContextUtil.get_owner = Mock()
        IconScoreContextUtil.get_icon_score = Mock()
        IconScoreContextUtil.is_service_flag_on = Mock()

        self.from_address = create_address(AddressPrefix.EOA)
        self.sample_token_address = create_address(AddressPrefix.CONTRACT)

        self.make_context()
        self._engine = DeployEngine()
        self._engine.open(self._icon_deploy_storage)
        IconScoreContext.storage = ContextStorage(
            deploy=Mock(DeployStorage),
            fee=None,
            icx=None,
            iiss=None,
            prep=None,
            issue=None,
            rc=None,
            meta=None
        )

        self._one_icx = 1 * 10 ** 18
        self._one_icx_to_token = 1

    def make_context(self):
        self._tx_index += 1
        self._context = IconScoreContext(IconScoreContextType.DIRECT)
        self._context.msg = Message(self.from_address, 0)

        tx_hash = create_tx_hash()
        self._context.new_icon_score_mapper = IconScoreMapper()
        self._context.tx = Transaction(tx_hash, origin=self.from_address)
        self._context.block = Block(1, create_block_hash(), 0, None, 0)
        self._context.icon_score_mapper = self._icon_score_mapper
        self._context.icx = IcxEngine()
        self._context.icx.open(self._icx_storage)
        ContextContainer._push_context(self._context)
        self._context.validate_score_blacklist = Mock()
        self._context.is_service_flag_on = Mock(return_value=False)

    def tearDown(self):
        self._engine = None
        ContextContainer._pop_context()
        self._icon_score_mapper.close()

        path = os.path.join(TEST_ROOT_PATH, 'tests')
        remove_path(path)
        path = os.path.join(TEST_ROOT_PATH, self._TEST_DB_PATH)
        remove_path(path)
        path = os.path.join(
            TEST_ROOT_PATH, self.sample_token_address.to_bytes().hex())
        remove_path(path)
        IconScoreContextUtil.validate_score_blacklist = VALIDATE_SCORE_BLACK_LIST
        IconScoreContextUtil.get_owner = GET_OWNER
        IconScoreContextUtil.get_icon_score = GET_ICON_SCORE
        IconScoreContextUtil.is_service_flag_on = IS_SERVICE_FLAG_ON

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
            os.path.join(TEST_ROOT_PATH, 'sample', 'normal_score.zip'))

        data = {
            "contentType": "application/zip",
            "content": f'0x{bytes.hex(content)}'
        }
        self._icon_deploy_storage.get_next_tx_hash = Mock(return_value=ZERO_TX_HASH)

        self._engine.invoke(
            self._context, ZERO_SCORE_ADDRESS, self.sample_token_address, data)

        self.assertTrue(
            os.path.join(
                TEST_ROOT_PATH, self.sample_token_address.to_bytes().hex()))
