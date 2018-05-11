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
from iconservice.base.address import AddressPrefix, create_address, ICX_ENGINE_ADDRESS
from iconservice.base.block import Block
from iconservice.base.message import Message
from iconservice.base.transaction import Transaction
from iconservice.database.factory import DatabaseFactory
from iconservice.iconscore.icon_score_context import IconScoreContextFactory, IconScoreContextType
from iconservice.iconscore.icon_score_engine import IconScoreEngine
from iconservice.iconscore.icon_score_info_mapper import IconScoreInfoMapper
from iconservice.iconscore.icon_score_loader import IconScoreLoader
from iconservice.iconscore.icon_score_installer import IconScoreInstaller
from iconservice.icx.icx_storage import IcxStorage

TEST_ROOT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../'))


# have to score.zip unpack and proj_name = test_score
class TestIconScoreEngine2(unittest.TestCase):
    _ROOT_SCORE_PATH = 'score'
    _TEST_DB_PATH = 'tests/test_db'

    def setUp(self):
        db_path = os.path.join(TEST_ROOT_PATH, self._TEST_DB_PATH)
        score_path = os.path.join(TEST_ROOT_PATH, self._ROOT_SCORE_PATH)
        self.__ensure_dir(db_path)
        self._db_factory = DatabaseFactory(db_path)
        self._icx_storage = self._create_icx_storage(self._db_factory)

        self._icon_score_loader = IconScoreLoader(score_path)
        self._icon_score_mapper = IconScoreInfoMapper(self._icx_storage, self._db_factory, self._icon_score_loader)

        self._engine = IconScoreEngine(
            self._icx_storage,
            self._icon_score_mapper)

        self._from = create_address(AddressPrefix.EOA, b'from')
        self._icon_score_address = create_address(AddressPrefix.CONTRACT, b'test_score')

        self._factory = IconScoreContextFactory(max_size=1)
        self._context = self._factory.create(IconScoreContextType.GENESIS)
        self._context.msg = Message(self._from, 0)
        self._context.tx = Transaction('test_01', origin=create_address(AddressPrefix.EOA, b'owner'))
        self._context.block = Block(1, 'block_hash', 0)

    def tearDown(self):
        self._engine = None
        info = self._icon_score_mapper.get(self._icon_score_address)
        if info is not None:
            score = info.icon_score
            score.db._context_db.close(self._context)
        self._factory.destroy(self._context)

        remove_path = os.path.join(TEST_ROOT_PATH, self._ROOT_SCORE_PATH)
        IconScoreInstaller.remove_existing_score(remove_path)
        remove_path = os.path.join(TEST_ROOT_PATH, self._TEST_DB_PATH)
        IconScoreInstaller.remove_existing_score(remove_path)

    @staticmethod
    def _create_icx_storage(db_factory: DatabaseFactory) -> 'IcxStorage':
        """Create IcxStorage instance

        :param db_factory: ContextDatabase Factory
        """
        db = db_factory.create_by_name('icon_dex')
        db.address = ICX_ENGINE_ADDRESS

        return IcxStorage(db)

    @staticmethod
    def __ensure_dir(dir_path):
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)

    def test_call_method1(self):
        self.__ensure_dir(self._icon_score_loader.score_root_path)
        path = os.path.join(TEST_ROOT_PATH, 'tests/score/test_score')
        installdata = {'content_type': 'application/tbears', 'content': path}
        calldata = {'method': 'balance_of', 'params': {'addr_from': self._icon_score_address}}

        self._engine.invoke(self._context, self._icon_score_address, 'install', installdata)
        self._engine.commit()
        self.assertEqual(1000000000000000000000, self._engine.query(self._context, self._icon_score_address, 'call', calldata))

    def test_call_method2(self):
        self.__ensure_dir(self._icon_score_loader.score_root_path)
        path = os.path.join(TEST_ROOT_PATH, 'tests/score/test_score')
        installdata = {'content_type': 'application/tbears', 'content': path}
        calldata = {'method': 'balance_of', 'params': {'addr_from': str(self._icon_score_address)}}

        self._engine.invoke(self._context, self._icon_score_address, 'install', installdata)
        self._engine.commit()
        self.assertEqual(1000000000000000000000, self._engine.query(self._context, self._icon_score_address, 'call', calldata))