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
from functools import wraps
from unittest.mock import Mock, patch

from iconservice.base.address import AddressPrefix, ZERO_SCORE_ADDRESS, GOVERNANCE_SCORE_ADDRESS
from iconservice.base.address import ICX_ENGINE_ADDRESS
from iconservice.base.block import Block
from iconservice.base.exception import InvalidParamsException, ExceptionCode
from iconservice.base.message import Message
from iconservice.base.transaction import Transaction
from iconservice.database.factory import ContextDatabaseFactory
from iconservice.deploy import DeployType
from iconservice.deploy.icon_score_deploy_engine import IconScoreDeployEngine, DirectoryNameChanger
from iconservice.deploy.icon_score_deploy_storage import IconScoreDeployStorage, IconScoreDeployTXParams, \
    IconScoreDeployInfo
from iconservice.icon_constant import ICON_DEX_DB_NAME, DEFAULT_BYTE_SIZE
from iconservice.iconscore.icon_score_context import IconScoreContextType, IconScoreContext, ContextContainer
from iconservice.iconscore.icon_score_context_util import IconScoreContextUtil
from iconservice.iconscore.icon_score_loader import IconScoreLoader
from iconservice.iconscore.icon_score_mapper import IconScoreMapper
from iconservice.iconscore.icon_score_step import IconScoreStepCounter
from iconservice.iconscore.icon_score_step import IconScoreStepCounterFactory
from iconservice.icx.icx_engine import IcxEngine
from iconservice.icx.icx_storage import IcxStorage
from tests import rmtree, create_address, create_tx_hash, create_block_hash

PROJECT_ROOT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../'))

PUT_SCORE_INFO_PATCHER = patch('iconservice.iconscore.icon_score_context_util.IconScoreContextUtil.put_score_info')
LOAD_SCORE_PATCHER = patch('iconservice.iconscore.icon_score_context_util.IconScoreContextUtil.load_score')
IS_SERVICE_FLAG_ON_PATCHER = patch('iconservice.iconscore.\
icon_score_context_util.IconScoreContextUtil.is_service_flag_on')
GET_DEPLOY_INFO_PATCHER = patch('iconservice.iconscore.icon_score_context_util.IconScoreContextUtil.get_deploy_info')
GET_SCORE_ROOT_PATH_PATCHER = patch('iconservice.iconscore.\
icon_score_context_util.IconScoreContextUtil.get_score_root_path')
COPY_TREE_PATCHER = patch('iconservice.deploy.icon_score_deploy_engine.copytree')
GET_REVISION_PATCHER = patch('iconservice.iconscore.icon_score_context_util.IconScoreContextUtil.get_revision')
GET_OWNER_PATCHER = patch('iconservice.iconscore.icon_score_context_util.IconScoreContextUtil.get_owner')
GET_IS_SERVICE_FLAG_ON = patch('iconservice.iconscore.icon_score_context_util.IconScoreContextUtil.is_service_flag_on')
GET_DEPLOY_TX_PARAMS_PATCHER = patch('iconservice.iconscore.icon_score_context_util.\
IconScoreContextUtil.get_deploy_tx_params')
VALIDATE_SCORE_BLACKLIST_PATCHER = patch('iconservice.iconscore.icon_score_context_util.\
IconScoreContextUtil.validate_score_blacklist')
VALIDATE_DEPLOYER = patch('iconservice.iconscore.icon_score_context_util.\
IconScoreContextUtil.validate_deployer')
TRY_SCORE_PACKAGE_VALIDATE_PATCHER = patch('iconservice.iconscore.icon_score_context_util.\
IconScoreContextUtil.try_score_package_validate')
RENAME_DIRECTORY_PATCHER = patch('iconservice.deploy.icon_score_deploy_engine.DirectoryNameChanger.rename_directory')
SYMLINK_PATCHER = patch('iconservice.deploy.icon_score_deploy_engine.symlink')


class MockScore(object):
    def __init__(self, test_case: unittest.TestCase):
        self._test_case = test_case

    def on_install(self, test1: int = 1, test2: str = 'a'):
        self._test_case.assertEqual(test1, 100)
        self._test_case.assertEqual(test2, 'hello')


def start_patches(*args):
    for patcher in args:
        patcher.start()


def stop_patches(*args):
    for patcher in args:
        patcher.stop()


