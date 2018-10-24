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

import os
import unittest
from unittest.mock import Mock

from iconservice.base.address import AddressPrefix
from iconservice.base.address import ICX_ENGINE_ADDRESS
from iconservice.base.block import Block
from iconservice.base.message import Message
from iconservice.base.transaction import Transaction
from iconservice.database.factory import ContextDatabaseFactory
from iconservice.deploy.icon_score_deploy_engine import IconScoreDeployEngine
from iconservice.deploy.icon_score_deploy_storage import IconScoreDeployStorage
from iconservice.iconscore.icon_score_context import IconScoreContextFactory
from iconservice.iconscore.icon_score_context import IconScoreContextType
from iconservice.iconscore.icon_score_mapper import IconScoreMapper
from iconservice.iconscore.icon_score_loader import IconScoreLoader
from iconservice.iconscore.icon_score_step import IconScoreStepCounter
from iconservice.iconscore.icon_score_step import IconScoreStepCounterFactory
from iconservice.icx.icx_engine import IcxEngine
from iconservice.icx.icx_storage import IcxStorage
from tests import rmtree, create_address, create_tx_hash, create_block_hash

TEST_ROOT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../'))


class MockScore(object):
    def __init__(self, test_case: unittest.TestCase):
        self._test_case = test_case

    def on_install(self, test1: int = 1, test2: str = 'a'):
        self._test_case.assertEqual(test1, 100)
        self._test_case.assertEqual(test2, 'hello')


class TestScoreDeployEngine(unittest.TestCase):
    _ROOT_SCORE_PATH = 'tests/score'
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
        db_path = os.path.join(TEST_ROOT_PATH, self._TEST_DB_PATH)
        score_path = os.path.join(TEST_ROOT_PATH, self._ROOT_SCORE_PATH)

        self._tx_index = 0

        self.__ensure_dir(db_path)
        self._icx_db = ContextDatabaseFactory.create_by_name('icon_dex')
        self._icx_db.address = ICX_ENGINE_ADDRESS
        self._icx_storage = IcxStorage(self._icx_db)
        self._score_deploy_engine = IconScoreDeployEngine()
        self._deploy_storage = IconScoreDeployStorage(self._icx_db)

        self._icon_score_loader = IconScoreLoader(score_path)
        self._icon_score_mapper = IconScoreMapper()

        self._addr1 = create_address(AddressPrefix.EOA)
        self._score_deploy_engine.open(
            score_root_path=score_path,
            icon_deploy_storage=self._deploy_storage)

        self._factory = IconScoreContextFactory(max_size=1)
        self.make_context()

    def tearDown(self):
        try:
            self._context = self._factory.create(IconScoreContextType.DIRECT)
            self._factory.destroy(self._context)
            self._icx_storage.close(self._context)
        finally:
            remove_path = os.path.join(TEST_ROOT_PATH, self._ROOT_SCORE_PATH)
            rmtree(remove_path)
            remove_path = os.path.join(TEST_ROOT_PATH, self._TEST_DB_PATH)
            rmtree(remove_path)

    def make_context(self):
        self._tx_index += 1
        self._context = self._factory.create(IconScoreContextType.DIRECT)
        self._context.msg = Message(self._addr1, 0)

        self._context.tx = Transaction(
            create_tx_hash(), origin=self._addr1)
        self._context.block = Block(1, create_block_hash(), 0, None)
        self._context.icon_score_mapper = self._icon_score_mapper
        self._context.icx = IcxEngine()
        self._step_counter: IconScoreStepCounter = IconScoreStepCounterFactory.create(self._context, 100)
        self._context.step_counter = self._step_counter
        self._context.icx.open(self._icx_storage)
        self._context.event_logs = Mock(spec=list)
        self._context.traces = Mock(spec=list)

    @staticmethod
    def __ensure_dir(dir_path):
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)

    # def test_goverance_score_load(self):
    #     self._score_deploy_engine.invoke(
    #         self._context,
    #         ZERO_SCORE_ADDRESS,
    #         create_address(AddressPrefix.CONTRACT, b'mock'),
    #         {})
