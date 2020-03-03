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
from iconservice.base.type_converter import TypeConverter
from iconservice.database.factory import ContextDatabaseFactory
from iconservice.icon_constant import DeployType
from iconservice.deploy import engine as isde
from iconservice.deploy import DeployStorage
from iconservice.deploy.storage import IconScoreDeployTXParams, IconScoreDeployInfo
from iconservice.deploy.icon_score_deployer import IconScoreDeployer
from iconservice.icon_constant import ICON_DEX_DB_NAME, IconServiceFlag
from iconservice.iconscore.icon_score_context import IconScoreContextType, IconScoreContext
from iconservice.iconscore.icon_score_context_util import IconScoreContextUtil
from iconservice.iconscore.icon_score_mapper import IconScoreMapper
from iconservice.iconscore.icon_score_step import IconScoreStepCounter
from iconservice.icx import IcxEngine
from iconservice.icx import IcxStorage
from iconservice.utils import ContextStorage
from tests import rmtree, create_address, create_tx_hash, create_block_hash

PROJECT_ROOT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../'))

IS_SERVICE_FLAG_ON_PATCHER = patch('iconservice.iconscore.\
icon_score_context_util.IconScoreContextUtil.is_service_flag_on')
GET_OWNER_PATCHER = patch('iconservice.iconscore.icon_score_context_util.IconScoreContextUtil.get_owner')
GET_DEPLOY_TX_PARAMS_PATCHER = patch('iconservice.iconscore.icon_score_context_util.\
IconScoreContextUtil.get_deploy_tx_params')
VALIDATE_SCORE_BLACKLIST_PATCHER = patch('iconservice.iconscore.icon_score_context_util.\
IconScoreContextUtil.validate_score_blacklist')
VALIDATE_DEPLOYER = patch('iconservice.iconscore.icon_score_context_util.\
IconScoreContextUtil.validate_deployer')
VALIDATE_PACKAGE_PATCHER = patch('iconservice.iconscore.icon_score_context_util.\
IconScoreContextUtil.validate_score_package')
MAKE_DIR_PATCHER = patch('iconservice.deploy.engine.os.makedirs')
GET_SCORE_DEPLOY_PATH_PATCHER = patch('iconservice.deploy.engine.get_score_deploy_path')
OS_PATH_JOIN_PATCHER = patch('iconservice.deploy.engine.os.path.join')
GET_SCORE_PATH_PATCHER = patch('iconservice.deploy.engine.get_score_path', return_value='aa')
SYMLINK_PATCHER = patch('iconservice.deploy.engine.os.symlink')
GET_SCORE_INFO_PATCHER = patch('iconservice.iconscore.icon_score_context_util.IconScoreContextUtil.get_score_info')
CREATE_SCORE_INFO_PATCHER = patch('iconservice.iconscore.icon_score_context_util.IconScoreContextUtil.create_score_info')
DEPLOY_PATCHER = patch('iconservice.deploy.icon_score_deployer.IconScoreDeployer.deploy')
DEPLOY_LEGACY_PATCHER = patch('iconservice.deploy.icon_score_deployer.IconScoreDeployer.deploy_legacy')
REMOVE_PATH_PATCHER = patch('iconservice.deploy.engine.remove_path')
MAKE_ANNOTATIONS_FROM_METHOD_PATCHER = patch('iconservice.base.type_converter.'
                                             'TypeConverter.make_annotations_from_method', return_value="annotations")
CONVERT_DATA_PARAMS_PATCHER = patch('iconservice.base.type_converter.'
                                    'TypeConverter.convert_data_params')
ZIP_TYPE = "application/zip"
TBEARS_TYPE = "application/tbears"


class MockScore(object):
    pass


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


