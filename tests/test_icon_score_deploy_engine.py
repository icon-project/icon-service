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
from unittest.mock import Mock, patch

from iconservice.base.address import AddressPrefix, ZERO_SCORE_ADDRESS, GOVERNANCE_SCORE_ADDRESS
from iconservice.base.address import ICX_ENGINE_ADDRESS
from iconservice.base.block import Block
from iconservice.base.exception import InvalidParamsException
from iconservice.base.message import Message
from iconservice.base.transaction import Transaction
from iconservice.database.factory import ContextDatabaseFactory
from iconservice.deploy import DeployType
from iconservice.deploy.icon_score_deploy_engine import IconScoreDeployEngine
from iconservice.deploy.icon_score_deploy_storage import IconScoreDeployStorage, IconScoreDeployTXParams, \
    IconScoreDeployInfo
from iconservice.icon_constant import ICON_DEX_DB_NAME, DEFAULT_BYTE_SIZE
from iconservice.iconscore.icon_score_context import IconScoreContextType, IconScoreContext, ContextContainer
from iconservice.iconscore.icon_score_loader import IconScoreLoader
from iconservice.iconscore.icon_score_mapper import IconScoreMapper
from iconservice.iconscore.icon_score_step import IconScoreStepCounter
from iconservice.iconscore.icon_score_step import IconScoreStepCounterFactory
from iconservice.icx.icx_engine import IcxEngine
from iconservice.icx.icx_storage import IcxStorage
from tests import rmtree, create_address, create_tx_hash, create_block_hash

PROJECT_ROOT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../'))


class MockScore(object):
    def __init__(self, test_case: unittest.TestCase):
        self._test_case = test_case

    def on_install(self, test1: int = 1, test2: str = 'a'):
        self._test_case.assertEqual(test1, 100)
        self._test_case.assertEqual(test2, 'hello')