def patch_several(*decorate_args):

    def decorate(func):

        @wraps(func)
        def wrapper(*args, **kwargs):
            start_patches(*decorate_args)
            ret = func(*args, **kwargs)
            stop_patches(*decorate_args)
            return ret

        return wrapper

    return decorate


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

    # case when icon_score_address is in (None, ZERO_ADDRESS)
    @patch_several(VALIDATE_SCORE_BLACKLIST_PATCHER, IS_SERVICE_FLAG_ON_PATCHER, VALIDATE_DEPLOYER)
    def test_invoke_case1(self):
        IconScoreContextUtil.is_service_flag_on.return_value = True
        self._score_deploy_engine._check_audit_ignore = Mock(return_value=True)
        self._score_deploy_engine.deploy = Mock()
        self._score_deploy_engine.write_deploy_info_and_tx_params = Mock()

        with self.assertRaises(AssertionError):
            self._score_deploy_engine.invoke(self._context, GOVERNANCE_SCORE_ADDRESS, ZERO_SCORE_ADDRESS, {})
        IconScoreContextUtil.validate_score_blacklist.assert_not_called()
        IconScoreContextUtil.is_service_flag_on.assert_not_called()
        IconScoreContextUtil.validate_deployer.assert_not_called()
        self._score_deploy_engine.write_deploy_info_and_tx_params.assert_not_called()
        self._score_deploy_engine._check_audit_ignore.assert_not_called()
        self._score_deploy_engine.deploy.assert_not_called()

        with self.assertRaises(AssertionError):
            self._score_deploy_engine.invoke(self._context, GOVERNANCE_SCORE_ADDRESS, None, {})
        IconScoreContextUtil.validate_score_blacklist.assert_not_called()
        IconScoreContextUtil.is_service_flag_on.assert_not_called()
        IconScoreContextUtil.validate_deployer.assert_not_called()
        self._score_deploy_engine.write_deploy_info_and_tx_params.assert_not_called()
        self._score_deploy_engine._check_audit_ignore.assert_not_called()
        self._score_deploy_engine.deploy.assert_not_called()

    # case when deployer_white_list flag on, ignore audit
    @patch_several(VALIDATE_SCORE_BLACKLIST_PATCHER, IS_SERVICE_FLAG_ON_PATCHER, VALIDATE_DEPLOYER)
    def test_invoke_case2(self):
        IconScoreContextUtil.is_service_flag_on.return_value = True
        self._score_deploy_engine._check_audit_ignore = Mock(return_value=True)
        self._score_deploy_engine.deploy = Mock()
        self._score_deploy_engine.write_deploy_info_and_tx_params = Mock()

        self._score_deploy_engine.invoke(self._context, ZERO_SCORE_ADDRESS, GOVERNANCE_SCORE_ADDRESS, {})

        IconScoreContextUtil.validate_deployer.assert_called_with(self._context, self._context.tx.origin)
        self._score_deploy_engine.write_deploy_info_and_tx_params.\
            assert_called_with(self._context, DeployType.INSTALL, GOVERNANCE_SCORE_ADDRESS, {})
        self._score_deploy_engine.deploy.assert_called_with(self._context, self._context.tx.hash)

    # case when deployer_white_list flag on, audit
    @patch_several(VALIDATE_SCORE_BLACKLIST_PATCHER, IS_SERVICE_FLAG_ON_PATCHER, VALIDATE_DEPLOYER)
    def test_invoke_case3(self):
        IconScoreContextUtil.is_service_flag_on.return_value = True
        self._score_deploy_engine._check_audit_ignore = Mock(return_value=False)
        self._score_deploy_engine.deploy = Mock()
        self._score_deploy_engine.write_deploy_info_and_tx_params = Mock()

        self._score_deploy_engine.invoke(self._context, ZERO_SCORE_ADDRESS, GOVERNANCE_SCORE_ADDRESS, {})

        IconScoreContextUtil.validate_deployer.assert_called_with(self._context, self._context.tx.origin)
        self._score_deploy_engine.write_deploy_info_and_tx_params.\
            assert_called_with(self._context, DeployType.INSTALL, GOVERNANCE_SCORE_ADDRESS, {})
        self._score_deploy_engine.deploy.assert_not_called()

    # case when deployer_white_list flag off, audit
    @patch_several(VALIDATE_SCORE_BLACKLIST_PATCHER, IS_SERVICE_FLAG_ON_PATCHER, VALIDATE_DEPLOYER)
    def test_invoke_case4(self):
        IconScoreContextUtil.is_service_flag_on.return_value = False
        self._score_deploy_engine._check_audit_ignore = Mock(return_value=False)
        self._score_deploy_engine.deploy = Mock()
        self._score_deploy_engine.write_deploy_info_and_tx_params = Mock()

        self._score_deploy_engine.invoke(self._context, ZERO_SCORE_ADDRESS, GOVERNANCE_SCORE_ADDRESS, {})

        IconScoreContextUtil.validate_deployer.assert_not_called()
        self._score_deploy_engine.write_deploy_info_and_tx_params.\
            assert_called_with(self._context, DeployType.INSTALL, GOVERNANCE_SCORE_ADDRESS, {})
        self._score_deploy_engine.deploy.assert_not_called()

    # case when deployer_white_list flag off, audit on
    @patch_several(VALIDATE_SCORE_BLACKLIST_PATCHER, IS_SERVICE_FLAG_ON_PATCHER, VALIDATE_DEPLOYER)
    def test_invoke_case5(self):
        IconScoreContextUtil.is_service_flag_on.return_value = False
        self._score_deploy_engine._check_audit_ignore = Mock(return_value=True)
        self._score_deploy_engine.deploy = Mock()
        self._score_deploy_engine.write_deploy_info_and_tx_params = Mock()

        self._score_deploy_engine.invoke(self._context, ZERO_SCORE_ADDRESS, GOVERNANCE_SCORE_ADDRESS, {})

        IconScoreContextUtil.validate_deployer.assert_not_called()
        self._score_deploy_engine.write_deploy_info_and_tx_params.\
            assert_called_with(self._context, DeployType.INSTALL, GOVERNANCE_SCORE_ADDRESS, {})
        self._score_deploy_engine.deploy.assert_called_with(self._context, self._context.tx.hash)

    # case when audit disable
    @patch_several(GET_REVISION_PATCHER, GET_OWNER_PATCHER, IS_SERVICE_FLAG_ON_PATCHER)
    def test_check_audit_ignore_case1(self):
        IconScoreContextUtil.get_revision.return_value = 0
        IconScoreContextUtil.is_service_flag_on.return_value = False
        IconScoreContextUtil.get_owner.return_value = self._addr1

        result = self._score_deploy_engine._check_audit_ignore(self._context, GOVERNANCE_SCORE_ADDRESS)
        self.assertTrue(result)

    # case when audit enable, revision2, transaction requested by owner
    @patch_several(GET_REVISION_PATCHER, GET_OWNER_PATCHER, IS_SERVICE_FLAG_ON_PATCHER)
    def test_check_audit_ignore_case2(self):
        IconScoreContextUtil.get_revision.return_value = 2
        IconScoreContextUtil.is_service_flag_on.return_value = True
        IconScoreContextUtil.get_owner.return_value = self._addr1

        result = self._score_deploy_engine._check_audit_ignore(self._context, GOVERNANCE_SCORE_ADDRESS)

        self.assertTrue(result)

    # case when audit enable, revision2, transaction requested by stranger
    @patch_several(GET_REVISION_PATCHER, GET_OWNER_PATCHER, IS_SERVICE_FLAG_ON_PATCHER)
    def test_check_audit_ignore_case3(self):
        IconScoreContextUtil.get_revision.return_value = 2
        IconScoreContextUtil.is_service_flag_on.return_value = True
        IconScoreContextUtil.get_owner.return_value = create_address(0)

        result = self._score_deploy_engine._check_audit_ignore(self._context, GOVERNANCE_SCORE_ADDRESS)

        self.assertFalse(result)

    # case when audit enable, revision0, transaction requested by stranger
    @patch_several(GET_REVISION_PATCHER, GET_OWNER_PATCHER, IS_SERVICE_FLAG_ON_PATCHER)
    def test_check_audit_ignore_case4(self):
        IconScoreContextUtil.get_revision.return_value = 0
        IconScoreContextUtil.is_service_flag_on.return_value = True
        IconScoreContextUtil.get_owner.return_value = self._addr1

        result = self._score_deploy_engine._check_audit_ignore(self._context, GOVERNANCE_SCORE_ADDRESS)

        self.assertFalse(result)

    # case when audit enable, revision0, transaction requested by stranger
    @patch_several(GET_REVISION_PATCHER, GET_OWNER_PATCHER, IS_SERVICE_FLAG_ON_PATCHER)
    def test_check_audit_ignore_case5(self):
        IconScoreContextUtil.get_revision.return_value = 0
        IconScoreContextUtil.is_service_flag_on.return_value = True
        IconScoreContextUtil.get_owner.return_value = create_address(0)

        result = self._score_deploy_engine._check_audit_ignore(self._context, GOVERNANCE_SCORE_ADDRESS)

        self.assertFalse(result)

    # case when tx_param is None
    @patch_several(GET_DEPLOY_TX_PARAMS_PATCHER)
    def test_deploy_case1(self):
        self._score_deploy_engine._score_deploy = Mock()
        self._score_deploy_engine._icon_score_deploy_storage.update_score_info = Mock()
        IconScoreContextUtil.get_deploy_tx_params.return_value = None

        with self.assertRaises(InvalidParamsException) as e:
            self._score_deploy_engine.deploy(self._context, self._context.tx.hash)

        IconScoreContextUtil.get_deploy_tx_params.assert_called_with(self._context, self._context.tx.hash)
        self.assertEqual(e.exception.message, f'tx_params is None : {self._context.tx.hash}')
        self.assertEqual(e.exception.code, ExceptionCode.INVALID_PARAMS)
        self._score_deploy_engine._score_deploy.assert_not_called()
        self._score_deploy_engine._icon_score_deploy_storage.update_score_info.assert_not_called()

    # case when tx_param is not None
    @patch_several(GET_DEPLOY_TX_PARAMS_PATCHER)
    def test_deploy_case2(self):
        self._score_deploy_engine._score_deploy = Mock()
        self._score_deploy_engine._icon_score_deploy_storage.update_score_info = Mock()
        tx_params = Mock(spec=IconScoreDeployTXParams)
        tx_params.configure_mock(score_address=GOVERNANCE_SCORE_ADDRESS)
        IconScoreContextUtil.get_deploy_tx_params.return_value = tx_params

        self._score_deploy_engine.deploy(self._context, self._context.tx.hash)

        self._score_deploy_engine._score_deploy.assert_called_with(self._context, tx_params)
        self._score_deploy_engine._icon_score_deploy_storage.\
            update_score_info.assert_called_with(self._context, GOVERNANCE_SCORE_ADDRESS, self._context.tx.hash)

    def test_deploy_for_builtin(self):
        self._score_deploy_engine._score_deploy_for_builtin = Mock()

        self._score_deploy_engine.deploy_for_builtin(self._context, GOVERNANCE_SCORE_ADDRESS, '.')

        self._score_deploy_engine._score_deploy_for_builtin.assert_called_with(self._context, GOVERNANCE_SCORE_ADDRESS,
                                                                               '.')

    # test for tbears mode and legacy_tbears_mode is True
    def test_score_deploy_case1(self):
        self._score_deploy_engine._on_deploy = Mock()
        tx_params = Mock(spec=IconScoreDeployTXParams)
        self._context.legacy_tbears_mode = True
        tx_params.configure_mock(deploy_data={'contentType': 'application/tbears', 'content': '0x1234'})

        self._score_deploy_engine._score_deploy(self._context, tx_params)

        self._score_deploy_engine._on_deploy.assert_called_with(self._context, tx_params)

    # test for tbears mode and legacy_tbears_mode is False
    def test_score_deploy_case2(self):
        self._score_deploy_engine._on_deploy = Mock()
        tx_params = Mock(spec=IconScoreDeployTXParams)
        tx_params.configure_mock(deploy_data={'contentType': 'application/tbears', 'content': '0x1234'})

        with self.assertRaises(InvalidParamsException) as e:
            self._score_deploy_engine._score_deploy(self._context, tx_params)
        self.assertEqual(e.exception.code, ExceptionCode.INVALID_PARAMS)
        self.assertEqual(e.exception.message, f"can't symlink deploy")
        self._score_deploy_engine._on_deploy.assert_not_called()

    # test for zip mode
    def test_score_deploy_case3(self):
        self._score_deploy_engine._on_deploy = Mock()
        tx_params = Mock(spec=IconScoreDeployTXParams)
        tx_params.configure_mock(deploy_data={'contentType': 'application/zip', 'content': '0x1234'})

        self._score_deploy_engine._score_deploy(self._context, tx_params)

        self._score_deploy_engine._on_deploy.assert_called_with(self._context, tx_params)

    # test for wrong contentType
    def test_score_deploy_case4(self):
        self._score_deploy_engine._on_deploy = Mock()
        tx_params = Mock(spec=IconScoreDeployTXParams)
        tx_params.configure_mock(deploy_data={'contentType': 'wrong/content', 'content': '0x1234'})

        with self.assertRaises(InvalidParamsException) as e:
            self._score_deploy_engine._score_deploy(self._context, tx_params)
        self.assertEqual(e.exception.code, ExceptionCode.INVALID_PARAMS)
        self.assertEqual(e.exception.message, f'Invalid contentType: wrong/content')
        self._score_deploy_engine._on_deploy.assert_not_called()

    def test_score_deploy_for_builtin(self):
        self._score_deploy_engine._on_deploy_for_builtin = Mock()

        self._score_deploy_engine._score_deploy_for_builtin(self._context, GOVERNANCE_SCORE_ADDRESS, '.')

        self._score_deploy_engine._on_deploy_for_builtin.assert_called_with(self._context,
                                                                            GOVERNANCE_SCORE_ADDRESS, '.')

    def test_write_deploy_info_and_tx_params(self):
        self._deploy_storage.put_deploy_info_and_tx_params = Mock()

        self._score_deploy_engine.write_deploy_info_and_tx_params(self._context, DeployType.INSTALL, ZERO_SCORE_ADDRESS,
                                                                  {})

        self._deploy_storage.put_deploy_info_and_tx_params.\
            assert_called_with(self._context, ZERO_SCORE_ADDRESS, DeployType.INSTALL,
                               self._context.tx.origin, self._context.tx.hash, {})

    def test_write_deploy_info_and_tx_params_for_builtin(self):
        self._deploy_storage.put_deploy_info_and_tx_params_for_builtin = Mock()

        self._score_deploy_engine.write_deploy_info_and_tx_params_for_builtin(self._context, GOVERNANCE_SCORE_ADDRESS,
                                                                              self._addr1)

        self._deploy_storage.put_deploy_info_and_tx_params_for_builtin.\
            assert_called_with(self._context, GOVERNANCE_SCORE_ADDRESS, self._addr1)

    # Case when deploy_info is not none
    @patch_several(GET_DEPLOY_INFO_PATCHER, LOAD_SCORE_PATCHER, PUT_SCORE_INFO_PATCHER, GET_SCORE_ROOT_PATH_PATCHER,
                   COPY_TREE_PATCHER)
    def test_on_deploy_for_builtin_case1(self):

        IconScoreContextUtil.get_score_root_path.return_value = self.score_path
        IconScoreContextUtil.get_deploy_info.return_value = None
        IconScoreContextUtil.load_score.return_value = MockScore(self)
        self._score_deploy_engine._initialize_score = Mock()
        tmp_dir = 'tmp'
        deploy_info = Mock(spec=IconScoreDeployInfo)
        next_tx_hash = b'\00\0x' * 16
        mock_score = MockScore(self)
        IconScoreContextUtil.load_score.return_value = mock_score
        deploy_info.configure_mock(next_tx_hash=next_tx_hash)
        IconScoreContextUtil.get_deploy_info.return_value = deploy_info

        self._score_deploy_engine._on_deploy_for_builtin(self._context, GOVERNANCE_SCORE_ADDRESS, tmp_dir)

        IconScoreContextUtil.get_score_root_path.assert_called_with(self._context)
        IconScoreContextUtil.get_deploy_info.assert_called_with(self._context, GOVERNANCE_SCORE_ADDRESS)
        IconScoreContextUtil.load_score.assert_called_with(self._context, GOVERNANCE_SCORE_ADDRESS, next_tx_hash)
        self._score_deploy_engine._initialize_score.assert_called_with(on_deploy=mock_score.on_install, params={})
        IconScoreContextUtil.put_score_info.assert_called()

    # Case when deploy_info is None
    @patch_several(GET_DEPLOY_INFO_PATCHER, LOAD_SCORE_PATCHER, PUT_SCORE_INFO_PATCHER, GET_SCORE_ROOT_PATH_PATCHER,
                   COPY_TREE_PATCHER)
    def test_on_deploy_for_builtin_case2(self):
        IconScoreContextUtil.get_score_root_path.return_value = self.score_path
        IconScoreContextUtil.get_deploy_info.return_value = None
        mock_score = MockScore(self)
        IconScoreContextUtil.load_score.return_value = mock_score
        self._score_deploy_engine._initialize_score = Mock()
        tmp_dir = 'tmp'

        self._score_deploy_engine._on_deploy_for_builtin(self._context, GOVERNANCE_SCORE_ADDRESS, tmp_dir)

        IconScoreContextUtil.get_score_root_path.assert_called_with(self._context)
        IconScoreContextUtil.get_deploy_info.assert_called_with(self._context, GOVERNANCE_SCORE_ADDRESS)
        IconScoreContextUtil.load_score.assert_called_with(self._context, GOVERNANCE_SCORE_ADDRESS,
                                                           bytes(DEFAULT_BYTE_SIZE))
        self._score_deploy_engine._initialize_score.assert_called_with(on_deploy=mock_score.on_install, params={})
        IconScoreContextUtil.put_score_info.assert_called_with(self._context, GOVERNANCE_SCORE_ADDRESS,
                                                               mock_score, bytes(DEFAULT_BYTE_SIZE))

    # Case when score is none
    @patch_several(GET_DEPLOY_INFO_PATCHER, LOAD_SCORE_PATCHER, PUT_SCORE_INFO_PATCHER, GET_SCORE_ROOT_PATH_PATCHER,
                   COPY_TREE_PATCHER)
    def test_on_deploy_for_builtin_case3(self):
        IconScoreContextUtil.get_score_root_path.return_value = self.score_path
        IconScoreContextUtil.load_score.return_value = MockScore(self)
        self._score_deploy_engine._initialize_score = Mock()
        tmp_dir = 'tmp'
        deploy_info = Mock(spec=IconScoreDeployInfo)
        next_tx_hash = b'\00\01' * 16
        deploy_info.configure_mock(next_tx_hash=next_tx_hash)
        IconScoreContextUtil.get_deploy_info.return_value = deploy_info

        # Case when score is None
        IconScoreContextUtil.load_score.return_value = None

        with self.assertRaises(InvalidParamsException) as e:
            self._score_deploy_engine._on_deploy_for_builtin(self._context, GOVERNANCE_SCORE_ADDRESS, tmp_dir)
        self.assertEqual(e.exception.code, ExceptionCode.INVALID_PARAMS)
        self.assertEqual(e.exception.message, f'score is None : {GOVERNANCE_SCORE_ADDRESS}')
        IconScoreContextUtil.get_score_root_path.assert_called_with(self._context)
        IconScoreContextUtil.get_deploy_info.assert_called_with(self._context, GOVERNANCE_SCORE_ADDRESS)
        IconScoreContextUtil.load_score.assert_called_with(self._context, GOVERNANCE_SCORE_ADDRESS, next_tx_hash)
        self._score_deploy_engine._initialize_score.assert_not_called()

    # Case when deploy_info is not None, zip, revision0, score validator flag False, SCORE is not None
    @patch_several(GET_DEPLOY_INFO_PATCHER, IS_SERVICE_FLAG_ON_PATCHER, LOAD_SCORE_PATCHER,
                   PUT_SCORE_INFO_PATCHER, TRY_SCORE_PACKAGE_VALIDATE_PATCHER)
    def test_on_deploy_case1(self):
        score_address = create_address(1)
        deploy_content = b'deploy_mock_data'
        deploy_data = {"contentType": "application/zip", "content": deploy_content}
        tx_params = Mock(spec=IconScoreDeployTXParams)
        tx_params.configure_mock(score_address=score_address, deploy_data=deploy_data)
        IconScoreContextUtil.is_service_flag_on.return_value = False
        self._score_deploy_engine._icon_score_deployer.deploy_legacy = Mock()
        mock_score = MockScore(self)
        mock_score.owner = self._addr1
        IconScoreContextUtil.load_score.return_value = mock_score
        self._score_deploy_engine._initialize_score = Mock()
        deploy_info = Mock(spec=IconScoreDeployInfo)
        next_tx_hash = b'\00\01' * 16
        deploy_info.configure_mock(next_tx_hash=next_tx_hash)
        IconScoreContextUtil.get_deploy_info.return_value = deploy_info

        self._score_deploy_engine._on_deploy(self._context, tx_params)

        IconScoreContextUtil.load_score.assert_called_with(self._context, score_address, next_tx_hash)
        self._score_deploy_engine._icon_score_deployer.\
            deploy_legacy.assert_called_with(address=score_address, data=deploy_content, tx_hash=next_tx_hash)
        self._score_deploy_engine._initialize_score.assert_called()
        IconScoreContextUtil.try_score_package_validate.assert_not_called()
        IconScoreContextUtil.put_score_info.assert_called_with(self._context, score_address, mock_score, next_tx_hash)

    # Case when deploy_info is not None, zip, revision0, score validator flag False, SCORE is None
    @patch_several(GET_DEPLOY_INFO_PATCHER, IS_SERVICE_FLAG_ON_PATCHER, LOAD_SCORE_PATCHER,
                   PUT_SCORE_INFO_PATCHER, TRY_SCORE_PACKAGE_VALIDATE_PATCHER)
    def test_on_deploy_case2(self):
        score_address = create_address(1)
        deploy_content = b'deploy_mock_data'
        deploy_data = {"contentType": "application/zip", "content": deploy_content}
        tx_params = Mock(spec=IconScoreDeployTXParams)
        tx_params.configure_mock(score_address=score_address, deploy_data=deploy_data)
        IconScoreContextUtil.is_service_flag_on.return_value = False
        self._score_deploy_engine._icon_score_deployer.deploy_legacy = Mock()
        IconScoreContextUtil.load_score.return_value = None
        self._score_deploy_engine._initialize_score = Mock()
        deploy_info = Mock(spec=IconScoreDeployInfo)
        next_tx_hash = b'\00\0x' * 16
        deploy_info.configure_mock(next_tx_hash=next_tx_hash)
        IconScoreContextUtil.get_deploy_info.return_value = deploy_info

        with self.assertRaises(InvalidParamsException) as e:
            self._score_deploy_engine._on_deploy(self._context, tx_params)
        self.assertEqual(e.exception.code, ExceptionCode.INVALID_PARAMS)
        self.assertEqual(e.exception.message, f'score is None : {score_address}')
        IconScoreContextUtil.get_deploy_info.assert_called()
        IconScoreContextUtil.is_service_flag_on.assert_called()
        IconScoreContextUtil.try_score_package_validate.assert_not_called()
        self._score_deploy_engine._icon_score_deployer.deploy_legacy.assert_called()
        self._score_deploy_engine._initialize_score.assert_not_called()

    # Case when deploy_info is not None, zip, revision0, score validator flag True, SCORE is not None
    @patch_several(GET_DEPLOY_INFO_PATCHER, IS_SERVICE_FLAG_ON_PATCHER, LOAD_SCORE_PATCHER,
                   PUT_SCORE_INFO_PATCHER, TRY_SCORE_PACKAGE_VALIDATE_PATCHER)
    def test_on_deploy_case3(self):
        score_address = create_address(1)
        deploy_content = b'deploy_mock_data'
        deploy_data = {"contentType": "application/zip", "content": deploy_content}
        tx_params = Mock(spec=IconScoreDeployTXParams)
        tx_params.configure_mock(score_address=score_address, deploy_data=deploy_data)
        IconScoreContextUtil.get_deploy_info.return_value = None
        IconScoreContextUtil.is_service_flag_on.return_value = True
        self._score_deploy_engine._icon_score_deployer.deploy_legacy = Mock()
        mock_score = MockScore(self)
        mock_score.owner = self._addr1
        IconScoreContextUtil.load_score.return_value = mock_score
        self._score_deploy_engine._initialize_score = Mock()
        deploy_info = Mock(spec=IconScoreDeployInfo)
        next_tx_hash = b'\00\0x' * 16
        deploy_info.configure_mock(next_tx_hash=next_tx_hash)
        IconScoreContextUtil.get_deploy_info.return_value = deploy_info

        self._score_deploy_engine._on_deploy(self._context, tx_params)

        IconScoreContextUtil.load_score.assert_called_with(self._context, score_address, next_tx_hash)
        self._score_deploy_engine._initialize_score.assert_called()
        IconScoreContextUtil.try_score_package_validate.assert_called_with(self._context, score_address, next_tx_hash)
        self._score_deploy_engine._icon_score_deployer.\
            deploy_legacy.assert_called_with(address=score_address, data=deploy_content, tx_hash=next_tx_hash)
        IconScoreContextUtil.put_score_info.assert_called_with(self._context, score_address, mock_score, next_tx_hash)

    # Case when deploy_info is not None, zip, revision0, score validator flag True, SCORE is None
    @patch_several(GET_DEPLOY_INFO_PATCHER, IS_SERVICE_FLAG_ON_PATCHER, LOAD_SCORE_PATCHER,
                   PUT_SCORE_INFO_PATCHER, TRY_SCORE_PACKAGE_VALIDATE_PATCHER)
    def test_on_deploy_case4(self):
        score_address = create_address(1)
        deploy_content = b'deploy_mock_data'
        deploy_data = {"contentType": "application/zip", "content": deploy_content}
        tx_params = Mock(spec=IconScoreDeployTXParams)
        tx_params.configure_mock(score_address=score_address, deploy_data=deploy_data)
        IconScoreContextUtil.is_service_flag_on.return_value = False
        IconScoreContextUtil.load_score.return_value = None
        self._score_deploy_engine._icon_score_deployer.deploy_legacy = Mock()
        self._score_deploy_engine._initialize_score = Mock()
        deploy_info = Mock(spec=IconScoreDeployInfo)
        next_tx_hash = b'\00\0x' * 16
        deploy_info.configure_mock(next_tx_hash=next_tx_hash)
        IconScoreContextUtil.get_deploy_info.return_value = deploy_info

        with self.assertRaises(InvalidParamsException) as e:
            self._score_deploy_engine._on_deploy(self._context, tx_params)
        self.assertEqual(e.exception.code, ExceptionCode.INVALID_PARAMS)
        self.assertEqual(e.exception.message, f'score is None : {score_address}')
        IconScoreContextUtil.get_deploy_info.assert_called()
        IconScoreContextUtil.is_service_flag_on.assert_called()
        IconScoreContextUtil.try_score_package_validate.assert_not_called()
        self._score_deploy_engine._icon_score_deployer.deploy_legacy.assert_called()
        self._score_deploy_engine._initialize_score.assert_not_called()

    # Case when deploy_info is not None, zip, revision2, score validator flag False, SCORE is not None
    @patch_several(GET_DEPLOY_INFO_PATCHER, IS_SERVICE_FLAG_ON_PATCHER, LOAD_SCORE_PATCHER,
                   PUT_SCORE_INFO_PATCHER, TRY_SCORE_PACKAGE_VALIDATE_PATCHER,
                   GET_REVISION_PATCHER)
    def test_on_deploy_case5(self):
        score_address = create_address(1)
        deploy_content = b'deploy_mock_data'
        deploy_data = {"contentType": "application/zip", "content": deploy_content}
        tx_params = Mock(spec=IconScoreDeployTXParams)
        tx_params.configure_mock(score_address=score_address, deploy_data=deploy_data)
        IconScoreContextUtil.is_service_flag_on.return_value = False
        IconScoreContextUtil.get_revision.return_value = 2
        self._score_deploy_engine._icon_score_deployer.deploy = Mock()
        mock_score = MockScore(self)
        mock_score.owner = self._addr1
        IconScoreContextUtil.load_score.return_value = mock_score
        self._score_deploy_engine._initialize_score = Mock()
        deploy_info = Mock(spec=IconScoreDeployInfo)
        next_tx_hash = b'\00\0x' * 16
        deploy_info.configure_mock(next_tx_hash=next_tx_hash)
        IconScoreContextUtil.get_deploy_info.return_value = deploy_info

        self._score_deploy_engine._on_deploy(self._context, tx_params)

        IconScoreContextUtil.get_deploy_info.assert_called_with(self._context, score_address)
        IconScoreContextUtil.load_score.assert_called_with(self._context, score_address, next_tx_hash)
        self._score_deploy_engine._icon_score_deployer.\
            deploy.assert_called_with(address=score_address, data=deploy_content, tx_hash=next_tx_hash)
        self._score_deploy_engine._initialize_score.assert_called()
        IconScoreContextUtil.try_score_package_validate.assert_not_called()
        IconScoreContextUtil.put_score_info.assert_called_with(self._context, score_address, mock_score, next_tx_hash)

    # Case when deploy_info is not None, zip, revision2, score validator flag False, SCORE is None
    @patch_several(GET_DEPLOY_INFO_PATCHER, IS_SERVICE_FLAG_ON_PATCHER, LOAD_SCORE_PATCHER,
                   PUT_SCORE_INFO_PATCHER, TRY_SCORE_PACKAGE_VALIDATE_PATCHER,
                   GET_REVISION_PATCHER)
    def test_on_deploy_case6(self):
        score_address = create_address(1)
        deploy_content = b'deploy_mock_data'
        deploy_data = {"contentType": "application/zip", "content": deploy_content}
        tx_params = Mock(spec=IconScoreDeployTXParams)
        tx_params.configure_mock(score_address=score_address, deploy_data=deploy_data)
        IconScoreContextUtil.is_service_flag_on.return_value = False
        IconScoreContextUtil.get_revision.return_value = 2
        self._score_deploy_engine._icon_score_deployer.deploy = Mock()
        IconScoreContextUtil.load_score.return_value = None
        self._score_deploy_engine._initialize_score = Mock()
        deploy_info = Mock(spec=IconScoreDeployInfo)
        next_tx_hash = b'\00\0x' * 16
        deploy_info.configure_mock(next_tx_hash=next_tx_hash)
        IconScoreContextUtil.get_deploy_info.return_value = deploy_info

        with self.assertRaises(InvalidParamsException) as e:
            self._score_deploy_engine._on_deploy(self._context, tx_params)
        self.assertEqual(e.exception.code, ExceptionCode.INVALID_PARAMS)
        self.assertEqual(e.exception.message, f'score is None : {score_address}')
        IconScoreContextUtil.get_deploy_info.assert_called()
        IconScoreContextUtil.is_service_flag_on.assert_called()
        IconScoreContextUtil.try_score_package_validate.assert_not_called()
        self._score_deploy_engine._icon_score_deployer.deploy.assert_called()
        self._score_deploy_engine._initialize_score.assert_not_called()

    # Case when deploy_info is not None, zip, revision2, score validator flag True, SCORE is not None
    @patch_several(GET_DEPLOY_INFO_PATCHER, IS_SERVICE_FLAG_ON_PATCHER, LOAD_SCORE_PATCHER,
                   PUT_SCORE_INFO_PATCHER, TRY_SCORE_PACKAGE_VALIDATE_PATCHER,
                   GET_REVISION_PATCHER)
    def test_on_deploy_case7(self):
        score_address = create_address(1)
        deploy_content = b'deploy_mock_data'
        deploy_data = {"contentType": "application/zip", "content": deploy_content}
        tx_params = Mock(spec=IconScoreDeployTXParams)
        tx_params.configure_mock(score_address=score_address, deploy_data=deploy_data)
        IconScoreContextUtil.is_service_flag_on.return_value = True
        IconScoreContextUtil.get_revision.return_value = 2
        self._score_deploy_engine._icon_score_deployer.deploy = Mock()
        mock_score = MockScore(self)
        mock_score.owner = self._addr1
        IconScoreContextUtil.load_score.return_value = mock_score
        self._score_deploy_engine._initialize_score = Mock()
        deploy_info = Mock(spec=IconScoreDeployInfo)
        next_tx_hash = b'\00\0x' * 16
        deploy_info.configure_mock(next_tx_hash=next_tx_hash)
        IconScoreContextUtil.get_deploy_info.return_value = deploy_info

        self._score_deploy_engine._on_deploy(self._context, tx_params)

        IconScoreContextUtil.load_score.assert_called_with(self._context, score_address, next_tx_hash)
        self._score_deploy_engine._icon_score_deployer.\
            deploy.assert_called_with(address=score_address, data=deploy_content, tx_hash=next_tx_hash)
        self._score_deploy_engine._initialize_score.assert_called()
        IconScoreContextUtil.try_score_package_validate.assert_called_with(self._context, score_address, next_tx_hash)
        IconScoreContextUtil.put_score_info.assert_called_with(self._context, score_address, mock_score, next_tx_hash)

    # Case when deploy_info is not None, zip, revision2, score validator flag True, SCORE is None
    @patch_several(GET_DEPLOY_INFO_PATCHER, IS_SERVICE_FLAG_ON_PATCHER, LOAD_SCORE_PATCHER,
                   PUT_SCORE_INFO_PATCHER, TRY_SCORE_PACKAGE_VALIDATE_PATCHER,
                   GET_REVISION_PATCHER)
    def test_on_deploy_case8(self):
        score_address = create_address(1)
        deploy_content = b'deploy_mock_data'
        deploy_data = {"contentType": "application/zip", "content": deploy_content}
        tx_params = Mock(spec=IconScoreDeployTXParams)
        tx_params.configure_mock(score_address=score_address, deploy_data=deploy_data)
        IconScoreContextUtil.is_service_flag_on.return_value = True
        IconScoreContextUtil.get_revision.return_value = 2
        self._score_deploy_engine._icon_score_deployer.deploy = Mock()
        mock_score = MockScore(self)
        mock_score.owner = self._addr1
        IconScoreContextUtil.load_score.return_value = mock_score
        self._score_deploy_engine._initialize_score = Mock()
        deploy_info = Mock(spec=IconScoreDeployInfo)
        next_tx_hash = b'\00\0x' * 16
        deploy_info.configure_mock(next_tx_hash=next_tx_hash)
        IconScoreContextUtil.get_deploy_info.return_value = deploy_info

        self._score_deploy_engine._on_deploy(self._context, tx_params)

        IconScoreContextUtil.load_score.assert_called_with(self._context, score_address, next_tx_hash)
        self._score_deploy_engine._icon_score_deployer.\
            deploy.assert_called_with(address=score_address, data=deploy_content, tx_hash=next_tx_hash)
        self._score_deploy_engine._initialize_score.assert_called()
        IconScoreContextUtil.try_score_package_validate.assert_called_with(self._context, score_address, next_tx_hash)
        IconScoreContextUtil.put_score_info.assert_called_with(self._context, score_address, mock_score, next_tx_hash)

    # Case when deploy_info is not None, zip, revision3, score validator flag False, SCORE is not None
    @patch_several(GET_DEPLOY_INFO_PATCHER, IS_SERVICE_FLAG_ON_PATCHER, LOAD_SCORE_PATCHER,
                   PUT_SCORE_INFO_PATCHER, TRY_SCORE_PACKAGE_VALIDATE_PATCHER,
                   GET_REVISION_PATCHER, RENAME_DIRECTORY_PATCHER)
    def test_on_deploy_case9(self):
        score_address = create_address(1)
        deploy_content = b'deploy_mock_data'
        deploy_data = {"contentType": "application/zip", "content": deploy_content}
        tx_params = Mock(spec=IconScoreDeployTXParams)
        tx_params.configure_mock(score_address=score_address, deploy_data=deploy_data)
        IconScoreContextUtil.is_service_flag_on.return_value = False
        IconScoreContextUtil.get_revision.return_value = 3
        self._score_deploy_engine._icon_score_deployer.deploy = Mock()
        mock_score = MockScore(self)
        mock_score.owner = self._addr1
        IconScoreContextUtil.load_score.return_value = mock_score
        self._score_deploy_engine._initialize_score = Mock()
        deploy_info = Mock(spec=IconScoreDeployInfo)
        next_tx_hash = b'\00\0x' * 16
        deploy_info.configure_mock(next_tx_hash=next_tx_hash)
        IconScoreContextUtil.get_deploy_info.return_value = deploy_info

        self._score_deploy_engine._on_deploy(self._context, tx_params)

        IconScoreContextUtil.load_score.assert_called_with(self._context, score_address, next_tx_hash)
        self._score_deploy_engine._icon_score_deployer.deploy.\
            assert_called_with(address=score_address, data=deploy_content, tx_hash=next_tx_hash)
        self._score_deploy_engine._initialize_score.assert_called()
        DirectoryNameChanger.rename_directory.assert_called()
        IconScoreContextUtil.try_score_package_validate.assert_not_called()
        IconScoreContextUtil.put_score_info.assert_called_with(self._context, score_address, mock_score, next_tx_hash)

    # Case when deploy_info is not None, zip, revision4, score validator flag False, SCORE is None
    @patch_several(GET_DEPLOY_INFO_PATCHER, IS_SERVICE_FLAG_ON_PATCHER, LOAD_SCORE_PATCHER,
                   PUT_SCORE_INFO_PATCHER, TRY_SCORE_PACKAGE_VALIDATE_PATCHER,
                   GET_REVISION_PATCHER, RENAME_DIRECTORY_PATCHER)
    def test_on_deploy_case10(self):
        score_address = create_address(1)
        deploy_content = b'deploy_mock_data'
        deploy_data = {"contentType": "application/zip", "content": deploy_content}
        tx_params = Mock(spec=IconScoreDeployTXParams)
        tx_params.configure_mock(score_address=score_address, deploy_data=deploy_data)
        IconScoreContextUtil.is_service_flag_on.return_value = False
        IconScoreContextUtil.get_revision.return_value = 4
        self._score_deploy_engine._icon_score_deployer.deploy = Mock()
        IconScoreContextUtil.load_score.return_value = None
        self._score_deploy_engine._initialize_score = Mock()
        deploy_info = Mock(spec=IconScoreDeployInfo)
        next_tx_hash = b'\00\0x' * 16
        deploy_info.configure_mock(next_tx_hash=next_tx_hash)
        IconScoreContextUtil.get_deploy_info.return_value = deploy_info

        with self.assertRaises(InvalidParamsException) as e:
            self._score_deploy_engine._on_deploy(self._context, tx_params)
        self.assertEqual(e.exception.code, ExceptionCode.INVALID_PARAMS)
        self.assertEqual(e.exception.message, f'score is None : {score_address}')
        IconScoreContextUtil.get_deploy_info.assert_called()
        IconScoreContextUtil.is_service_flag_on.assert_called()
        IconScoreContextUtil.try_score_package_validate.assert_not_called()
        self._score_deploy_engine._icon_score_deployer.deploy.assert_called()
        self._score_deploy_engine._initialize_score.assert_not_called()

    # Case when deploy_info is not None, zip, revision4, score validator flag True, SCORE is not None
    @patch_several(GET_DEPLOY_INFO_PATCHER, IS_SERVICE_FLAG_ON_PATCHER, LOAD_SCORE_PATCHER,
                   PUT_SCORE_INFO_PATCHER, TRY_SCORE_PACKAGE_VALIDATE_PATCHER,
                   GET_REVISION_PATCHER, RENAME_DIRECTORY_PATCHER)
    def test_on_deploy_case11(self):
        score_address = create_address(1)
        deploy_content = b'deploy_mock_data'
        deploy_data = {"contentType": "application/zip", "content": deploy_content}
        tx_params = Mock(spec=IconScoreDeployTXParams)
        tx_params.configure_mock(score_address=score_address, deploy_data=deploy_data)
        IconScoreContextUtil.is_service_flag_on.return_value = False
        IconScoreContextUtil.get_revision.return_value = 4
        self._score_deploy_engine._icon_score_deployer.deploy = Mock()
        mock_score = MockScore(self)
        mock_score.owner = self._addr1
        IconScoreContextUtil.load_score.return_value = mock_score
        self._score_deploy_engine._initialize_score = Mock()
        deploy_info = Mock(spec=IconScoreDeployInfo)
        next_tx_hash = b'\00\0x' * 16
        deploy_info.configure_mock(next_tx_hash=next_tx_hash)
        IconScoreContextUtil.get_deploy_info.return_value = deploy_info

        self._score_deploy_engine._on_deploy(self._context, tx_params)

        IconScoreContextUtil.load_score.assert_called_with(self._context, score_address, next_tx_hash)
        self._score_deploy_engine._icon_score_deployer.\
            deploy.assert_called_with(address=score_address, data=deploy_content, tx_hash=next_tx_hash)
        self._score_deploy_engine._initialize_score.assert_called()
        DirectoryNameChanger.rename_directory.assert_called()
        IconScoreContextUtil.try_score_package_validate.assert_not_called()
        IconScoreContextUtil.put_score_info.assert_called_with(self._context, score_address, mock_score, next_tx_hash)

    # Case when deploy_info is not None, zip, revision4, score validator flag True, SCORE None
    @patch_several(GET_DEPLOY_INFO_PATCHER, IS_SERVICE_FLAG_ON_PATCHER, LOAD_SCORE_PATCHER,
                   PUT_SCORE_INFO_PATCHER, TRY_SCORE_PACKAGE_VALIDATE_PATCHER,
                   GET_REVISION_PATCHER, RENAME_DIRECTORY_PATCHER)
    def test_on_deploy_case12(self):
        score_address = create_address(1)
        deploy_content = b'deploy_mock_data'
        deploy_data = {"contentType": "application/zip", "content": deploy_content}
        tx_params = Mock(spec=IconScoreDeployTXParams)
        tx_params.configure_mock(score_address=score_address, deploy_data=deploy_data)
        IconScoreContextUtil.is_service_flag_on.return_value = False
        IconScoreContextUtil.get_revision.return_value = 3
        self._score_deploy_engine._icon_score_deployer.deploy = Mock()
        IconScoreContextUtil.load_score.return_value = None
        self._score_deploy_engine._initialize_score = Mock()
        deploy_info = Mock(spec=IconScoreDeployInfo)
        next_tx_hash = b'\00\0x' * 16
        deploy_info.configure_mock(next_tx_hash=next_tx_hash)
        IconScoreContextUtil.get_deploy_info.return_value = deploy_info

        with self.assertRaises(InvalidParamsException) as e:
            self._score_deploy_engine._on_deploy(self._context, tx_params)
        self.assertEqual(e.exception.code, ExceptionCode.INVALID_PARAMS)
        self.assertEqual(e.exception.message, f'score is None : {score_address}')
        IconScoreContextUtil.get_deploy_info.assert_called()
        IconScoreContextUtil.is_service_flag_on.assert_called()
        IconScoreContextUtil.try_score_package_validate.assert_not_called()
        self._score_deploy_engine._icon_score_deployer.deploy.assert_called()
        self._score_deploy_engine._initialize_score.assert_not_called()

    # Case when deploy_info is not None, tbears, score validator flag False, SCORE is not None
    @patch_several(GET_DEPLOY_INFO_PATCHER, IS_SERVICE_FLAG_ON_PATCHER, LOAD_SCORE_PATCHER,
                   PUT_SCORE_INFO_PATCHER, TRY_SCORE_PACKAGE_VALIDATE_PATCHER,
                   GET_SCORE_ROOT_PATH_PATCHER, SYMLINK_PATCHER)
    def test_on_deploy_case13(self):
        score_address = create_address(1)
        deploy_content = b'deploy_mock_data'
        deploy_data = {"contentType": "application/tbears", "content": deploy_content}
        tx_params = Mock(spec=IconScoreDeployTXParams)
        tx_params.configure_mock(score_address=score_address, deploy_data=deploy_data)
        IconScoreContextUtil.is_service_flag_on.return_value = False
        IconScoreContextUtil.get_score_root_path.return_value = os.path.join(PROJECT_ROOT_PATH, self._ROOT_SCORE_PATH)
        mock_score = MockScore(self)
        mock_score.owner = self._addr1
        IconScoreContextUtil.load_score.return_value = mock_score
        self._score_deploy_engine._initialize_score = Mock()
        self._score_deploy_engine._icon_score_deployer.deploy_legacy = Mock()
        self._score_deploy_engine._icon_score_deployer.deploy = Mock()
        deploy_info = Mock(spec=IconScoreDeployInfo)
        next_tx_hash = b'\00\0x' * 16
        deploy_info.configure_mock(next_tx_hash=next_tx_hash)
        IconScoreContextUtil.get_deploy_info.return_value = deploy_info

        self._score_deploy_engine._on_deploy(self._context, tx_params)

        IconScoreContextUtil.load_score.assert_called_with(self._context, score_address, next_tx_hash)
        self._score_deploy_engine._initialize_score.assert_called()
        self._score_deploy_engine._icon_score_deployer.deploy_legacy.assert_not_called()
        self._score_deploy_engine._icon_score_deployer.deploy.assert_not_called()
        IconScoreContextUtil.try_score_package_validate.assert_not_called()
        IconScoreContextUtil.put_score_info.assert_called_with(self._context, score_address, mock_score, next_tx_hash)

    # Case when deploy_info is not None, tbears, score validator flag False, SCORE is None
    @patch_several(GET_DEPLOY_INFO_PATCHER, IS_SERVICE_FLAG_ON_PATCHER, LOAD_SCORE_PATCHER,
                   PUT_SCORE_INFO_PATCHER, TRY_SCORE_PACKAGE_VALIDATE_PATCHER,
                   GET_SCORE_ROOT_PATH_PATCHER, SYMLINK_PATCHER)
    def test_on_deploy_case14(self):
        score_address = create_address(1)
        deploy_content = b'deploy_mock_data'
        deploy_data = {"contentType": "application/tbears", "content": deploy_content}
        tx_params = Mock(spec=IconScoreDeployTXParams)
        tx_params.configure_mock(score_address=score_address, deploy_data=deploy_data)
        IconScoreContextUtil.is_service_flag_on.return_value = False
        IconScoreContextUtil.get_score_root_path.return_value = os.path.join(PROJECT_ROOT_PATH, self._ROOT_SCORE_PATH)
        IconScoreContextUtil.load_score.return_value = None
        self._score_deploy_engine._icon_score_deployer.deploy_legacy = Mock()
        self._score_deploy_engine._icon_score_deployer.deploy = Mock()
        self._score_deploy_engine._initialize_score = Mock()
        deploy_info = Mock(spec=IconScoreDeployInfo)
        next_tx_hash = b'\00\0x' * 16
        deploy_info.configure_mock(next_tx_hash=next_tx_hash)
        IconScoreContextUtil.get_deploy_info.return_value = deploy_info

        with self.assertRaises(InvalidParamsException) as e:
            self._score_deploy_engine._on_deploy(self._context, tx_params)
        self.assertEqual(e.exception.code, ExceptionCode.INVALID_PARAMS)
        self.assertEqual(e.exception.message, f'score is None : {score_address}')
        IconScoreContextUtil.get_deploy_info.assert_called()
        IconScoreContextUtil.is_service_flag_on.assert_called()
        IconScoreContextUtil.try_score_package_validate.assert_not_called()
        self._score_deploy_engine._icon_score_deployer.deploy_legacy.assert_not_called()
        self._score_deploy_engine._icon_score_deployer.deploy.assert_not_called()
        self._score_deploy_engine._initialize_score.assert_not_called()

    # Case when deploy_info is not None, tbears, score validator flag True, SCORE is not None
    @patch_several(GET_DEPLOY_INFO_PATCHER, IS_SERVICE_FLAG_ON_PATCHER, LOAD_SCORE_PATCHER,
                   PUT_SCORE_INFO_PATCHER, TRY_SCORE_PACKAGE_VALIDATE_PATCHER,
                   GET_SCORE_ROOT_PATH_PATCHER, SYMLINK_PATCHER)
    def test_on_deploy_case15(self):
        score_address = create_address(1)
        deploy_content = b'deploy_mock_data'
        deploy_data = {"contentType": "application/tbears", "content": deploy_content}
        tx_params = Mock(spec=IconScoreDeployTXParams)
        tx_params.configure_mock(score_address=score_address, deploy_data=deploy_data)
        IconScoreContextUtil.is_service_flag_on.return_value = True
        IconScoreContextUtil.get_score_root_path.return_value = os.path.join(PROJECT_ROOT_PATH, self._ROOT_SCORE_PATH)
        mock_score = MockScore(self)
        mock_score.owner = self._addr1
        IconScoreContextUtil.load_score.return_value = mock_score
        self._score_deploy_engine._initialize_score = Mock()
        deploy_info = Mock(spec=IconScoreDeployInfo)
        next_tx_hash = b'\00\0x' * 16
        deploy_info.configure_mock(next_tx_hash=next_tx_hash)
        IconScoreContextUtil.get_deploy_info.return_value = deploy_info

        self._score_deploy_engine._on_deploy(self._context, tx_params)

        IconScoreContextUtil.load_score.assert_called_with(self._context, score_address, next_tx_hash)
        self._score_deploy_engine._initialize_score.assert_called()
        IconScoreContextUtil.try_score_package_validate.assert_called_with(self._context, score_address, next_tx_hash)
        IconScoreContextUtil.put_score_info.assert_called_with(self._context, score_address, mock_score, next_tx_hash)

    # Case when deploy_info is not None, tbears, score validator flag True, SCORE is None
    @patch_several(GET_DEPLOY_INFO_PATCHER, IS_SERVICE_FLAG_ON_PATCHER, LOAD_SCORE_PATCHER,
                   PUT_SCORE_INFO_PATCHER, TRY_SCORE_PACKAGE_VALIDATE_PATCHER,
                   GET_SCORE_ROOT_PATH_PATCHER, SYMLINK_PATCHER)
    def test_on_deploy_case16(self):
        score_address = create_address(1)
        deploy_content = b'deploy_mock_data'
        deploy_data = {"contentType": "application/tbears", "content": deploy_content}
        tx_params = Mock(spec=IconScoreDeployTXParams)
        tx_params.configure_mock(score_address=score_address, deploy_data=deploy_data)
        IconScoreContextUtil.is_service_flag_on.return_value = True
        IconScoreContextUtil.get_score_root_path.return_value = os.path.join(PROJECT_ROOT_PATH, self._ROOT_SCORE_PATH)
        IconScoreContextUtil.load_score.return_value = None
        self._score_deploy_engine._icon_score_deployer.deploy_legacy = Mock()
        self._score_deploy_engine._icon_score_deployer.deploy = Mock()
        self._score_deploy_engine._initialize_score = Mock()
        deploy_info = Mock(spec=IconScoreDeployInfo)
        next_tx_hash = b'\00\0x' * 16
        deploy_info.configure_mock(next_tx_hash=next_tx_hash)
        IconScoreContextUtil.get_deploy_info.return_value = deploy_info

        with self.assertRaises(InvalidParamsException) as e:
            self._score_deploy_engine._on_deploy(self._context, tx_params)
        self.assertEqual(e.exception.code, ExceptionCode.INVALID_PARAMS)
        self.assertEqual(e.exception.message, f'score is None : {score_address}')
        IconScoreContextUtil.get_deploy_info.assert_called()
        IconScoreContextUtil.is_service_flag_on.assert_called()
        self._score_deploy_engine._icon_score_deployer.deploy_legacy.assert_not_called()
        self._score_deploy_engine._icon_score_deployer.deploy.assert_not_called()
        self._score_deploy_engine._initialize_score.assert_not_called()

    # Case when deploy_info is None, zip, revision0, score validator flag False, SCORE is not None
    @patch_several(GET_DEPLOY_INFO_PATCHER, IS_SERVICE_FLAG_ON_PATCHER, LOAD_SCORE_PATCHER,
                   PUT_SCORE_INFO_PATCHER, TRY_SCORE_PACKAGE_VALIDATE_PATCHER)
    def test_on_deploy_case17(self):
        score_address = create_address(1)
        deploy_content = b'deploy_mock_data'
        deploy_data = {"contentType": "application/zip", "content": deploy_content}
        tx_params = Mock(spec=IconScoreDeployTXParams)
        tx_params.configure_mock(score_address=score_address, deploy_data=deploy_data)
        IconScoreContextUtil.get_deploy_info.return_value = None
        IconScoreContextUtil.is_service_flag_on.return_value = False
        self._score_deploy_engine._icon_score_deployer.deploy_legacy = Mock()
        mock_score = MockScore(self)
        mock_score.owner = self._addr1
        IconScoreContextUtil.load_score.return_value = mock_score
        self._score_deploy_engine._initialize_score = Mock()
        default_byte_value = bytes(DEFAULT_BYTE_SIZE)

        self._score_deploy_engine._on_deploy(self._context, tx_params)

        IconScoreContextUtil.load_score.assert_called_with(self._context, score_address, default_byte_value)
        self._score_deploy_engine._icon_score_deployer. \
            deploy_legacy.assert_called_with(address=score_address, data=deploy_content, tx_hash=default_byte_value)
        self._score_deploy_engine._initialize_score.assert_called()
        IconScoreContextUtil.try_score_package_validate.assert_not_called()
        IconScoreContextUtil.put_score_info.assert_called_with(self._context,
                                                               score_address, mock_score, default_byte_value)

    # Case when deploy_info is None, zip, revision0, score validator flag False, SCORE is None
    @patch_several(GET_DEPLOY_INFO_PATCHER, IS_SERVICE_FLAG_ON_PATCHER, LOAD_SCORE_PATCHER,
                   PUT_SCORE_INFO_PATCHER)
    def test_on_deploy_case18(self):
        score_address = create_address(1)
        deploy_content = b'deploy_mock_data'
        deploy_data = {"contentType": "application/zip", "content": deploy_content}
        tx_params = Mock(spec=IconScoreDeployTXParams)
        tx_params.configure_mock(score_address=score_address, deploy_data=deploy_data)
        IconScoreContextUtil.get_deploy_info.return_value = None
        IconScoreContextUtil.is_service_flag_on.return_value = False
        self._score_deploy_engine._icon_score_deployer.deploy_legacy = Mock()
        self._score_deploy_engine._icon_score_deployer.deploy = Mock()
        self._score_deploy_engine._icon_score_deployer.deploy_legacy = Mock()
        IconScoreContextUtil.load_score.return_value = None
        self._score_deploy_engine._initialize_score = Mock()

        with self.assertRaises(InvalidParamsException) as e:
            self._score_deploy_engine._on_deploy(self._context, tx_params)
        self.assertEqual(e.exception.code, ExceptionCode.INVALID_PARAMS)
        self.assertEqual(e.exception.message, f'score is None : {score_address}')
        self._score_deploy_engine._icon_score_deployer.deploy_legacy.assert_called()
        self._score_deploy_engine._icon_score_deployer.deploy.assert_not_called()
        self._score_deploy_engine._initialize_score.assert_not_called()

    # Case when deploy_info is None, zip, revision0, score validator flag True, SCORE is not None
    @patch_several(GET_DEPLOY_INFO_PATCHER, IS_SERVICE_FLAG_ON_PATCHER, LOAD_SCORE_PATCHER,
                   PUT_SCORE_INFO_PATCHER, TRY_SCORE_PACKAGE_VALIDATE_PATCHER)
    def test_on_deploy_case19(self):
        score_address = create_address(1)
        deploy_content = b'deploy_mock_data'
        deploy_data = {"contentType": "application/zip", "content": deploy_content}
        tx_params = Mock(spec=IconScoreDeployTXParams)
        tx_params.configure_mock(score_address=score_address, deploy_data=deploy_data)
        IconScoreContextUtil.get_deploy_info.return_value = None
        IconScoreContextUtil.is_service_flag_on.return_value = True
        self._score_deploy_engine._icon_score_deployer.deploy_legacy = Mock()
        mock_score = MockScore(self)
        mock_score.owner = self._addr1
        IconScoreContextUtil.load_score.return_value = mock_score
        self._score_deploy_engine._initialize_score = Mock()
        default_byte_value = bytes(DEFAULT_BYTE_SIZE)

        self._score_deploy_engine._on_deploy(self._context, tx_params)

        IconScoreContextUtil.load_score.assert_called_with(self._context, score_address, default_byte_value)
        self._score_deploy_engine._initialize_score.assert_called()
        IconScoreContextUtil.try_score_package_validate.\
            assert_called_with(self._context, score_address, default_byte_value)
        self._score_deploy_engine._icon_score_deployer.\
            deploy_legacy.assert_called_with(address=score_address, data=deploy_content, tx_hash=default_byte_value)
        IconScoreContextUtil.put_score_info.assert_called_with(self._context, score_address,
                                                               mock_score, default_byte_value)

    # Case when deploy_info is None, zip, revision0, score validator flag True, SCORE is None
    @patch_several(GET_DEPLOY_INFO_PATCHER, IS_SERVICE_FLAG_ON_PATCHER, LOAD_SCORE_PATCHER,
                   PUT_SCORE_INFO_PATCHER, TRY_SCORE_PACKAGE_VALIDATE_PATCHER)
    def test_on_deploy_case20(self):
        score_address = create_address(1)
        deploy_content = b'deploy_mock_data'
        deploy_data = {"contentType": "application/zip", "content": deploy_content}
        tx_params = Mock(spec=IconScoreDeployTXParams)
        tx_params.configure_mock(score_address=score_address, deploy_data=deploy_data)
        IconScoreContextUtil.get_deploy_info.return_value = None
        IconScoreContextUtil.is_service_flag_on.return_value = False
        IconScoreContextUtil.load_score.return_value = None
        self._score_deploy_engine._icon_score_deployer.deploy_legacy = Mock()
        self._score_deploy_engine._initialize_score = Mock()

        with self.assertRaises(InvalidParamsException) as e:
            self._score_deploy_engine._on_deploy(self._context, tx_params)
        self.assertEqual(e.exception.code, ExceptionCode.INVALID_PARAMS)
        self.assertEqual(e.exception.message, f'score is None : {score_address}')
        IconScoreContextUtil.get_deploy_info.assert_called()
        IconScoreContextUtil.is_service_flag_on.assert_called()
        IconScoreContextUtil.try_score_package_validate.assert_not_called()
        self._score_deploy_engine._icon_score_deployer.deploy_legacy.assert_called()
        self._score_deploy_engine._initialize_score.assert_not_called()

    # Case when deploy_info is None, zip, revision2, score validator flag False, SCORE is not None
    @patch_several(GET_DEPLOY_INFO_PATCHER, IS_SERVICE_FLAG_ON_PATCHER, LOAD_SCORE_PATCHER,
                   PUT_SCORE_INFO_PATCHER, TRY_SCORE_PACKAGE_VALIDATE_PATCHER,
                   GET_REVISION_PATCHER)
    def test_on_deploy_case21(self):
        score_address = create_address(1)
        deploy_content = b'deploy_mock_data'
        deploy_data = {"contentType": "application/zip", "content": deploy_content}
        tx_params = Mock(spec=IconScoreDeployTXParams)
        tx_params.configure_mock(score_address=score_address, deploy_data=deploy_data)
        IconScoreContextUtil.get_deploy_info.return_value = None
        IconScoreContextUtil.is_service_flag_on.return_value = False
        IconScoreContextUtil.get_revision.return_value = 2
        self._score_deploy_engine._icon_score_deployer.deploy = Mock()
        mock_score = MockScore(self)
        mock_score.owner = self._addr1
        IconScoreContextUtil.load_score.return_value = mock_score
        self._score_deploy_engine._initialize_score = Mock()
        default_byte_value = bytes(DEFAULT_BYTE_SIZE)

        self._score_deploy_engine._on_deploy(self._context, tx_params)

        IconScoreContextUtil.load_score.assert_called_with(self._context, score_address, default_byte_value)
        self._score_deploy_engine._icon_score_deployer. \
            deploy.assert_called_with(address=score_address, data=deploy_content, tx_hash=default_byte_value)
        self._score_deploy_engine._initialize_score.assert_called()
        IconScoreContextUtil.try_score_package_validate.assert_not_called()
        IconScoreContextUtil.put_score_info.assert_called_with(self._context,
                                                               score_address, mock_score, default_byte_value)

    # Case when deploy_info is None, zip, revision2, score validator flag False, SCORE is None
    @patch_several(GET_DEPLOY_INFO_PATCHER, IS_SERVICE_FLAG_ON_PATCHER, LOAD_SCORE_PATCHER,
                   PUT_SCORE_INFO_PATCHER, TRY_SCORE_PACKAGE_VALIDATE_PATCHER,
                   GET_REVISION_PATCHER)
    def test_on_deploy_case22(self):
        score_address = create_address(1)
        deploy_content = b'deploy_mock_data'
        deploy_data = {"contentType": "application/zip", "content": deploy_content}
        tx_params = Mock(spec=IconScoreDeployTXParams)
        tx_params.configure_mock(score_address=score_address, deploy_data=deploy_data)
        IconScoreContextUtil.get_deploy_info.return_value = None
        IconScoreContextUtil.is_service_flag_on.return_value = False
        IconScoreContextUtil.get_revision.return_value = 2
        self._score_deploy_engine._icon_score_deployer.deploy = Mock()
        IconScoreContextUtil.load_score.return_value = None
        self._score_deploy_engine._initialize_score = Mock()
        IconScoreContextUtil.get_deploy_info.return_value = None

        with self.assertRaises(InvalidParamsException) as e:
            self._score_deploy_engine._on_deploy(self._context, tx_params)
        self.assertEqual(e.exception.code, ExceptionCode.INVALID_PARAMS)
        self.assertEqual(e.exception.message, f'score is None : {score_address}')
        IconScoreContextUtil.get_deploy_info.assert_called()
        IconScoreContextUtil.is_service_flag_on.assert_called()
        IconScoreContextUtil.try_score_package_validate.assert_not_called()
        self._score_deploy_engine._icon_score_deployer.deploy.assert_called()
        self._score_deploy_engine._initialize_score.assert_not_called()

    # Case when deploy_info is None, zip, revision2, score validator flag True, SCORE is not None
    @patch_several(GET_DEPLOY_INFO_PATCHER, IS_SERVICE_FLAG_ON_PATCHER, LOAD_SCORE_PATCHER,
                   PUT_SCORE_INFO_PATCHER, TRY_SCORE_PACKAGE_VALIDATE_PATCHER,
                   GET_REVISION_PATCHER)
    def test_on_deploy_case23(self):
        score_address = create_address(1)
        deploy_content = b'deploy_mock_data'
        deploy_data = {"contentType": "application/zip", "content": deploy_content}
        tx_params = Mock(spec=IconScoreDeployTXParams)
        tx_params.configure_mock(score_address=score_address, deploy_data=deploy_data)
        IconScoreContextUtil.get_deploy_info.return_value = None
        IconScoreContextUtil.is_service_flag_on.return_value = True
        IconScoreContextUtil.get_revision.return_value = 2
        self._score_deploy_engine._icon_score_deployer.deploy = Mock()
        mock_score = MockScore(self)
        mock_score.owner = self._addr1
        IconScoreContextUtil.load_score.return_value = mock_score
        default_byte_value = bytes(DEFAULT_BYTE_SIZE)
        self._score_deploy_engine._initialize_score = Mock()

        self._score_deploy_engine._on_deploy(self._context, tx_params)

        IconScoreContextUtil.load_score.assert_called_with(self._context, score_address, default_byte_value)
        self._score_deploy_engine._icon_score_deployer.\
            deploy.assert_called_with(address=score_address, data=deploy_content, tx_hash=default_byte_value)
        self._score_deploy_engine._initialize_score.assert_called()
        IconScoreContextUtil.try_score_package_validate.\
            assert_called_with(self._context, score_address, default_byte_value)
        IconScoreContextUtil.put_score_info.assert_called_with\
            (self._context, score_address, mock_score, default_byte_value)

    # Case when deploy_info is None, zip, revision2, score validator flag True, SCORE is None
    @patch_several(GET_DEPLOY_INFO_PATCHER, IS_SERVICE_FLAG_ON_PATCHER, LOAD_SCORE_PATCHER,
                   PUT_SCORE_INFO_PATCHER, TRY_SCORE_PACKAGE_VALIDATE_PATCHER,
                   GET_REVISION_PATCHER)
    def test_on_deploy_case24(self):
        score_address = create_address(1)
        deploy_content = b'deploy_mock_data'
        deploy_data = {"contentType": "application/zip", "content": deploy_content}
        tx_params = Mock(spec=IconScoreDeployTXParams)
        tx_params.configure_mock(score_address=score_address, deploy_data=deploy_data)
        IconScoreContextUtil.get_deploy_info.return_value = None
        IconScoreContextUtil.is_service_flag_on.return_value = True
        IconScoreContextUtil.get_revision.return_value = 2
        self._score_deploy_engine._icon_score_deployer.deploy = Mock()
        mock_score = MockScore(self)
        mock_score.owner = self._addr1
        IconScoreContextUtil.load_score.return_value = mock_score
        self._score_deploy_engine._initialize_score = Mock()
        default_byte_value = bytes(DEFAULT_BYTE_SIZE)

        self._score_deploy_engine._on_deploy(self._context, tx_params)

        IconScoreContextUtil.load_score.assert_called_with(self._context, score_address, default_byte_value)
        self._score_deploy_engine._icon_score_deployer. \
            deploy.assert_called_with(address=score_address, data=deploy_content, tx_hash=default_byte_value)
        self._score_deploy_engine._initialize_score.assert_called()
        IconScoreContextUtil.try_score_package_validate.assert_called_with\
            (self._context, score_address, default_byte_value)
        IconScoreContextUtil.put_score_info.assert_called_with\
            (self._context, score_address, mock_score, default_byte_value)

    # Case when deploy_info is None, zip, revision3, score validator flag False, SCORE is not None
    @patch_several(GET_DEPLOY_INFO_PATCHER, IS_SERVICE_FLAG_ON_PATCHER, LOAD_SCORE_PATCHER,
                   PUT_SCORE_INFO_PATCHER, TRY_SCORE_PACKAGE_VALIDATE_PATCHER,
                   GET_REVISION_PATCHER, RENAME_DIRECTORY_PATCHER)
    def test_on_deploy_case25(self):
        score_address = create_address(1)
        deploy_content = b'deploy_mock_data'
        deploy_data = {"contentType": "application/zip", "content": deploy_content}
        tx_params = Mock(spec=IconScoreDeployTXParams)
        tx_params.configure_mock(score_address=score_address, deploy_data=deploy_data)
        IconScoreContextUtil.get_deploy_info.return_value = None
        IconScoreContextUtil.is_service_flag_on.return_value = False
        IconScoreContextUtil.get_revision.return_value = 3
        self._score_deploy_engine._icon_score_deployer.deploy = Mock()
        mock_score = MockScore(self)
        mock_score.owner = self._addr1
        IconScoreContextUtil.load_score.return_value = mock_score
        self._score_deploy_engine._initialize_score = Mock()
        default_byte_value = bytes(DEFAULT_BYTE_SIZE)

        self._score_deploy_engine._on_deploy(self._context, tx_params)

        IconScoreContextUtil.load_score.assert_called_with(self._context, score_address, default_byte_value)
        self._score_deploy_engine._icon_score_deployer.deploy. \
            assert_called_with(address=score_address, data=deploy_content, tx_hash=default_byte_value)
        self._score_deploy_engine._initialize_score.assert_called()
        DirectoryNameChanger.rename_directory.assert_called()
        IconScoreContextUtil.try_score_package_validate.assert_not_called()
        IconScoreContextUtil.put_score_info.assert_called_with\
            (self._context, score_address, mock_score, default_byte_value)

    # Case when deploy_info is None, zip, revision4, score validator flag False, SCORE is None
    @patch_several(GET_DEPLOY_INFO_PATCHER, IS_SERVICE_FLAG_ON_PATCHER, LOAD_SCORE_PATCHER,
                   PUT_SCORE_INFO_PATCHER, TRY_SCORE_PACKAGE_VALIDATE_PATCHER,
                   GET_REVISION_PATCHER, RENAME_DIRECTORY_PATCHER)
    def test_on_deploy_case26(self):
        score_address = create_address(1)
        deploy_content = b'deploy_mock_data'
        deploy_data = {"contentType": "application/zip", "content": deploy_content}
        tx_params = Mock(spec=IconScoreDeployTXParams)
        tx_params.configure_mock(score_address=score_address, deploy_data=deploy_data)
        IconScoreContextUtil.get_deploy_info.return_value = None
        IconScoreContextUtil.is_service_flag_on.return_value = False
        IconScoreContextUtil.get_revision.return_value = 4
        self._score_deploy_engine._icon_score_deployer.deploy = Mock()
        IconScoreContextUtil.load_score.return_value = None
        self._score_deploy_engine._initialize_score = Mock()
        IconScoreContextUtil.get_deploy_info.return_value = None

        with self.assertRaises(InvalidParamsException) as e:
            self._score_deploy_engine._on_deploy(self._context, tx_params)
        self.assertEqual(e.exception.code, ExceptionCode.INVALID_PARAMS)
        self.assertEqual(e.exception.message, f'score is None : {score_address}')
        IconScoreContextUtil.get_deploy_info.assert_called()
        IconScoreContextUtil.is_service_flag_on.assert_called()
        IconScoreContextUtil.try_score_package_validate.assert_not_called()
        self._score_deploy_engine._icon_score_deployer.deploy.assert_called()
        self._score_deploy_engine._initialize_score.assert_not_called()

    # Case when deploy_info is None, zip, revision4, score validator flag True, SCORE is not None
    @patch_several(GET_DEPLOY_INFO_PATCHER, IS_SERVICE_FLAG_ON_PATCHER, LOAD_SCORE_PATCHER,
                   PUT_SCORE_INFO_PATCHER, TRY_SCORE_PACKAGE_VALIDATE_PATCHER,
                   GET_REVISION_PATCHER, RENAME_DIRECTORY_PATCHER)
    def test_on_deploy_case27(self):
        score_address = create_address(1)
        deploy_content = b'deploy_mock_data'
        deploy_data = {"contentType": "application/zip", "content": deploy_content}
        tx_params = Mock(spec=IconScoreDeployTXParams)
        tx_params.configure_mock(score_address=score_address, deploy_data=deploy_data)
        IconScoreContextUtil.get_deploy_info.return_value = None
        IconScoreContextUtil.is_service_flag_on.return_value = False
        IconScoreContextUtil.get_revision.return_value = 4
        self._score_deploy_engine._icon_score_deployer.deploy = Mock()
        mock_score = MockScore(self)
        mock_score.owner = self._addr1
        IconScoreContextUtil.load_score.return_value = mock_score
        self._score_deploy_engine._initialize_score = Mock()
        default_byte_value = bytes(DEFAULT_BYTE_SIZE)
        IconScoreContextUtil.get_deploy_info.return_value = None

        self._score_deploy_engine._on_deploy(self._context, tx_params)

        IconScoreContextUtil.load_score.assert_called_with\
            (self._context, score_address, default_byte_value)
        self._score_deploy_engine._icon_score_deployer. \
            deploy.assert_called_with(address=score_address, data=deploy_content, tx_hash=default_byte_value)
        self._score_deploy_engine._initialize_score.assert_called()
        DirectoryNameChanger.rename_directory.assert_called()
        IconScoreContextUtil.try_score_package_validate.assert_not_called()
        IconScoreContextUtil.put_score_info.assert_called_with\
            (self._context, score_address, mock_score, default_byte_value)

    # Case when deploy_info is None, zip, revision4, score validator flag True, SCORE None
    @patch_several(GET_DEPLOY_INFO_PATCHER, IS_SERVICE_FLAG_ON_PATCHER, LOAD_SCORE_PATCHER,
                   PUT_SCORE_INFO_PATCHER, TRY_SCORE_PACKAGE_VALIDATE_PATCHER,
                   GET_REVISION_PATCHER, RENAME_DIRECTORY_PATCHER)
    def test_on_deploy_case28(self):
        score_address = create_address(1)
        deploy_content = b'deploy_mock_data'
        deploy_data = {"contentType": "application/zip", "content": deploy_content}
        tx_params = Mock(spec=IconScoreDeployTXParams)
        tx_params.configure_mock(score_address=score_address, deploy_data=deploy_data)
        IconScoreContextUtil.get_deploy_info.return_value = None
        IconScoreContextUtil.is_service_flag_on.return_value = False
        IconScoreContextUtil.get_revision.return_value = 3
        self._score_deploy_engine._icon_score_deployer.deploy = Mock()
        IconScoreContextUtil.load_score.return_value = None
        self._score_deploy_engine._initialize_score = Mock()
        IconScoreContextUtil.get_deploy_info.return_value = None

        with self.assertRaises(InvalidParamsException) as e:
            self._score_deploy_engine._on_deploy(self._context, tx_params)
        self.assertEqual(e.exception.code, ExceptionCode.INVALID_PARAMS)
        self.assertEqual(e.exception.message, f'score is None : {score_address}')
        IconScoreContextUtil.get_deploy_info.assert_called()
        IconScoreContextUtil.is_service_flag_on.assert_called()
        IconScoreContextUtil.try_score_package_validate.assert_not_called()
        self._score_deploy_engine._icon_score_deployer.deploy.assert_called()
        self._score_deploy_engine._initialize_score.assert_not_called()

    # Case when deploy_info is None, tbears, score validator flag False, SCORE is not None
    @patch_several(GET_DEPLOY_INFO_PATCHER, IS_SERVICE_FLAG_ON_PATCHER, LOAD_SCORE_PATCHER,
                   PUT_SCORE_INFO_PATCHER, TRY_SCORE_PACKAGE_VALIDATE_PATCHER,
                   GET_SCORE_ROOT_PATH_PATCHER, SYMLINK_PATCHER)
    def test_on_deploy_case29(self):
        score_address = create_address(1)
        deploy_content = b'deploy_mock_data'
        deploy_data = {"contentType": "application/tbears", "content": deploy_content}
        tx_params = Mock(spec=IconScoreDeployTXParams)
        tx_params.configure_mock(score_address=score_address, deploy_data=deploy_data)
        IconScoreContextUtil.get_deploy_info.return_value = None
        IconScoreContextUtil.is_service_flag_on.return_value = False
        IconScoreContextUtil.get_score_root_path.return_value = os.path.join(PROJECT_ROOT_PATH, self._ROOT_SCORE_PATH)
        mock_score = MockScore(self)
        mock_score.owner = self._addr1
        IconScoreContextUtil.load_score.return_value = mock_score
        self._score_deploy_engine._initialize_score = Mock()
        default_byte_value = bytes(DEFAULT_BYTE_SIZE)
        IconScoreContextUtil.get_deploy_info.return_value = None

        self._score_deploy_engine._on_deploy(self._context, tx_params)

        IconScoreContextUtil.load_score.assert_called_with(self._context, score_address, default_byte_value)
        self._score_deploy_engine._initialize_score.assert_called()
        IconScoreContextUtil.try_score_package_validate.assert_not_called()
        IconScoreContextUtil.put_score_info.assert_called_with\
            (self._context, score_address, mock_score, default_byte_value)

    # Case when deploy_info is None, tbears, score validator flag False, SCORE is None
    @patch_several(GET_DEPLOY_INFO_PATCHER, IS_SERVICE_FLAG_ON_PATCHER, LOAD_SCORE_PATCHER,
                   PUT_SCORE_INFO_PATCHER, TRY_SCORE_PACKAGE_VALIDATE_PATCHER,
                   GET_SCORE_ROOT_PATH_PATCHER, SYMLINK_PATCHER)
    def test_on_deploy_case30(self):
        score_address = create_address(1)
        deploy_content = b'deploy_mock_data'
        deploy_data = {"contentType": "application/tbears", "content": deploy_content}
        tx_params = Mock(spec=IconScoreDeployTXParams)
        tx_params.configure_mock(score_address=score_address, deploy_data=deploy_data)
        IconScoreContextUtil.get_deploy_info.return_value = None
        IconScoreContextUtil.is_service_flag_on.return_value = False
        IconScoreContextUtil.get_score_root_path.return_value = os.path.join(PROJECT_ROOT_PATH, self._ROOT_SCORE_PATH)
        IconScoreContextUtil.load_score.return_value = None
        self._score_deploy_engine._initialize_score = Mock()
        IconScoreContextUtil.get_deploy_info.return_value = None

        with self.assertRaises(InvalidParamsException) as e:
            self._score_deploy_engine._on_deploy(self._context, tx_params)
        self.assertEqual(e.exception.code, ExceptionCode.INVALID_PARAMS)
        self.assertEqual(e.exception.message, f'score is None : {score_address}')
        IconScoreContextUtil.get_deploy_info.assert_called()
        IconScoreContextUtil.is_service_flag_on.assert_called()
        IconScoreContextUtil.try_score_package_validate.assert_not_called()
        self._score_deploy_engine._initialize_score.assert_not_called()

    # Case when deploy_info is None, tbears, score validator flag True, SCORE is not None
    @patch_several(GET_DEPLOY_INFO_PATCHER, IS_SERVICE_FLAG_ON_PATCHER, LOAD_SCORE_PATCHER,
                   PUT_SCORE_INFO_PATCHER, TRY_SCORE_PACKAGE_VALIDATE_PATCHER,
                   GET_SCORE_ROOT_PATH_PATCHER, SYMLINK_PATCHER)
    def test_on_deploy_case31(self):
        score_address = create_address(1)
        deploy_content = b'deploy_mock_data'
        deploy_data = {"contentType": "application/tbears", "content": deploy_content}
        tx_params = Mock(spec=IconScoreDeployTXParams)
        tx_params.configure_mock(score_address=score_address, deploy_data=deploy_data)
        IconScoreContextUtil.get_deploy_info.return_value = None
        IconScoreContextUtil.is_service_flag_on.return_value = True
        IconScoreContextUtil.get_score_root_path.return_value = os.path.join(PROJECT_ROOT_PATH, self._ROOT_SCORE_PATH)
        mock_score = MockScore(self)
        mock_score.owner = self._addr1
        IconScoreContextUtil.load_score.return_value = mock_score
        self._score_deploy_engine._initialize_score = Mock()
        default_byte_value = bytes(DEFAULT_BYTE_SIZE)
        IconScoreContextUtil.get_deploy_info.return_value = None

        self._score_deploy_engine._on_deploy(self._context, tx_params)

        IconScoreContextUtil.load_score.assert_called_with(self._context, score_address, default_byte_value)
        self._score_deploy_engine._initialize_score.assert_called()
        IconScoreContextUtil.try_score_package_validate.assert_called_with\
            (self._context, score_address, default_byte_value)
        IconScoreContextUtil.put_score_info.assert_called_with\
            (self._context, score_address, mock_score, default_byte_value)

    # Case when deploy_info is not None, tbears, score validator flag True, SCORE is None
    @patch_several(GET_DEPLOY_INFO_PATCHER, IS_SERVICE_FLAG_ON_PATCHER, LOAD_SCORE_PATCHER,
                   PUT_SCORE_INFO_PATCHER, TRY_SCORE_PACKAGE_VALIDATE_PATCHER,
                   GET_SCORE_ROOT_PATH_PATCHER, SYMLINK_PATCHER)
    def test_on_deploy_case32(self):
        score_address = create_address(1)
        deploy_content = b'deploy_mock_data'
        deploy_data = {"contentType": "application/tbears", "content": deploy_content}
        tx_params = Mock(spec=IconScoreDeployTXParams)
        tx_params.configure_mock(score_address=score_address, deploy_data=deploy_data)
        IconScoreContextUtil.get_deploy_info.return_value = None
        IconScoreContextUtil.is_service_flag_on.return_value = True
        IconScoreContextUtil.get_score_root_path.return_value = os.path.join(PROJECT_ROOT_PATH, self._ROOT_SCORE_PATH)
        IconScoreContextUtil.load_score.return_value = None
        self._score_deploy_engine._initialize_score = Mock()
        IconScoreContextUtil.get_deploy_info.return_value = None

        with self.assertRaises(InvalidParamsException) as e:
            self._score_deploy_engine._on_deploy(self._context, tx_params)
        self.assertEqual(e.exception.code, ExceptionCode.INVALID_PARAMS)
        self.assertEqual(e.exception.message, f'score is None : {score_address}')
        IconScoreContextUtil.get_deploy_info.assert_called()
        IconScoreContextUtil.is_service_flag_on.assert_called()
        self._score_deploy_engine._initialize_score.assert_not_called()

    # Case when deploy_info is not None, next_tx_hash is None,
    # zip, revision0, score validator flag False, SCORE is not None
    @patch_several(GET_DEPLOY_INFO_PATCHER, IS_SERVICE_FLAG_ON_PATCHER, LOAD_SCORE_PATCHER,
                   PUT_SCORE_INFO_PATCHER, TRY_SCORE_PACKAGE_VALIDATE_PATCHER)
    def test_on_deploy_case33(self):
        score_address = create_address(1)
        deploy_content = b'deploy_mock_data'
        deploy_data = {"contentType": "application/zip", "content": deploy_content}
        tx_params = Mock(spec=IconScoreDeployTXParams)
        tx_params.configure_mock(score_address=score_address, deploy_data=deploy_data)
        IconScoreContextUtil.get_deploy_info.return_value = None
        IconScoreContextUtil.is_service_flag_on.return_value = False
        self._score_deploy_engine._icon_score_deployer.deploy_legacy = Mock()
        mock_score = MockScore(self)
        mock_score.owner = self._addr1
        IconScoreContextUtil.load_score.return_value = mock_score
        self._score_deploy_engine._initialize_score = Mock()
        deploy_info = Mock(spec=IconScoreDeployInfo)
        default_byte_value = bytes(DEFAULT_BYTE_SIZE)
        deploy_info.configure_mock(next_tx_hash=None)
        IconScoreContextUtil.get_deploy_info.return_value = deploy_info

        self._score_deploy_engine._on_deploy(self._context, tx_params)

        IconScoreContextUtil.load_score.assert_called_with(self._context, score_address, default_byte_value)
        self._score_deploy_engine._icon_score_deployer.\
            deploy_legacy.assert_called_with(address=score_address, data=deploy_content, tx_hash=default_byte_value)
        self._score_deploy_engine._initialize_score.assert_called()
        IconScoreContextUtil.try_score_package_validate.assert_not_called()
        IconScoreContextUtil.put_score_info.assert_called_with\
            (self._context, score_address, mock_score, default_byte_value)

    # Case when deploy_info is not None, next_tx_hash is None,
    # zip, revision0, score validator flag False, SCORE is not None
    @patch_several(GET_DEPLOY_INFO_PATCHER, IS_SERVICE_FLAG_ON_PATCHER, LOAD_SCORE_PATCHER,
                   PUT_SCORE_INFO_PATCHER, TRY_SCORE_PACKAGE_VALIDATE_PATCHER)
    def test_on_deploy_case34(self):
        score_address = create_address(1)
        deploy_content = b'deploy_mock_data'
        deploy_data = {"contentType": "application/zip", "content": deploy_content}
        tx_params = Mock(spec=IconScoreDeployTXParams)
        tx_params.configure_mock(score_address=score_address, deploy_data=deploy_data)
        IconScoreContextUtil.get_deploy_info.return_value = None
        IconScoreContextUtil.is_service_flag_on.return_value = False
        self._score_deploy_engine._icon_score_deployer.deploy_legacy = Mock()
        IconScoreContextUtil.load_score.return_value = None
        self._score_deploy_engine._initialize_score = Mock()
        deploy_info = Mock(spec=IconScoreDeployInfo)
        deploy_info.configure_mock(next_tx_hash=None)
        IconScoreContextUtil.get_deploy_info.return_value = deploy_info

        with self.assertRaises(InvalidParamsException) as e:
            self._score_deploy_engine._on_deploy(self._context, tx_params)
        self.assertEqual(e.exception.code, ExceptionCode.INVALID_PARAMS)
        self.assertEqual(e.exception.message, f'score is None : {score_address}')
        IconScoreContextUtil.get_deploy_info.assert_called()
        IconScoreContextUtil.is_service_flag_on.assert_called()
        IconScoreContextUtil.try_score_package_validate.assert_not_called()
        self._score_deploy_engine._icon_score_deployer.deploy_legacy.assert_called()
        self._score_deploy_engine._initialize_score.assert_not_called()

    # Case when deploy_info is not None, next_tx_hash is None,
    # zip, revision0, score validator flag False, SCORE is not None
    @patch_several(GET_DEPLOY_INFO_PATCHER, IS_SERVICE_FLAG_ON_PATCHER, LOAD_SCORE_PATCHER,
                   PUT_SCORE_INFO_PATCHER, TRY_SCORE_PACKAGE_VALIDATE_PATCHER)
    def test_on_deploy_case35(self):
        score_address = create_address(1)
        deploy_content = b'deploy_mock_data'
        deploy_data = {"contentType": "application/zip", "content": deploy_content}
        tx_params = Mock(spec=IconScoreDeployTXParams)
        tx_params.configure_mock(score_address=score_address, deploy_data=deploy_data)
        IconScoreContextUtil.get_deploy_info.return_value = None
        IconScoreContextUtil.is_service_flag_on.return_value = True
        self._score_deploy_engine._icon_score_deployer.deploy_legacy = Mock()
        mock_score = MockScore(self)
        mock_score.owner = self._addr1
        IconScoreContextUtil.load_score.return_value = mock_score
        self._score_deploy_engine._initialize_score = Mock()
        deploy_info = Mock(spec=IconScoreDeployInfo)
        default_byte_value = bytes(DEFAULT_BYTE_SIZE)
        deploy_info.configure_mock(next_tx_hash=None)
        IconScoreContextUtil.get_deploy_info.return_value = deploy_info

        self._score_deploy_engine._on_deploy(self._context, tx_params)

        IconScoreContextUtil.load_score.assert_called_with(self._context, score_address, default_byte_value)
        self._score_deploy_engine._initialize_score.assert_called()
        IconScoreContextUtil.try_score_package_validate.assert_called_with\
            (self._context, score_address, default_byte_value)
        self._score_deploy_engine._icon_score_deployer. \
            deploy_legacy.assert_called_with(address=score_address, data=deploy_content, tx_hash=default_byte_value)
        IconScoreContextUtil.put_score_info.assert_called_with\
            (self._context, score_address, mock_score, default_byte_value)

    # Case when deploy_info is not None, next_tx_hash is None,
    # zip, revision0, score validator flag False, SCORE is not None
    @patch_several(GET_DEPLOY_INFO_PATCHER, IS_SERVICE_FLAG_ON_PATCHER, LOAD_SCORE_PATCHER,
                   PUT_SCORE_INFO_PATCHER, TRY_SCORE_PACKAGE_VALIDATE_PATCHER)
    def test_on_deploy_case36(self):
        score_address = create_address(1)
        deploy_content = b'deploy_mock_data'
        deploy_data = {"contentType": "application/zip", "content": deploy_content}
        tx_params = Mock(spec=IconScoreDeployTXParams)
        tx_params.configure_mock(score_address=score_address, deploy_data=deploy_data)
        IconScoreContextUtil.get_deploy_info.return_value = None
        IconScoreContextUtil.is_service_flag_on.return_value = False
        IconScoreContextUtil.load_score.return_value = None
        self._score_deploy_engine._icon_score_deployer.deploy_legacy = Mock()
        self._score_deploy_engine._initialize_score = Mock()
        deploy_info = Mock(spec=IconScoreDeployInfo)
        deploy_info.configure_mock(next_tx_hash=None)
        IconScoreContextUtil.get_deploy_info.return_value = deploy_info

        with self.assertRaises(InvalidParamsException) as e:
            self._score_deploy_engine._on_deploy(self._context, tx_params)
        self.assertEqual(e.exception.code, ExceptionCode.INVALID_PARAMS)
        self.assertEqual(e.exception.message, f'score is None : {score_address}')
        IconScoreContextUtil.get_deploy_info.assert_called()
        IconScoreContextUtil.is_service_flag_on.assert_called()
        IconScoreContextUtil.try_score_package_validate.assert_not_called()
        self._score_deploy_engine._icon_score_deployer.deploy_legacy.assert_called()
        self._score_deploy_engine._initialize_score.assert_not_called()

    # Case when deploy_info is not None, next_tx_hash is None,
    # zip, revision0, score validator flag False, SCORE is not None
    @patch_several(GET_DEPLOY_INFO_PATCHER, IS_SERVICE_FLAG_ON_PATCHER, LOAD_SCORE_PATCHER,
                   PUT_SCORE_INFO_PATCHER, TRY_SCORE_PACKAGE_VALIDATE_PATCHER,
                   GET_REVISION_PATCHER)
    def test_on_deploy_case37(self):
        score_address = create_address(1)
        deploy_content = b'deploy_mock_data'
        deploy_data = {"contentType": "application/zip", "content": deploy_content}
        tx_params = Mock(spec=IconScoreDeployTXParams)
        tx_params.configure_mock(score_address=score_address, deploy_data=deploy_data)
        IconScoreContextUtil.get_deploy_info.return_value = None
        IconScoreContextUtil.is_service_flag_on.return_value = False
        IconScoreContextUtil.get_revision.return_value = 2
        self._score_deploy_engine._icon_score_deployer.deploy = Mock()
        mock_score = MockScore(self)
        mock_score.owner = self._addr1
        IconScoreContextUtil.load_score.return_value = mock_score
        self._score_deploy_engine._initialize_score = Mock()
        deploy_info = Mock(spec=IconScoreDeployInfo)
        default_byte_value = bytes(DEFAULT_BYTE_SIZE)
        deploy_info.configure_mock(next_tx_hash=None)
        IconScoreContextUtil.get_deploy_info.return_value = deploy_info

        self._score_deploy_engine._on_deploy(self._context, tx_params)

        IconScoreContextUtil.load_score.assert_called_with(self._context, score_address, default_byte_value)
        self._score_deploy_engine._icon_score_deployer. \
            deploy.assert_called_with(address=score_address, data=deploy_content, tx_hash=default_byte_value)
        self._score_deploy_engine._initialize_score.assert_called()
        IconScoreContextUtil.try_score_package_validate.assert_not_called()
        IconScoreContextUtil.put_score_info.assert_called_with\
            (self._context, score_address, mock_score, default_byte_value)

    # Case when deploy_info is not None, next_tx_hash is None,
    # zip, revision0, score validator flag False, SCORE is not None
    @patch_several(GET_DEPLOY_INFO_PATCHER, IS_SERVICE_FLAG_ON_PATCHER, LOAD_SCORE_PATCHER,
                   PUT_SCORE_INFO_PATCHER, TRY_SCORE_PACKAGE_VALIDATE_PATCHER,
                   GET_REVISION_PATCHER)
    def test_on_deploy_case38(self):
        score_address = create_address(1)
        deploy_content = b'deploy_mock_data'
        deploy_data = {"contentType": "application/zip", "content": deploy_content}
        tx_params = Mock(spec=IconScoreDeployTXParams)
        tx_params.configure_mock(score_address=score_address, deploy_data=deploy_data)
        IconScoreContextUtil.is_service_flag_on.return_value = False
        IconScoreContextUtil.get_revision.return_value = 2
        self._score_deploy_engine._icon_score_deployer.deploy = Mock()
        IconScoreContextUtil.load_score.return_value = None
        self._score_deploy_engine._initialize_score = Mock()
        deploy_info = Mock(spec=IconScoreDeployInfo)
        deploy_info.configure_mock(next_tx_hash=None)
        IconScoreContextUtil.get_deploy_info.return_value = deploy_info

        with self.assertRaises(InvalidParamsException) as e:
            self._score_deploy_engine._on_deploy(self._context, tx_params)
        self.assertEqual(e.exception.code, ExceptionCode.INVALID_PARAMS)
        self.assertEqual(e.exception.message, f'score is None : {score_address}')
        IconScoreContextUtil.get_deploy_info.assert_called()
        IconScoreContextUtil.is_service_flag_on.assert_called()
        IconScoreContextUtil.try_score_package_validate.assert_not_called()
        self._score_deploy_engine._icon_score_deployer.deploy.assert_called()
        self._score_deploy_engine._initialize_score.assert_not_called()

    # Case when deploy_info is not None, next_tx_hash is None,
    # zip, revision0, score validator flag False, SCORE is not None
    @patch_several(GET_DEPLOY_INFO_PATCHER, IS_SERVICE_FLAG_ON_PATCHER, LOAD_SCORE_PATCHER,
                   PUT_SCORE_INFO_PATCHER, TRY_SCORE_PACKAGE_VALIDATE_PATCHER,
                   GET_REVISION_PATCHER)
    def test_on_deploy_case39(self):
        score_address = create_address(1)
        deploy_content = b'deploy_mock_data'
        deploy_data = {"contentType": "application/zip", "content": deploy_content}
        tx_params = Mock(spec=IconScoreDeployTXParams)
        tx_params.configure_mock(score_address=score_address, deploy_data=deploy_data)
        IconScoreContextUtil.is_service_flag_on.return_value = True
        IconScoreContextUtil.get_revision.return_value = 2
        self._score_deploy_engine._icon_score_deployer.deploy = Mock()
        mock_score = MockScore(self)
        mock_score.owner = self._addr1
        IconScoreContextUtil.load_score.return_value = mock_score
        self._score_deploy_engine._initialize_score = Mock()
        deploy_info = Mock(spec=IconScoreDeployInfo)
        default_byte_value = bytes(DEFAULT_BYTE_SIZE)
        deploy_info.configure_mock(next_tx_hash=None)
        IconScoreContextUtil.get_deploy_info.return_value = deploy_info

        self._score_deploy_engine._on_deploy(self._context, tx_params)

        IconScoreContextUtil.load_score.assert_called_with(self._context, score_address, default_byte_value)
        self._score_deploy_engine._icon_score_deployer. \
            deploy.assert_called_with(address=score_address, data=deploy_content, tx_hash=default_byte_value)
        self._score_deploy_engine._initialize_score.assert_called()
        IconScoreContextUtil.try_score_package_validate.assert_called_with\
            (self._context, score_address, default_byte_value)
        IconScoreContextUtil.put_score_info.assert_called_with\
            (self._context, score_address, mock_score, default_byte_value)

    # Case when deploy_info is not None, next_tx_hash is None,
    # zip, revision0, score validator flag False, SCORE is not None
    @patch_several(GET_DEPLOY_INFO_PATCHER, IS_SERVICE_FLAG_ON_PATCHER, LOAD_SCORE_PATCHER,
                   PUT_SCORE_INFO_PATCHER, TRY_SCORE_PACKAGE_VALIDATE_PATCHER,
                   GET_REVISION_PATCHER)
    def test_on_deploy_case40(self):
        score_address = create_address(1)
        deploy_content = b'deploy_mock_data'
        deploy_data = {"contentType": "application/zip", "content": deploy_content}
        tx_params = Mock(spec=IconScoreDeployTXParams)
        tx_params.configure_mock(score_address=score_address, deploy_data=deploy_data)
        IconScoreContextUtil.is_service_flag_on.return_value = True
        IconScoreContextUtil.get_revision.return_value = 2
        self._score_deploy_engine._icon_score_deployer.deploy = Mock()
        mock_score = MockScore(self)
        mock_score.owner = self._addr1
        IconScoreContextUtil.load_score.return_value = mock_score
        self._score_deploy_engine._initialize_score = Mock()
        deploy_info = Mock(spec=IconScoreDeployInfo)
        default_byte_value = bytes(DEFAULT_BYTE_SIZE)
        deploy_info.configure_mock(next_tx_hash=None)
        IconScoreContextUtil.get_deploy_info.return_value = deploy_info

        self._score_deploy_engine._on_deploy(self._context, tx_params)

        IconScoreContextUtil.load_score.assert_called_with(self._context, score_address, default_byte_value)
        self._score_deploy_engine._icon_score_deployer.\
            deploy.assert_called_with(address=score_address, data=deploy_content, tx_hash=default_byte_value)
        self._score_deploy_engine._initialize_score.assert_called()
        IconScoreContextUtil.try_score_package_validate.assert_called_with\
            (self._context, score_address, default_byte_value)
        IconScoreContextUtil.put_score_info.assert_called_with\
            (self._context, score_address, mock_score, default_byte_value)

    # Case when deploy_info is not None, next_tx_hash is None,
    # zip, revision0, score validator flag False, SCORE is not None
    @patch_several(GET_DEPLOY_INFO_PATCHER, IS_SERVICE_FLAG_ON_PATCHER, LOAD_SCORE_PATCHER,
                   PUT_SCORE_INFO_PATCHER, TRY_SCORE_PACKAGE_VALIDATE_PATCHER,
                   GET_REVISION_PATCHER, RENAME_DIRECTORY_PATCHER)
    def test_on_deploy_case41(self):
        score_address = create_address(1)
        deploy_content = b'deploy_mock_data'
        deploy_data = {"contentType": "application/zip", "content": deploy_content}
        tx_params = Mock(spec=IconScoreDeployTXParams)
        tx_params.configure_mock(score_address=score_address, deploy_data=deploy_data)
        IconScoreContextUtil.get_deploy_info.return_value = None
        IconScoreContextUtil.is_service_flag_on.return_value = False
        IconScoreContextUtil.get_revision.return_value = 3
        self._score_deploy_engine._icon_score_deployer.deploy = Mock()
        mock_score = MockScore(self)
        mock_score.owner = self._addr1
        IconScoreContextUtil.load_score.return_value = mock_score
        self._score_deploy_engine._initialize_score = Mock()
        deploy_info = Mock(spec=IconScoreDeployInfo)
        default_byte_value = bytes(DEFAULT_BYTE_SIZE)
        deploy_info.configure_mock(next_tx_hash=None)
        IconScoreContextUtil.get_deploy_info.return_value = deploy_info

        self._score_deploy_engine._on_deploy(self._context, tx_params)

        IconScoreContextUtil.load_score.assert_called_with(self._context, score_address, default_byte_value)
        self._score_deploy_engine._icon_score_deployer.deploy. \
            assert_called_with(address=score_address, data=deploy_content, tx_hash=default_byte_value)
        self._score_deploy_engine._initialize_score.assert_called()
        DirectoryNameChanger.rename_directory.assert_called()
        IconScoreContextUtil.try_score_package_validate.assert_not_called()
        IconScoreContextUtil.put_score_info.assert_called_with\
            (self._context, score_address, mock_score, default_byte_value)

    # Case when deploy_info is not None, next_tx_hash is None,
    # zip, revision0, score validator flag False, SCORE is not None
    @patch_several(GET_DEPLOY_INFO_PATCHER, IS_SERVICE_FLAG_ON_PATCHER, LOAD_SCORE_PATCHER,
                   PUT_SCORE_INFO_PATCHER, TRY_SCORE_PACKAGE_VALIDATE_PATCHER,
                   GET_REVISION_PATCHER, RENAME_DIRECTORY_PATCHER)
    def test_on_deploy_case42(self):
        score_address = create_address(1)
        deploy_content = b'deploy_mock_data'
        deploy_data = {"contentType": "application/zip", "content": deploy_content}
        tx_params = Mock(spec=IconScoreDeployTXParams)
        tx_params.configure_mock(score_address=score_address, deploy_data=deploy_data)
        IconScoreContextUtil.get_deploy_info.return_value = None
        IconScoreContextUtil.is_service_flag_on.return_value = False
        IconScoreContextUtil.get_revision.return_value = 4
        self._score_deploy_engine._icon_score_deployer.deploy = Mock()
        IconScoreContextUtil.load_score.return_value = None
        self._score_deploy_engine._initialize_score = Mock()
        deploy_info = Mock(spec=IconScoreDeployInfo)
        deploy_info.configure_mock(next_tx_hash=None)
        IconScoreContextUtil.get_deploy_info.return_value = deploy_info

        with self.assertRaises(InvalidParamsException) as e:
            self._score_deploy_engine._on_deploy(self._context, tx_params)
        self.assertEqual(e.exception.code, ExceptionCode.INVALID_PARAMS)
        self.assertEqual(e.exception.message, f'score is None : {score_address}')
        IconScoreContextUtil.get_deploy_info.assert_called()
        IconScoreContextUtil.is_service_flag_on.assert_called()
        IconScoreContextUtil.try_score_package_validate.assert_not_called()
        self._score_deploy_engine._icon_score_deployer.deploy.assert_called()
        self._score_deploy_engine._initialize_score.assert_not_called()

    # Case when deploy_info is not None, next_tx_hash is None,
    # zip, revision0, score validator flag False, SCORE is not None
    @patch_several(GET_DEPLOY_INFO_PATCHER, IS_SERVICE_FLAG_ON_PATCHER, LOAD_SCORE_PATCHER,
                   PUT_SCORE_INFO_PATCHER, TRY_SCORE_PACKAGE_VALIDATE_PATCHER,
                   GET_REVISION_PATCHER, RENAME_DIRECTORY_PATCHER)
    def test_on_deploy_case43(self):
        score_address = create_address(1)
        deploy_content = b'deploy_mock_data'
        deploy_data = {"contentType": "application/zip", "content": deploy_content}
        tx_params = Mock(spec=IconScoreDeployTXParams)
        tx_params.configure_mock(score_address=score_address, deploy_data=deploy_data)
        IconScoreContextUtil.get_deploy_info.return_value = None
        IconScoreContextUtil.is_service_flag_on.return_value = False
        IconScoreContextUtil.get_revision.return_value = 4
        self._score_deploy_engine._icon_score_deployer.deploy = Mock()
        mock_score = MockScore(self)
        mock_score.owner = self._addr1
        IconScoreContextUtil.load_score.return_value = mock_score
        self._score_deploy_engine._initialize_score = Mock()
        deploy_info = Mock(spec=IconScoreDeployInfo)
        default_byte_value = bytes(DEFAULT_BYTE_SIZE)
        deploy_info.configure_mock(next_tx_hash=None)
        IconScoreContextUtil.get_deploy_info.return_value = deploy_info

        self._score_deploy_engine._on_deploy(self._context, tx_params)

        IconScoreContextUtil.load_score.assert_called_with(self._context, score_address, default_byte_value)
        self._score_deploy_engine._icon_score_deployer.\
            deploy.assert_called_with(address=score_address, data=deploy_content, tx_hash=default_byte_value)
        self._score_deploy_engine._initialize_score.assert_called()
        DirectoryNameChanger.rename_directory.assert_called()
        IconScoreContextUtil.try_score_package_validate.assert_not_called()
        IconScoreContextUtil.put_score_info.assert_called_with\
            (self._context, score_address, mock_score, default_byte_value)

    # Case when deploy_info is not None, next_tx_hash is None,
    # zip, revision0, score validator flag False, SCORE is not None
    @patch_several(GET_DEPLOY_INFO_PATCHER, IS_SERVICE_FLAG_ON_PATCHER, LOAD_SCORE_PATCHER,
                   PUT_SCORE_INFO_PATCHER, TRY_SCORE_PACKAGE_VALIDATE_PATCHER,
                   GET_REVISION_PATCHER, RENAME_DIRECTORY_PATCHER)
    def test_on_deploy_case44(self):
        score_address = create_address(1)
        deploy_content = b'deploy_mock_data'
        deploy_data = {"contentType": "application/zip", "content": deploy_content}
        tx_params = Mock(spec=IconScoreDeployTXParams)
        tx_params.configure_mock(score_address=score_address, deploy_data=deploy_data)
        IconScoreContextUtil.get_deploy_info.return_value = None
        IconScoreContextUtil.is_service_flag_on.return_value = False
        IconScoreContextUtil.get_revision.return_value = 3
        self._score_deploy_engine._icon_score_deployer.deploy = Mock()
        IconScoreContextUtil.load_score.return_value = None
        self._score_deploy_engine._initialize_score = Mock()
        deploy_info = Mock(spec=IconScoreDeployInfo)
        deploy_info.configure_mock(next_tx_hash=None)
        IconScoreContextUtil.get_deploy_info.return_value = deploy_info

        with self.assertRaises(InvalidParamsException) as e:
            self._score_deploy_engine._on_deploy(self._context, tx_params)
        self.assertEqual(e.exception.code, ExceptionCode.INVALID_PARAMS)
        self.assertEqual(e.exception.message, f'score is None : {score_address}')
        IconScoreContextUtil.get_deploy_info.assert_called()
        IconScoreContextUtil.is_service_flag_on.assert_called()
        IconScoreContextUtil.try_score_package_validate.assert_not_called()
        self._score_deploy_engine._icon_score_deployer.deploy.assert_called()
        self._score_deploy_engine._initialize_score.assert_not_called()

    # Case when deploy_info is not None, next_tx_hash is None,
    # tbears, revision0, score validator flag False, SCORE is not None
    @patch_several(GET_DEPLOY_INFO_PATCHER, IS_SERVICE_FLAG_ON_PATCHER, LOAD_SCORE_PATCHER,
                   PUT_SCORE_INFO_PATCHER, TRY_SCORE_PACKAGE_VALIDATE_PATCHER,
                   GET_SCORE_ROOT_PATH_PATCHER, SYMLINK_PATCHER)
    def test_on_deploy_case45(self):
        score_address = create_address(1)
        deploy_content = b'deploy_mock_data'
        deploy_data = {"contentType": "application/tbears", "content": deploy_content}
        tx_params = Mock(spec=IconScoreDeployTXParams)
        tx_params.configure_mock(score_address=score_address, deploy_data=deploy_data)
        IconScoreContextUtil.get_deploy_info.return_value = None
        IconScoreContextUtil.is_service_flag_on.return_value = False
        IconScoreContextUtil.get_score_root_path.return_value = os.path.join(PROJECT_ROOT_PATH, self._ROOT_SCORE_PATH)
        mock_score = MockScore(self)
        mock_score.owner = self._addr1
        IconScoreContextUtil.load_score.return_value = mock_score
        self._score_deploy_engine._initialize_score = Mock()
        deploy_info = Mock(spec=IconScoreDeployInfo)
        deploy_info.configure_mock(next_tx_hash=None)
        default_byte_value = bytes(DEFAULT_BYTE_SIZE)
        IconScoreContextUtil.get_deploy_info.return_value = deploy_info

        self._score_deploy_engine._on_deploy(self._context, tx_params)

        IconScoreContextUtil.load_score.assert_called_with(self._context, score_address, default_byte_value)
        self._score_deploy_engine._initialize_score.assert_called()
        IconScoreContextUtil.try_score_package_validate.assert_not_called()
        IconScoreContextUtil.put_score_info.assert_called_with\
            (self._context, score_address, mock_score, default_byte_value)

    # Case when deploy_info is not None, next_tx_hash is None,
    # tbears, revision0, score validator flag False, SCORE is not None
    @patch_several(GET_DEPLOY_INFO_PATCHER, IS_SERVICE_FLAG_ON_PATCHER, LOAD_SCORE_PATCHER,
                   PUT_SCORE_INFO_PATCHER, TRY_SCORE_PACKAGE_VALIDATE_PATCHER,
                   GET_SCORE_ROOT_PATH_PATCHER, SYMLINK_PATCHER)
    def test_on_deploy_case46(self):
        score_address = create_address(1)
        deploy_content = b'deploy_mock_data'
        deploy_data = {"contentType": "application/tbears", "content": deploy_content}
        tx_params = Mock(spec=IconScoreDeployTXParams)
        tx_params.configure_mock(score_address=score_address, deploy_data=deploy_data)
        IconScoreContextUtil.get_deploy_info.return_value = None
        IconScoreContextUtil.is_service_flag_on.return_value = False
        IconScoreContextUtil.get_score_root_path.return_value = os.path.join(PROJECT_ROOT_PATH, self._ROOT_SCORE_PATH)
        IconScoreContextUtil.load_score.return_value = None
        self._score_deploy_engine._initialize_score = Mock()
        deploy_info = Mock(spec=IconScoreDeployInfo)
        deploy_info.configure_mock(next_tx_hash=None)
        IconScoreContextUtil.get_deploy_info.return_value = deploy_info
        self._score_deploy_engine._icon_score_deployer.deploy_legacy = Mock()

        with self.assertRaises(InvalidParamsException) as e:
            self._score_deploy_engine._on_deploy(self._context, tx_params)
        self.assertEqual(e.exception.code, ExceptionCode.INVALID_PARAMS)
        self.assertEqual(e.exception.message, f'score is None : {score_address}')
        IconScoreContextUtil.get_deploy_info.assert_called()
        IconScoreContextUtil.is_service_flag_on.assert_called()
        IconScoreContextUtil.try_score_package_validate.assert_not_called()
        self._score_deploy_engine._icon_score_deployer.deploy_legacy.assert_not_called()
        self._score_deploy_engine._initialize_score.assert_not_called()

    # Case when deploy_info is not None, next_tx_hash is None,
    # tbears, revision0, score validator flag False, SCORE is not None
    @patch_several(GET_DEPLOY_INFO_PATCHER, IS_SERVICE_FLAG_ON_PATCHER, LOAD_SCORE_PATCHER,
                   PUT_SCORE_INFO_PATCHER, TRY_SCORE_PACKAGE_VALIDATE_PATCHER,
                   GET_SCORE_ROOT_PATH_PATCHER, SYMLINK_PATCHER)
    def test_on_deploy_case47(self):
        score_address = create_address(1)
        deploy_content = b'deploy_mock_data'
        deploy_data = {"contentType": "application/tbears", "content": deploy_content}
        tx_params = Mock(spec=IconScoreDeployTXParams)
        tx_params.configure_mock(score_address=score_address, deploy_data=deploy_data)
        IconScoreContextUtil.get_deploy_info.return_value = None
        IconScoreContextUtil.is_service_flag_on.return_value = True
        IconScoreContextUtil.get_score_root_path.return_value = os.path.join(PROJECT_ROOT_PATH, self._ROOT_SCORE_PATH)
        mock_score = MockScore(self)
        mock_score.owner = self._addr1
        IconScoreContextUtil.load_score.return_value = mock_score
        self._score_deploy_engine._initialize_score = Mock()
        deploy_info = Mock(spec=IconScoreDeployInfo)
        default_byte_value = bytes(DEFAULT_BYTE_SIZE)
        deploy_info.configure_mock(next_tx_hash=None)
        IconScoreContextUtil.get_deploy_info.return_value = deploy_info

        self._score_deploy_engine._on_deploy(self._context, tx_params)

        IconScoreContextUtil.load_score.assert_called_with(self._context, score_address, default_byte_value)
        self._score_deploy_engine._initialize_score.assert_called()
        IconScoreContextUtil.try_score_package_validate.assert_called_with\
            (self._context, score_address, default_byte_value)
        IconScoreContextUtil.put_score_info.assert_called_with\
            (self._context, score_address, mock_score, default_byte_value)

    # Case when deploy_info is not None, next_tx_hash is None,
    # tbears, revision0, score validator flag False, SCORE is not None
    @patch_several(GET_DEPLOY_INFO_PATCHER, IS_SERVICE_FLAG_ON_PATCHER, LOAD_SCORE_PATCHER,
                   PUT_SCORE_INFO_PATCHER, TRY_SCORE_PACKAGE_VALIDATE_PATCHER,
                   GET_SCORE_ROOT_PATH_PATCHER, SYMLINK_PATCHER)
    def test_on_deploy_case48(self):
        score_address = create_address(1)
        deploy_content = b'deploy_mock_data'
        deploy_data = {"contentType": "application/tbears", "content": deploy_content}
        tx_params = Mock(spec=IconScoreDeployTXParams)
        tx_params.configure_mock(score_address=score_address, deploy_data=deploy_data)
        IconScoreContextUtil.get_deploy_info.return_value = None
        IconScoreContextUtil.is_service_flag_on.return_value = True
        IconScoreContextUtil.get_score_root_path.return_value = os.path.join(PROJECT_ROOT_PATH, self._ROOT_SCORE_PATH)
        IconScoreContextUtil.load_score.return_value = None
        self._score_deploy_engine._initialize_score = Mock()
        deploy_info = Mock(spec=IconScoreDeployInfo)
        deploy_info.configure_mock(next_tx_hash=None)
        IconScoreContextUtil.get_deploy_info.return_value = deploy_info

        with self.assertRaises(InvalidParamsException) as e:
            self._score_deploy_engine._on_deploy(self._context, tx_params)
        self.assertEqual(e.exception.code, ExceptionCode.INVALID_PARAMS)
        self.assertEqual(e.exception.message, f'score is None : {score_address}')
        IconScoreContextUtil.get_deploy_info.assert_called()
        IconScoreContextUtil.is_service_flag_on.assert_called()
        IconScoreContextUtil.try_score_package_validate.assert_called()
        self._score_deploy_engine._initialize_score.assert_not_called()

    def test_initialize_score(self):
        pass

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