class TestScoreDeployEngine(unittest.TestCase):
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
        self._score_deploy_engine = isde.Engine()
        self._deploy_storage = DeployStorage(self._icx_db)

        self._icon_score_mapper = IconScoreMapper()

        self.addr1 = create_address(AddressPrefix.EOA)
        self.addr2 = create_address(AddressPrefix.EOA)
        self.score_address = create_address(AddressPrefix.CONTRACT)
        self._score_deploy_engine.open()
        IconScoreContext.storage = ContextStorage(
            deploy=self._deploy_storage,
            fee=None,
            icx=None,
            iiss=None,
            prep=None,
            issue=None,
            rc=None,
            meta=None,
        )

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
        self._context.msg = Message(self.addr1, 0)

        self._context.tx = Transaction(
            create_tx_hash(), origin=self.addr1)
        self._context.block = Block(1, create_block_hash(), 0, None, 0)
        self._context.icon_score_mapper = self._icon_score_mapper
        self._context.icx = IcxEngine()
        self._context.revision = 0
        self._context.new_icon_score_mapper = {}
        self._step_counter: IconScoreStepCounter = \
            self.__step_counter_factory.create(IconScoreContextType.INVOKE)
        self._context.step_counter = self._step_counter
        self._context.icx.open(self._icx_storage)
        self._context.event_logs = Mock(spec=list)
        self._context.traces = Mock(spec=list)

    def _invoke_setUp(self, _is_audit_needed: bool):
        self._score_deploy_engine._is_audit_needed = Mock(return_value=_is_audit_needed)
        self._score_deploy_engine.deploy = Mock()
        self._deploy_storage.put_deploy_info_and_tx_params = Mock()

    def _is_audit_needed_setUp(self, revision: int, get_owner, is_service_flag_on: bool):
        self._context.revision = revision
        IconScoreContextUtil.is_service_flag_on.return_value = is_service_flag_on
        IconScoreContextUtil.get_owner.return_value = get_owner

    def _deploy_setUp(self, get_deploy_tx_params=None):
        self._score_deploy_engine._score_deploy = Mock()
        self._deploy_storage.update_score_info = Mock()
        self._deploy_storage.get_deploy_tx_params = Mock(return_value=get_deploy_tx_params)

    def _score_deploy_setUp(self, legacy_tbears_mode: bool=False):
        self._score_deploy_engine._on_deploy = Mock()
        self._context.legacy_tbears_mode = legacy_tbears_mode

    # case when icon_score_address is in (None, ZERO_ADDRESS)
    @patch_several(VALIDATE_SCORE_BLACKLIST_PATCHER, IS_SERVICE_FLAG_ON_PATCHER, VALIDATE_DEPLOYER)
    def test_invoke_case1(self):
        self._invoke_setUp(True)

        with self.assertRaises(AssertionError):
            self._score_deploy_engine.invoke(self._context, GOVERNANCE_SCORE_ADDRESS, ZERO_SCORE_ADDRESS, {})
        IconScoreContextUtil.validate_score_blacklist.assert_not_called()
        IconScoreContextUtil.validate_deployer.assert_not_called()
        self._deploy_storage.put_deploy_info_and_tx_params.assert_not_called()
        self._score_deploy_engine._is_audit_needed.assert_not_called()
        self._score_deploy_engine.deploy.assert_not_called()

        with self.assertRaises(AssertionError):
            self._score_deploy_engine.invoke(self._context, GOVERNANCE_SCORE_ADDRESS, None, {})
        IconScoreContextUtil.validate_score_blacklist.assert_not_called()
        IconScoreContextUtil.validate_deployer.assert_not_called()
        self._deploy_storage.put_deploy_info_and_tx_params.assert_not_called()
        self._score_deploy_engine._is_audit_needed.assert_not_called()
        self._score_deploy_engine.deploy.assert_not_called()

    # case when deployer_white_list flag on, ignore audit
    @patch_several(IS_SERVICE_FLAG_ON_PATCHER, VALIDATE_DEPLOYER)
    def test_invoke_case2(self):
        self._invoke_setUp(False)

        self._score_deploy_engine.invoke(self._context, ZERO_SCORE_ADDRESS, GOVERNANCE_SCORE_ADDRESS, {})

        IconScoreContextUtil.validate_deployer.assert_called_with(self._context, self._context.tx.origin)
        self._deploy_storage.put_deploy_info_and_tx_params.\
            assert_called_with(self._context, GOVERNANCE_SCORE_ADDRESS, DeployType.INSTALL, self._context.tx.origin,
                               self._context.tx.hash, {})
        self._score_deploy_engine.deploy.assert_called_with(self._context, self._context.tx.hash)

    # case when deployer_white_list flag on, audit
    @patch_several(IS_SERVICE_FLAG_ON_PATCHER, VALIDATE_DEPLOYER)
    def test_invoke_case3(self):
        self._invoke_setUp(True)

        self._score_deploy_engine.invoke(self._context, ZERO_SCORE_ADDRESS, GOVERNANCE_SCORE_ADDRESS, {})

        IconScoreContextUtil.validate_deployer.assert_called_with(self._context, self._context.tx.origin)
        self._deploy_storage.put_deploy_info_and_tx_params.\
            assert_called_with(self._context, GOVERNANCE_SCORE_ADDRESS, DeployType.INSTALL, self._context.tx.origin,
                               self._context.tx.hash, {})
        self._score_deploy_engine.deploy.assert_not_called()

    # case when deployer_white_list flag off, audit
    @patch_several(IS_SERVICE_FLAG_ON_PATCHER, VALIDATE_DEPLOYER)
    def test_invoke_case4(self):
        self._invoke_setUp(False)

        self._score_deploy_engine.invoke(self._context, ZERO_SCORE_ADDRESS, GOVERNANCE_SCORE_ADDRESS, {})

        IconScoreContextUtil.validate_deployer.assert_called_with(self._context, self._context.tx.origin)
        self._deploy_storage.put_deploy_info_and_tx_params. \
            assert_called_with(self._context, GOVERNANCE_SCORE_ADDRESS, DeployType.INSTALL, self._context.tx.origin,
                               self._context.tx.hash, {})
        self._score_deploy_engine.deploy.assert_called_with(self._context, self._context.tx.hash)

    # case when deployer_white_list flag off, audit on
    @patch_several(IS_SERVICE_FLAG_ON_PATCHER, VALIDATE_DEPLOYER)
    def test_invoke_case5(self):
        self._invoke_setUp(True)

        self._score_deploy_engine.invoke(self._context, ZERO_SCORE_ADDRESS, GOVERNANCE_SCORE_ADDRESS, {})

        IconScoreContextUtil.validate_deployer.assert_called_with(self._context, self._context.tx.origin)
        self._score_deploy_engine.deploy.assert_not_called()

    # case when revision0, owner, audit false
    @patch_several(GET_OWNER_PATCHER, IS_SERVICE_FLAG_ON_PATCHER)
    def test_is_audit_needed_case1(self):
        self._is_audit_needed_setUp(0, self.addr1, False)

        result = self._score_deploy_engine._is_audit_needed(self._context, GOVERNANCE_SCORE_ADDRESS)
        IconScoreContextUtil.get_owner.assert_called_with(self._context, GOVERNANCE_SCORE_ADDRESS)
        IconScoreContextUtil.is_service_flag_on.assert_called_with(self._context, IconServiceFlag.AUDIT)
        self.assertFalse(result)

    # case when revision0, owner x, audit false
    @patch_several(GET_OWNER_PATCHER, IS_SERVICE_FLAG_ON_PATCHER)
    def test_is_audit_needed_case2(self):
        self._is_audit_needed_setUp(0, self.addr2, False)

        result = self._score_deploy_engine._is_audit_needed(self._context, GOVERNANCE_SCORE_ADDRESS)
        IconScoreContextUtil.get_owner.assert_called_with(self._context, GOVERNANCE_SCORE_ADDRESS)
        IconScoreContextUtil.is_service_flag_on.assert_called_with(self._context, IconServiceFlag.AUDIT)
        self.assertFalse(result)

    # case when revision0, owner, audit true
    @patch_several(GET_OWNER_PATCHER, IS_SERVICE_FLAG_ON_PATCHER)
    def test_is_audit_needed_case3(self):
        self._is_audit_needed_setUp(0, self.addr1, True)

        result = self._score_deploy_engine._is_audit_needed(self._context, GOVERNANCE_SCORE_ADDRESS)
        IconScoreContextUtil.get_owner.assert_called_with(self._context, GOVERNANCE_SCORE_ADDRESS)
        IconScoreContextUtil.is_service_flag_on.assert_called_with(self._context, IconServiceFlag.AUDIT)
        self.assertTrue(result)

    # case when revision0, owner x, audit true
    @patch_several(GET_OWNER_PATCHER, IS_SERVICE_FLAG_ON_PATCHER)
    def test_is_audit_needed_case4(self):
        self._is_audit_needed_setUp(0, self.addr2, True)

        result = self._score_deploy_engine._is_audit_needed(self._context, GOVERNANCE_SCORE_ADDRESS)
        IconScoreContextUtil.get_owner.assert_called_with(self._context, GOVERNANCE_SCORE_ADDRESS)
        IconScoreContextUtil.is_service_flag_on.assert_called_with(self._context, IconServiceFlag.AUDIT)
        self.assertTrue(result)

    # case when revision2, transaction requested by owner, audit true, system_score
    @patch_several(GET_OWNER_PATCHER, IS_SERVICE_FLAG_ON_PATCHER)
    def test_is_audit_needed_case5(self):
        self._is_audit_needed_setUp(2, self.addr1, True)

        result = self._score_deploy_engine._is_audit_needed(self._context, GOVERNANCE_SCORE_ADDRESS)
        IconScoreContextUtil.get_owner.assert_called_with(self._context, GOVERNANCE_SCORE_ADDRESS)
        IconScoreContextUtil.is_service_flag_on.assert_called_with(self._context, IconServiceFlag.AUDIT)
        self.assertFalse(result)

    # case when revision2, transaction requested by stranger, audit true, system_score
    @patch_several(GET_OWNER_PATCHER, IS_SERVICE_FLAG_ON_PATCHER)
    def test_is_audit_needed_case6(self):
        self._is_audit_needed_setUp(2, self.addr2, True)

        result = self._score_deploy_engine._is_audit_needed(self._context, GOVERNANCE_SCORE_ADDRESS)
        IconScoreContextUtil.get_owner.assert_called_with(self._context, GOVERNANCE_SCORE_ADDRESS)
        IconScoreContextUtil.is_service_flag_on.assert_called_with(self._context, IconServiceFlag.AUDIT)
        self.assertTrue(result)

    # case when revision2, transaction requested by owner, audit false, system_score
    @patch_several(GET_OWNER_PATCHER, IS_SERVICE_FLAG_ON_PATCHER)
    def test_is_audit_needed_case7(self):
        self._is_audit_needed_setUp(2, self.addr1, False)

        result = self._score_deploy_engine._is_audit_needed(self._context, GOVERNANCE_SCORE_ADDRESS)
        IconScoreContextUtil.get_owner.assert_called_with(self._context, GOVERNANCE_SCORE_ADDRESS)
        IconScoreContextUtil.is_service_flag_on.assert_called_with(self._context, IconServiceFlag.AUDIT)
        self.assertFalse(result)

    # case when revision2, transaction requested by stranger, audit false, system_score
    @patch_several(GET_OWNER_PATCHER, IS_SERVICE_FLAG_ON_PATCHER)
    def test_is_audit_needed_case8(self):
        self._is_audit_needed_setUp(2, self.addr1, False)

        result = self._score_deploy_engine._is_audit_needed(self._context, GOVERNANCE_SCORE_ADDRESS)
        IconScoreContextUtil.get_owner.assert_called_with(self._context, GOVERNANCE_SCORE_ADDRESS)
        IconScoreContextUtil.is_service_flag_on.assert_called_with(self._context, IconServiceFlag.AUDIT)
        self.assertFalse(result)

    # case when revision2, transaction requested by owner, audit true, normal_score
    @patch_several(GET_OWNER_PATCHER, IS_SERVICE_FLAG_ON_PATCHER)
    def test_is_audit_needed_case9(self):
        self._is_audit_needed_setUp(2, self.addr1, True)

        result = self._score_deploy_engine._is_audit_needed(self._context, self.score_address)
        IconScoreContextUtil.get_owner.assert_called_with(self._context, self.score_address)
        IconScoreContextUtil.is_service_flag_on.assert_called_with(self._context, IconServiceFlag.AUDIT)
        self.assertTrue(result)

    # case when revision2, transaction requested by stranger, audit true, normal_score
    @patch_several(GET_OWNER_PATCHER, IS_SERVICE_FLAG_ON_PATCHER)
    def test_is_audit_needed_case10(self):
        self._is_audit_needed_setUp(2, self.addr2, True)

        result = self._score_deploy_engine._is_audit_needed(self._context, self.score_address)
        IconScoreContextUtil.get_owner.assert_called_with(self._context, self.score_address)
        IconScoreContextUtil.is_service_flag_on.assert_called_with(self._context, IconServiceFlag.AUDIT)
        self.assertTrue(result)

    # case when revision2, transaction requested by owner, audit false, normal_score
    @patch_several(GET_OWNER_PATCHER, IS_SERVICE_FLAG_ON_PATCHER)
    def test_is_audit_needed_case11(self):
        self._is_audit_needed_setUp(2, self.addr1, False)

        result = self._score_deploy_engine._is_audit_needed(self._context, self.score_address)
        IconScoreContextUtil.get_owner.assert_called_with(self._context, self.score_address)
        IconScoreContextUtil.is_service_flag_on.assert_called_with(self._context, IconServiceFlag.AUDIT)
        self.assertFalse(result)

    # case when revision2, transaction requested by stranger, audit false, normal_score
    @patch_several(GET_OWNER_PATCHER, IS_SERVICE_FLAG_ON_PATCHER)
    def test_is_audit_needed_case12(self):
        self._is_audit_needed_setUp(2, self.addr1, False)

        result = self._score_deploy_engine._is_audit_needed(self._context, self.score_address)
        IconScoreContextUtil.get_owner.assert_called_with(self._context, self.score_address)
        IconScoreContextUtil.is_service_flag_on.assert_called_with(self._context, IconServiceFlag.AUDIT)
        self.assertFalse(result)

    # case when tx_param is None
    @patch_several(GET_DEPLOY_TX_PARAMS_PATCHER)
    def test_deploy_case1(self):
        self._deploy_setUp()

        with self.assertRaises(InvalidParamsException) as e:
            self._score_deploy_engine.deploy(self._context, self._context.tx.hash)

        self._deploy_storage.get_deploy_tx_params.assert_called_with(self._context, self._context.tx.hash)
        self.assertEqual(e.exception.code, ExceptionCode.INVALID_PARAMETER)
        self._score_deploy_engine._score_deploy.assert_not_called()
        IconScoreContext.storage.deploy.update_score_info.assert_not_called()

    # case when tx_param is not None
    @patch_several(GET_DEPLOY_TX_PARAMS_PATCHER)
    def test_deploy_case2(self):
        tx_params = Mock(spec=IconScoreDeployTXParams)
        tx_params.configure_mock(score_address=GOVERNANCE_SCORE_ADDRESS)
        self._deploy_setUp(tx_params)

        self._score_deploy_engine.deploy(self._context, self._context.tx.hash)

        self._score_deploy_engine._score_deploy.assert_called_with(self._context, tx_params)
        IconScoreContext.storage.deploy.\
            update_score_info.assert_called_with(self._context, GOVERNANCE_SCORE_ADDRESS, self._context.tx.hash)

    # test for tbears mode, legacy_tbears_mode is True
    def test_score_deploy_case1(self):
        self._score_deploy_setUp(True)
        tx_params = Mock(spec=IconScoreDeployTXParams)
        tx_params.configure_mock(deploy_data={'contentType': 'application/tbears', 'content': '0x1234'})

        self._score_deploy_engine._score_deploy(self._context, tx_params)

        self._score_deploy_engine._on_deploy.assert_called_with(self._context, tx_params)

    # test for tbears mode, and legacy_tbears_mode is False
    def test_score_deploy_case2(self):
        tx_params = Mock(spec=IconScoreDeployTXParams)
        tx_params.configure_mock(deploy_data={'contentType': 'application/tbears', 'content': '0x1234'})
        self._score_deploy_setUp()

        with self.assertRaises(InvalidParamsException) as e:
            self._score_deploy_engine._score_deploy(self._context, tx_params)
        self.assertEqual(e.exception.code, ExceptionCode.INVALID_PARAMETER)
        self.assertEqual(e.exception.message, f"Invalid contentType: application/tbears")
        self._score_deploy_engine._on_deploy.assert_not_called()

    # test for zip mode
    def test_score_deploy_case3(self):
        tx_params = Mock(spec=IconScoreDeployTXParams)
        tx_params.configure_mock(deploy_data={'contentType': 'application/zip', 'content': '0x1234'})
        self._score_deploy_setUp()

        self._score_deploy_engine._score_deploy(self._context, tx_params)

        self._score_deploy_engine._on_deploy.assert_called_with(self._context, tx_params)

    # test for wrong contentType
    def test_score_deploy_case4(self):
        self._score_deploy_setUp()
        tx_params = Mock(spec=IconScoreDeployTXParams)
        tx_params.configure_mock(deploy_data={'contentType': 'wrong/content', 'content': '0x1234'})

        with self.assertRaises(InvalidParamsException) as e:
            self._score_deploy_engine._score_deploy(self._context, tx_params)
        self.assertEqual(e.exception.code, ExceptionCode.INVALID_PARAMETER)
        self.assertEqual(e.exception.message, f'Invalid contentType: wrong/content')
        self._score_deploy_engine._on_deploy.assert_not_called()

    # Case when deploy_info is not None, zip, revision0, score validator flag False, SCORE is not None
    @patch_several(VALIDATE_PACKAGE_PATCHER)
    def test_on_deploy(self):
        mock_score = MockScore()
        mock_score.owner = self.addr1
        deploy_params = {"a": 1}
        deploy_data = {"params": deploy_params}
        deploy_info = Mock(spec=IconScoreDeployInfo)
        deploy_type = 'deploy_type'
        next_tx_hash = b'\00\01' * 16
        deploy_info.configure_mock(next_tx_hash=next_tx_hash)
        tx_params = Mock(spec=IconScoreDeployTXParams)
        tx_params.configure_mock(score_address=self.score_address, deploy_data=deploy_data, deploy_type=deploy_type,
                                 params=deploy_params)

        backup_msg, backup_tx = self._context.msg, self._context.tx

        self._score_deploy_engine._write_score_to_filesystem = Mock()
        score_info = Mock()
        score_info.configure_mock(get_score=Mock(return_value=mock_score))
        self._score_deploy_engine._create_score_info = Mock(return_value=score_info)
        self._deploy_storage.get_deploy_info = Mock(return_value=deploy_info)
        self._score_deploy_engine._initialize_score = Mock()

        self._score_deploy_engine._on_deploy(self._context, tx_params)

        self._deploy_storage.get_deploy_info.assert_called_with(self._context, self.score_address)
        self._score_deploy_engine._write_score_to_filesystem.assert_called_with(self._context, self.score_address,
                                                                                next_tx_hash, deploy_data)
        IconScoreContextUtil.validate_score_package.assert_called_with(self._context, self.score_address,
                                                                       next_tx_hash)
        self._score_deploy_engine._create_score_info.assert_called_with(self._context, self.score_address, next_tx_hash)
        score_info.get_score.assert_called_with(self._context.revision)
        self._score_deploy_engine._initialize_score.assert_called_with(deploy_type, mock_score, deploy_params)

        self.assertEqual(self._context.msg, backup_msg)
        self.assertEqual(self._context.tx, backup_tx)

    # tbears mode
    def test_write_score_to_filesystem_case1(self):
        content = '0x1234'
        deploy_data = {'contentType': 'application/tbears', 'content': content}
        self._score_deploy_engine._write_score_to_score_deploy_path_on_tbears_mode = Mock()

        self._score_deploy_engine._write_score_to_filesystem(self._context, GOVERNANCE_SCORE_ADDRESS,
                                                             self._context.tx.hash, deploy_data)
        self._score_deploy_engine._write_score_to_score_deploy_path_on_tbears_mode.\
            assert_called_with(self._context, GOVERNANCE_SCORE_ADDRESS, self._context.tx.hash, content)

    # normal mode
    def test_write_score_to_filesystem_case2(self):
        content = '0x1234'
        deploy_data = {'contentType': 'application/zip', 'content': content}
        self._score_deploy_engine._write_score_to_score_deploy_path = Mock()

        self._score_deploy_engine._write_score_to_filesystem(self._context, GOVERNANCE_SCORE_ADDRESS,
                                                             self._context.tx.hash, deploy_data)
        self._score_deploy_engine._write_score_to_score_deploy_path. \
            assert_called_with(self._context, GOVERNANCE_SCORE_ADDRESS, self._context.tx.hash, content)

    # case when current_score_info is None
    @patch_several(GET_SCORE_INFO_PATCHER, CREATE_SCORE_INFO_PATCHER)
    def test_create_score_info_case1(self):
        IconScoreContextUtil.get_score_info.return_value = None

        self._score_deploy_engine._create_score_info(self._context, GOVERNANCE_SCORE_ADDRESS, self._context.tx.hash)
        IconScoreContextUtil.create_score_info.assert_called_with(self._context, GOVERNANCE_SCORE_ADDRESS,
                                                                  self._context.tx.hash, None)

    # case when current_score_info is not None
    @patch_several(GET_SCORE_INFO_PATCHER, CREATE_SCORE_INFO_PATCHER)
    def test_create_score_info_case2(self):
        db = 'db'
        score_info_mock = Mock()
        score_info_mock.configure_mock(score_db=db)
        IconScoreContextUtil.get_score_info.return_value = score_info_mock

        self._score_deploy_engine._create_score_info(self._context, GOVERNANCE_SCORE_ADDRESS, self._context.tx.hash)
        IconScoreContextUtil.create_score_info.assert_called_with(self._context, GOVERNANCE_SCORE_ADDRESS,
                                                                  self._context.tx.hash, db)

    @patch_several(GET_SCORE_PATH_PATCHER, GET_SCORE_DEPLOY_PATH_PATCHER, SYMLINK_PATCHER, MAKE_DIR_PATCHER)
    def test_write_score_to_score_deploy_path_on_tbears_mode(self):
        score_deploy_path = 'score_deploy_path'
        isde.get_score_deploy_path.return_value = score_deploy_path
        score_path = 'score_path'
        isde.get_score_path.return_value = score_path

        self._score_deploy_engine._write_score_to_score_deploy_path_on_tbears_mode\
            (self._context, GOVERNANCE_SCORE_ADDRESS, self._context.tx.hash, None)

        isde.get_score_path.assert_called_with(self._context.score_root_path, GOVERNANCE_SCORE_ADDRESS)
        os.makedirs.assert_called_with(score_path, exist_ok=True)
        os.symlink.assert_called_with(None, score_deploy_path, target_is_directory=True)

    # case when revision3
    @patch_several(DEPLOY_PATCHER, REMOVE_PATH_PATCHER, GET_SCORE_DEPLOY_PATH_PATCHER, OS_PATH_JOIN_PATCHER)
    def test_write_score_to_score_deploy_path_case1(self):
        self._context.revision = 3
        score_path = 'score_path'
        score_deploy_path = 'score_deploy_path'
        isde.get_score_deploy_path.return_value = 'score_deploy_path'
        os.path.join.return_value = score_path
        self._score_deploy_engine._write_score_to_score_deploy_path(self._context, GOVERNANCE_SCORE_ADDRESS,
                                                                    self._context.tx.hash, None)

        isde.get_score_deploy_path.assert_called_with(self._context.score_root_path, GOVERNANCE_SCORE_ADDRESS,
                                                      self._context.tx.hash)
        os.path.join.assert_called_with(self._context.score_root_path, GOVERNANCE_SCORE_ADDRESS.to_bytes().hex(),
                                        f"0x{self._context.tx.hash.hex()}")
        isde.remove_path.assert_called_with(score_path)
        IconScoreDeployer.deploy.assert_called_with(score_deploy_path, None, 3)

    # case when revision2
    @patch_several(DEPLOY_PATCHER, REMOVE_PATH_PATCHER, GET_SCORE_DEPLOY_PATH_PATCHER, OS_PATH_JOIN_PATCHER)
    def test_write_score_to_score_deploy_path_case1(self):
        self._context.revision = 2
        score_path = 'score_path'
        score_deploy_path = 'score_deploy_path'
        isde.get_score_deploy_path.return_value = 'score_deploy_path'
        os.path.join.return_value = score_path
        self._score_deploy_engine._write_score_to_score_deploy_path(self._context, GOVERNANCE_SCORE_ADDRESS,
                                                                    self._context.tx.hash, None)

        isde.get_score_deploy_path.assert_called_with(self._context.score_root_path, GOVERNANCE_SCORE_ADDRESS,
                                                      self._context.tx.hash)
        os.path.join.assert_not_called()
        isde.remove_path.assert_not_called()
        IconScoreDeployer.deploy.assert_called_with(score_deploy_path, None, 2)

    # case when revision0
    @patch_several(DEPLOY_PATCHER, DEPLOY_LEGACY_PATCHER, REMOVE_PATH_PATCHER,
                   GET_SCORE_DEPLOY_PATH_PATCHER, OS_PATH_JOIN_PATCHER)
    def test_write_score_to_score_deploy_path_case1(self):
        score_path = 'score_path'
        score_deploy_path = 'score_deploy_path'
        isde.get_score_deploy_path.return_value = 'score_deploy_path'
        os.path.join.return_value = score_path
        self._score_deploy_engine._write_score_to_score_deploy_path(self._context, GOVERNANCE_SCORE_ADDRESS,
                                                                    self._context.tx.hash, None)

        isde.get_score_deploy_path.assert_called_with(self._context.score_root_path, GOVERNANCE_SCORE_ADDRESS,
                                                      self._context.tx.hash)
        os.path.join.assert_not_called()
        isde.remove_path.assert_not_called()
        IconScoreDeployer.deploy.assert_not_called()
        IconScoreDeployer.deploy_legacy.assert_called_with(score_deploy_path, None)

    # case on_install
    @patch_several(MAKE_ANNOTATIONS_FROM_METHOD_PATCHER, CONVERT_DATA_PARAMS_PATCHER)
    def test_initialize_score_case1(self):
        mock_score = MockScore()
        on_install = Mock()
        mock_score.on_install = on_install
        deploy_type = DeployType.INSTALL
        params = {"param1": '0x1', "param2": "string"}

        self._score_deploy_engine._initialize_score(deploy_type, mock_score, params)
        TypeConverter.make_annotations_from_method.assert_called_with(on_install)
        TypeConverter.convert_data_params.assert_called_with('annotations', params)
        on_install.assert_called_with(**params)

    # case on_update
    @patch_several(MAKE_ANNOTATIONS_FROM_METHOD_PATCHER, CONVERT_DATA_PARAMS_PATCHER)
    def test_initialize_score_case2(self):
        mock_score = MockScore()
        on_update = Mock()
        mock_score.on_update = on_update
        deploy_type = DeployType.UPDATE
        params = {"param1": '0x1', "param2": "string"}

        self._score_deploy_engine._initialize_score(deploy_type, mock_score, params)
        TypeConverter.make_annotations_from_method.assert_called_with(on_update)
        TypeConverter.convert_data_params.assert_called_with('annotations', params)
        on_update.assert_called_with(**params)

    # case strange method name
    @patch_several(MAKE_ANNOTATIONS_FROM_METHOD_PATCHER, CONVERT_DATA_PARAMS_PATCHER)
    def test_initialize_score_case3(self):
        mock_score = MockScore()
        on_strange = Mock()
        mock_score.on_install = on_strange
        deploy_type = "strange"
        params = {"param1": '0x1', "param2": "string"}

        with self.assertRaises(InvalidParamsException) as e:
            self._score_deploy_engine._initialize_score(deploy_type, mock_score, params)

        self.assertEqual(e.exception.code, ExceptionCode.INVALID_PARAMETER)
        self.assertEqual(e.exception.message, f"Invalid deployType: {deploy_type}")
        TypeConverter.make_annotations_from_method.assert_not_called()
        TypeConverter.convert_data_params.assert_not_called()
        on_strange.assert_not_called()

    @staticmethod
    def __ensure_dir(dir_path):
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)