class TestScoreDeployEngine(unittest.TestCase, ContextContainer):
    _ROOT_SCORE_PATH = 'tests/score'
    _TEST_DB_PATH = 'tests/test_db'

    @classmethod
    def setUpClass(cls):
        db_path = os.path.join(PROJECT_ROOT_PATH, cls._TEST_DB_PATH)
        ContextDatabaseFactory.open(
            db_path, ContextDatabaseFactory.Mode.SINGLE_DB)

    @classmethod
    def tearDownClass(cls):
        ContextDatabaseFactory.close()

    def setUp(self):
        db_path = os.path.join(PROJECT_ROOT_PATH, self._TEST_DB_PATH)
        score_path = os.path.join(PROJECT_ROOT_PATH, self._ROOT_SCORE_PATH)

        self.score_path = score_path
        self._tx_index = 0

        self.__ensure_dir(db_path)
        self._icx_db = ContextDatabaseFactory.create_by_name(ICON_DEX_DB_NAME)
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

        self.make_context()

    def tearDown(self):
        try:
            self._context = IconScoreContext(IconScoreContextType.DIRECT)
            self._icx_storage.close(self._context)
        finally:
            remove_path = os.path.join(PROJECT_ROOT_PATH, self._ROOT_SCORE_PATH)
            rmtree(remove_path)
            remove_path = os.path.join(PROJECT_ROOT_PATH, self._TEST_DB_PATH)
            rmtree(remove_path)

    def make_context(self):
        self._tx_index += 1
        self._context = IconScoreContext(IconScoreContextType.DIRECT)
        self._context.msg = Message(self._addr1, 0)

        self._context.tx = Transaction(
            create_tx_hash(), origin=self._addr1)
        self._context.block = Block(1, create_block_hash(), 0, None)
        self._context.icon_score_mapper = self._icon_score_mapper
        self._context.icx = IcxEngine()
        self.__step_counter_factory = IconScoreStepCounterFactory()
        self._step_counter: IconScoreStepCounter = \
            self.__step_counter_factory.create(100)
        self._context.step_counter = self._step_counter
        self._context.icx.open(self._icx_storage)
        self._context.event_logs = Mock(spec=list)
        self._context.traces = Mock(spec=list)

    def test_score_deploy(self):
        self._score_deploy_engine._on_deploy = Mock()
        tx_params = Mock(spec=IconScoreDeployTXParams)
        tx_params.configure_mock(deploy_data={'contentType': 'application/zip', 'content': '0x1234'})

        self._score_deploy_engine._score_deploy(self._context, tx_params)
        self._score_deploy_engine._on_deploy.assert_called()

    @patch('iconservice.iconscore.icon_score_context_util.IconScoreContextUtil.get_score_root_path')
    @patch('iconservice.iconscore.icon_score_context_util.IconScoreContextUtil.put_score_info')
    @patch('iconservice.iconscore.icon_score_context_util.IconScoreContextUtil.load_score')
    @patch('iconservice.iconscore.icon_score_context_util.IconScoreContextUtil.get_deploy_info')
    @patch('iconservice.iconscore.icon_score_context_util.IconScoreContextUtil.get_revision')
    def test_on_deploy_for_builtin(self, get_revision, get_deploy_info,
                                   load_score, put_score_info, get_score_root_path):
        get_revision.return_value = 3

        # Case when deploy_info is None
        get_score_root_path.return_value = self.score_path
        get_deploy_info.return_value = None
        load_score.return_value = MockScore(self)
        self._score_deploy_engine._initialize_score = Mock()
        tmp_dir = os.path.join(self.score_path, 'tmp')
        os.makedirs(tmp_dir)

        self._score_deploy_engine._on_deploy_for_builtin(self._context, GOVERNANCE_SCORE_ADDRESS, tmp_dir)

        get_score_root_path.assert_called()
        get_deploy_info.assert_called()
        load_score.assert_called()
        self._score_deploy_engine._initialize_score.assert_called()
        put_score_info.assert_called()

        # Case when deploy_info is not none
        deploy_info = Mock(spec=IconScoreDeployInfo)
        deploy_info.configure_mock(next_tx_hash=bytes(DEFAULT_BYTE_SIZE))
        get_deploy_info.return_value = deploy_info

        self._score_deploy_engine._on_deploy_for_builtin(self._context, GOVERNANCE_SCORE_ADDRESS, tmp_dir)

        get_score_root_path.assert_called()
        get_deploy_info.assert_called()
        load_score.assert_called()
        self._score_deploy_engine._initialize_score.assert_called()
        put_score_info.assert_called()

        # Case when score is None
        load_score.return_value = None

        self.assertRaises(InvalidParamsException, self._score_deploy_engine._on_deploy_for_builtin,
                          self._context, GOVERNANCE_SCORE_ADDRESS, tmp_dir)

    @patch('iconservice.iconscore.icon_score_context_util.IconScoreContextUtil.put_score_info')
    @patch('iconservice.iconscore.icon_score_context_util.IconScoreContextUtil.load_score')
    @patch('iconservice.iconscore.icon_score_context_util.IconScoreContextUtil.is_service_flag_on')
    @patch('iconservice.iconscore.icon_score_context_util.IconScoreContextUtil.get_deploy_info')
    @patch('iconservice.iconscore.icon_score_context_util.IconScoreContextUtil.get_revision')
    def test_on_deploy(self, get_revision, get_deploy_info, is_service_flag_on, load_score, put_score_info):

        get_revision.return_value = 3

        # Case when deploy_info is None, SCORE is not None
        score_address = create_address(1)
        deploy_content = read_zipfile_as_byte(os.path.join(PROJECT_ROOT_PATH, 'tests/sample', 'sample_token.zip'))
        deploy_data = {"contentType": "application/zip", "content": deploy_content}
        tx_params = Mock(spec=IconScoreDeployTXParams)
        tx_params.configure_mock(score_address=score_address, deploy_data=deploy_data)
        get_deploy_info.return_value = None
        is_service_flag_on.return_value = False
        mock_score = MockScore(self)
        mock_score.owner = self._addr1
        load_score.return_value = mock_score
        self._score_deploy_engine._initialize_score = Mock()

        self._score_deploy_engine._on_deploy(self._context, tx_params)
        load_score.assert_called()
        put_score_info.assert_called()

        # Case when deploy_info is not None, SCORE is not None
        deploy_info = Mock(spec=IconScoreDeployInfo)
        deploy_info.configure_mock(next_tx_hash=bytes(DEFAULT_BYTE_SIZE))
        get_deploy_info.return_value = deploy_info

        self._score_deploy_engine._on_deploy(self._context, tx_params)
        load_score.assert_called()
        put_score_info.assert_called()

        # Case when deploy_info is not None, SCORE is None
        load_score.return_value=None
        self.assertRaises(InvalidParamsException, self._score_deploy_engine._on_deploy, self._context, tx_params)

        # Case when deploy_info is None, SCORE is None
        get_deploy_info.return_value = None
        self.assertRaises(InvalidParamsException, self._score_deploy_engine._on_deploy, self._context, tx_params)

    def test_initialize_score(self):
        pass

    def test_score_deploy_for_builtin(self):
        self._score_deploy_engine._on_deploy_for_builtin = Mock()
        self._score_deploy_engine._score_deploy_for_builtin(self._context, GOVERNANCE_SCORE_ADDRESS, '.')

        self._score_deploy_engine._on_deploy_for_builtin.assert_called()

    def test_write_deploy_info_and_tx_params(self):
        self._deploy_storage.put_deploy_info_and_tx_params = Mock()
        self._score_deploy_engine.write_deploy_info_and_tx_params(self._context, DeployType.INSTALL, ZERO_SCORE_ADDRESS,
                                                                  {})

        self._deploy_storage.put_deploy_info_and_tx_params.assert_called()

    def test_write_deploy_info_and_tx_params_for_builtin(self):
        self._deploy_storage.put_deploy_info_and_tx_params_for_builtin = Mock()
        self._score_deploy_engine.write_deploy_info_and_tx_params_for_builtin(self._context, GOVERNANCE_SCORE_ADDRESS,
                                                                              self._addr1)

        self._deploy_storage.put_deploy_info_and_tx_params_for_builtin.assert_called()

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


def read_zipfile_as_byte(archive_path: str) -> bytes:
    with open(archive_path, 'rb') as f:
        byte_data = f.read()
        return byte_data
