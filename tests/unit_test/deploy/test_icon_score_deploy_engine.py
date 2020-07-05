# -*- coding: utf-8 -*-
# Copyright 2020 ICON Foundation
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
from typing import Optional
from unittest.mock import Mock, PropertyMock, call

import pytest

from iconservice.base.address import AddressPrefix, GOVERNANCE_SCORE_ADDRESS, Address, \
    SYSTEM_SCORE_ADDRESS
from iconservice.base.block import Block
from iconservice.base.exception import InvalidParamsException, ExceptionCode
from iconservice.base.message import Message
from iconservice.base.transaction import Transaction
from iconservice.base.type_converter import TypeConverter
from iconservice.deploy import engine as isde
from iconservice.deploy.icon_score_deployer import IconScoreDeployer
from iconservice.deploy.storage import IconScoreDeployTXParams, IconScoreDeployInfo, Storage
from iconservice.icon_constant import DeployType, IconScoreContextType, Revision
from iconservice.icon_constant import IconServiceFlag
from iconservice.iconscore.context.context import ContextContainer
from iconservice.iconscore.icon_score_context import IconScoreContext
from iconservice.iconscore.icon_score_context_util import IconScoreContextUtil
from iconservice.iconscore.icon_score_mapper import IconScoreMapper
from iconservice.iconscore.icon_score_step import IconScoreStepCounter, StepType
from iconservice.utils import ContextStorage
from tests import create_address, create_tx_hash, create_block_hash

EOA1 = create_address(AddressPrefix.EOA)
EOA2 = create_address(AddressPrefix.EOA)
SCORE_ADDRESS = create_address(AddressPrefix.CONTRACT)


@pytest.fixture(scope="module")
def mock_engine():
    engine = isde.Engine()
    return engine


@pytest.fixture(scope="function")
def context():
    ctx = IconScoreContext(IconScoreContextType.DIRECT)
    ctx.tx = Transaction(tx_hash=create_tx_hash(), origin=EOA1)
    ctx.block = Block(block_height=0, block_hash=create_block_hash(), timestamp=0, prev_hash=None)
    ctx.msg = Message(sender=EOA1, value=0)
    ctx.icon_score_mapper = IconScoreMapper()
    ctx.new_icon_score_mapper = {}
    ctx.step_counter = IconScoreStepCounter(1, {}, 1000, False)
    ctx.event_logs = []
    ctx.traces = []
    ctx.current_address = EOA1
    IconScoreContext.storage = ContextStorage(deploy=Mock(spec=Storage), fee=None, icx=None, iiss=None, prep=None,
                                              issue=None, meta=None, rc=None, inv=None)

    ContextContainer._push_context(ctx)
    yield ctx
    ContextContainer._pop_context()


@pytest.mark.parametrize("data",
                         [{"contentType": "application/tbears", "content": "path"}, {}])
def test_invoke_install(context, mock_engine, mocker, data):
    new_score_address = create_address(1)
    mocker.patch.object(isde, "generate_score_address_for_tbears", return_value=new_score_address)
    mocker.patch.object(isde, "generate_score_address", return_value=new_score_address)
    mocker.patch.object(IconScoreContextUtil, "get_deploy_info", return_value=None)
    mocker.patch.object(IconScoreStepCounter, "apply_step")
    mocker.patch.object(isde.Engine, "_invoke")
    expected_apply_step_args_list = list()
    expected_apply_step_args_list.append(call(StepType.CONTRACT_CREATE, 1))
    content_size = len(data.get("content", ""))
    expected_apply_step_args_list.append(call(StepType.CONTRACT_SET, content_size))

    ret = mock_engine.invoke(context, SYSTEM_SCORE_ADDRESS, data)

    if data.get("contentType") == "application/tbears":
        isde.generate_score_address_for_tbears.assert_called_with("path")
    else:
        isde.generate_score_address.assert_called_with(context.tx.origin, context.tx.timestamp, context.tx.nonce)
    IconScoreContextUtil.get_deploy_info.assert_called_with(context, new_score_address)
    apply_step_args_list = IconScoreStepCounter.apply_step.call_args_list
    assert expected_apply_step_args_list == apply_step_args_list
    mock_engine._invoke.assert_called_with(context=context, to=SYSTEM_SCORE_ADDRESS,
                                           icon_score_address=new_score_address, data=data)
    assert ret == new_score_address

    mocker.stopall()


def test_invoke_update(context, mock_engine, mocker):
    score_address = create_address(1)
    data = {}
    mocker.patch.object(isde.Engine, "_invoke")
    mocker.patch.object(IconScoreStepCounter, "apply_step")
    expected_apply_step_args_list = list()
    expected_apply_step_args_list.append(call(StepType.CONTRACT_UPDATE, 1))
    content_size = len(data.get("content", ""))
    expected_apply_step_args_list.append(call(StepType.CONTRACT_SET, content_size))

    ret = mock_engine.invoke(context, score_address, data)

    assert expected_apply_step_args_list == IconScoreStepCounter.apply_step.call_args_list
    mock_engine._invoke.assert_called_with(context=context, to=score_address,
                                           icon_score_address=score_address, data=data)
    assert ret == score_address
    mocker.stopall()


@pytest.mark.parametrize("to,score_address,expect",
                         [(SYSTEM_SCORE_ADDRESS, SYSTEM_SCORE_ADDRESS, pytest.raises(AssertionError)),
                          (SYSTEM_SCORE_ADDRESS, None, pytest.raises(AssertionError))])
def test_invoke_invalid_score_addresses(context, mock_engine, mocker, to, score_address, expect):
    """case when icon_score_address is in (None, ZERO_ADDRESS)"""
    mocker.patch.object(isde.Engine, "_is_audit_needed", return_value=True)
    mocker.patch.object(isde.Engine, "deploy")

    with expect:
        mock_engine._invoke(context, to, score_address, {})
    context.storage.deploy.put_deploy_info_and_tx_params.assert_not_called()
    mock_engine._is_audit_needed.assert_not_called()
    mock_engine.deploy.assert_not_called()
    mocker.stopall()


@pytest.mark.parametrize("to,score_address,deploy_type",
                         [(SYSTEM_SCORE_ADDRESS, GOVERNANCE_SCORE_ADDRESS, DeployType.INSTALL),
                          (GOVERNANCE_SCORE_ADDRESS, GOVERNANCE_SCORE_ADDRESS, DeployType.UPDATE)])
def test_invoke_valid_score_addresses(context, mock_engine, mocker, to, score_address, deploy_type):
    """case when icon_score_address is not in (None, ZERO_ADDRESS)"""
    mocker.patch.object(isde.Engine, "_is_audit_needed", return_value=False)
    mocker.patch.object(isde.Engine, "deploy")

    mock_engine._invoke(context, to, score_address, {})
    context.storage.deploy.put_deploy_info_and_tx_params.assert_called_with(context, score_address, deploy_type,
                                                                            context.tx.origin, context.tx.hash, {})
    mock_engine._is_audit_needed.assert_called_with(context, score_address)
    mock_engine.deploy.assert_called_with(context, context.tx.hash)
    mocker.stopall()


@pytest.mark.parametrize("deploy_data, call_method",
                         [
                             ({"contentType": "application/tbears", 'content': '0x1234'},
                              "_write_score_to_score_deploy_path_on_tbears_mode"),
                             ({"contentType": "application/zip", 'content': '0x1234'},
                              "_write_score_to_score_deploy_path"),
                         ])
def test_write_score_to_filesystem(mock_engine, context, mocker, deploy_data, call_method):
    """tbears mode"""
    content = '0x1234'
    mocker.patch.object(isde.Engine, call_method)

    mock_engine._write_score_to_filesystem(context, GOVERNANCE_SCORE_ADDRESS, context.tx.hash, deploy_data)
    method = getattr(mock_engine, call_method)
    method.assert_called_with(context, GOVERNANCE_SCORE_ADDRESS, context.tx.hash, content)
    mocker.stopall()


@pytest.mark.parametrize("get_score_info_return_value", [None, 'dummy'])
def test_create_score_info(mock_engine, context, mocker, get_score_info_return_value):
    """case when current_score_info is None"""
    score_info = None if get_score_info_return_value is None else Mock(score_db=get_score_info_return_value)
    mocker.patch.object(IconScoreContextUtil, "create_score_info")
    mocker.patch.object(IconScoreContextUtil, "get_score_info", return_value=score_info)

    mock_engine._create_score_info(context, GOVERNANCE_SCORE_ADDRESS, context.tx.hash)
    IconScoreContextUtil.create_score_info. \
        assert_called_with(context, GOVERNANCE_SCORE_ADDRESS, context.tx.hash, get_score_info_return_value)
    mocker.stopall()


def test_write_score_to_score_deploy_path_on_tbears_mode(mock_engine, context, mocker):
    score_deploy_path = 'score_deploy_path'
    score_path = 'score_path'
    mocker.patch("iconservice.deploy.engine.get_score_deploy_path", return_value=score_deploy_path)
    mocker.patch("iconservice.deploy.engine.get_score_path", return_value=score_path)
    mocker.patch.object(os, "symlink")
    mocker.patch.object(os, "makedirs")

    mock_engine._write_score_to_score_deploy_path_on_tbears_mode(context, GOVERNANCE_SCORE_ADDRESS,
                                                                         context.tx.hash, None)

    isde.get_score_path.assert_called_with(context.score_root_path, GOVERNANCE_SCORE_ADDRESS)
    os.makedirs.assert_called_with(score_path, exist_ok=True)
    os.symlink.assert_called_with(None, score_deploy_path, target_is_directory=True)
    mocker.stopall()


def test_on_deploy(mock_engine, context, mocker):
    """Case when deploy_info is not None, zip, revision0, score validator flag False, SCORE is not None"""
    mocker.patch.object(IconScoreContextUtil, 'validate_score_package')
    mock_score = Mock()
    mock_score.owner = EOA1
    deploy_params = {"a": 1}
    deploy_data = {"params": deploy_params}
    deploy_info = Mock(spec=IconScoreDeployInfo)
    deploy_type = 'deploy_type'
    next_tx_hash = b'\00\01' * 16
    deploy_info.configure_mock(next_tx_hash=next_tx_hash)
    tx_params = Mock(spec=IconScoreDeployTXParams)
    tx_params.configure_mock(score_address=SCORE_ADDRESS, deploy_data=deploy_data, deploy_type=deploy_type,
                             params=deploy_params)

    backup_msg, backup_tx = context.msg, context.tx

    mocker.patch.object(mock_engine, "_write_score_to_filesystem")
    score_info = Mock()
    score_info.configure_mock(get_score=Mock(return_value=mock_score))
    mocker.patch.object(mock_engine, "_create_score_info", return_value=score_info)
    context.storage.deploy.get_deploy_info = Mock(return_value=deploy_info)
    mocker.patch.object(mock_engine, "_initialize_score")

    mock_engine._on_deploy(context, tx_params)

    context.storage.deploy.get_deploy_info.assert_called_with(context, SCORE_ADDRESS)
    mock_engine._write_score_to_filesystem.assert_called_with(context, SCORE_ADDRESS, next_tx_hash, deploy_data)
    IconScoreContextUtil.validate_score_package.assert_called_with(context, SCORE_ADDRESS,
                                                                   next_tx_hash)
    mock_engine._create_score_info.assert_called_with(context, SCORE_ADDRESS, next_tx_hash)
    score_info.get_score.assert_called_with(context.revision)
    mock_engine._initialize_score.assert_called_with(deploy_type, mock_score, deploy_params)

    assert context.msg == backup_msg
    assert context.tx == backup_tx
    mocker.stopall()


class TestIsAuditNeeded:
    @staticmethod
    def set_test(mocker, is_service_flag_one_return_value: bool, get_owner_return_value: Address, revision: int):
        mocker.patch.object(IconScoreContextUtil, "is_service_flag_on", return_value=is_service_flag_one_return_value)
        mocker.patch.object(IconScoreContextUtil, "get_owner", return_value=get_owner_return_value)
        mocker.patch.object(IconScoreContext, "revision", PropertyMock(return_value=revision))

    @pytest.mark.parametrize("audit_flag", [True, False])
    def test_is_audit_needed_case_revision0(self, mock_engine, context, mocker, audit_flag):
        """case when revision0, owner, audit false"""
        self.set_test(mocker, audit_flag, EOA1, 0)

        result = mock_engine._is_audit_needed(context, SCORE_ADDRESS)
        IconScoreContextUtil.get_owner.assert_called_with(context, SCORE_ADDRESS)
        IconScoreContextUtil.is_service_flag_on.assert_called_with(context, IconServiceFlag.AUDIT)
        assert result is audit_flag
        mocker.stopall()

    @pytest.mark.parametrize("owner", [EOA1, EOA2])
    @pytest.mark.parametrize("score_address", [SCORE_ADDRESS, GOVERNANCE_SCORE_ADDRESS])
    @pytest.mark.parametrize("audit_flag", [True, False])
    @pytest.mark.parametrize("revision", [revision.value for revision in Revision if revision.value >= 2])
    def test_is_audit_needed_case_revision_gt2(self, mock_engine, context, mocker,
                                               audit_flag, owner, score_address, revision):
        """
        case when revision >= 2
        tx sender = EOA1
        """
        self.set_test(mocker, audit_flag, owner, revision)
        is_owner = owner == EOA1
        is_system_score = score_address == GOVERNANCE_SCORE_ADDRESS

        result = mock_engine._is_audit_needed(context, score_address)
        IconScoreContextUtil.get_owner.assert_called_with(context, score_address)
        IconScoreContextUtil.is_service_flag_on.assert_called_with(context, IconServiceFlag.AUDIT)
        assert result is (audit_flag and not (is_system_score and is_owner))
        mocker.stopall()


class TestDeploy:
    @staticmethod
    def set_test(mocker, get_deploy_tx_param_return_value: Optional[IconScoreDeployTXParams]):
        mocker.patch.object(isde.Engine, "_score_deploy")
        mocker.patch.object(IconScoreContext.storage.deploy, "update_score_info")
        mocker.patch.object(IconScoreContext.storage.deploy, "get_deploy_tx_params",
                            return_value=get_deploy_tx_param_return_value)

    def test_deploy_case_tx_param_none(self, mock_engine, context, mocker):
        """case when tx_param is None"""
        self.set_test(mocker, get_deploy_tx_param_return_value=None)

        with pytest.raises(InvalidParamsException) as e:
            mock_engine.deploy(context, context.tx.hash)

        context.storage.deploy.get_deploy_tx_params.assert_called_with(context, context.tx.hash)
        assert e.value.code == ExceptionCode.INVALID_PARAMETER
        mock_engine._score_deploy.assert_not_called()
        context.storage.deploy.update_score_info.assert_not_called()
        mocker.stopall()

    def test_deploy_case_tx_param_not_none(self, mock_engine, context, mocker):
        """case when tx_param is not None"""
        tx_params = Mock(spec=IconScoreDeployTXParams)
        tx_params.configure_mock(score_address=GOVERNANCE_SCORE_ADDRESS)
        self.set_test(mocker, get_deploy_tx_param_return_value=tx_params)

        mock_engine.deploy(context, context.tx.hash)

        mock_engine._score_deploy.assert_called_with(context, tx_params)
        context.storage.deploy. \
            update_score_info.assert_called_with(context, GOVERNANCE_SCORE_ADDRESS, context.tx.hash)
        mocker.stopall()


class TestScoreDeploy:
    content = f"0x{b'content'.hex()}"

    @staticmethod
    def set_test(mocker, mock_engine):
        mocker.patch.object(mock_engine, "_on_deploy")

    @pytest.mark.parametrize("tbears_mode", [True, False])
    def test_score_deploy_tbears_mode(self, mock_engine, context, mocker, tbears_mode):
        context.legacy_tbears_mode = tbears_mode

        if tbears_mode:
            deploy_data = {'contentType': 'application/tbears', 'content': self.content}
        else:
            deploy_data = {'contentType': 'application/zip', 'content': self.content}

        tx_params = Mock(spec=IconScoreDeployTXParams)
        tx_params.configure_mock(deploy_data=deploy_data)

        self.set_test(mocker, mock_engine)

        mock_engine._score_deploy(context, tx_params)
        mock_engine._on_deploy.assert_called_with(context, tx_params)
        mocker.stopall()

    @pytest.mark.parametrize("content_type", [
        "application/tbears",
        "wrong/content"
    ])
    def test_score_deploy_invalid_content_type(self, mock_engine, context, mocker, content_type):
        context.legacy_tbears_mode = False

        tx_params = Mock(spec=IconScoreDeployTXParams)
        tx_params.configure_mock(deploy_data={'contentType': content_type, 'content': self.content})

        self.set_test(mocker, mock_engine)

        with pytest.raises(InvalidParamsException) as e:
            mock_engine._score_deploy(context, tx_params)
        assert e.value.code == ExceptionCode.INVALID_PARAMETER
        assert e.value.message == f"Invalid contentType: {content_type}"
        mock_engine._on_deploy.assert_not_called()
        mocker.stopall()


class TestWriteScoreToScoreDeployPath:
    score_path = "score_path"
    score_deploy_path = "score_deploy_path"

    @staticmethod
    def set_test(mocker, score_path: str, score_deploy_path: str, revision: int):
        mocker.patch.object(IconScoreDeployer, "deploy")
        mocker.patch.object(IconScoreDeployer, "deploy_legacy")
        mocker.patch("iconservice.deploy.engine.remove_path")
        mocker.patch("iconservice.deploy.engine.get_score_deploy_path", return_value=score_deploy_path)
        mocker.patch.object(os.path, "join", return_value=score_path)
        mocker.patch.object(IconScoreContext, "revision", PropertyMock(return_value=revision))

    @pytest.mark.parametrize('revision', [revision.value for revision in Revision if revision.value >= 3])
    def test_write_score_to_score_deploy_path_revision_ge3(self, mock_engine, context, mocker, revision):
        self.set_test(mocker, self.score_path, self.score_deploy_path, revision)

        mock_engine._write_score_to_score_deploy_path(context, GOVERNANCE_SCORE_ADDRESS, context.tx.hash, None)

        isde.get_score_deploy_path.assert_called_with(context.score_root_path, GOVERNANCE_SCORE_ADDRESS,
                                                      context.tx.hash)
        os.path.join.assert_called_with(context.score_root_path, GOVERNANCE_SCORE_ADDRESS.to_bytes().hex(),
                                        f"0x{context.tx.hash.hex()}")
        isde.remove_path.assert_called_with(self.score_path)
        IconScoreDeployer.deploy.assert_called_with(self.score_deploy_path, None, revision)
        mocker.stopall()

    def test_write_score_to_score_deploy_path_revision_2(self, mock_engine, context, mocker):
        self.set_test(mocker, self.score_path, self.score_deploy_path, 2)

        mock_engine._write_score_to_score_deploy_path(context, GOVERNANCE_SCORE_ADDRESS, context.tx.hash, None)

        isde.get_score_deploy_path.assert_called_with(context.score_root_path,
                                                      GOVERNANCE_SCORE_ADDRESS, context.tx.hash)
        os.path.join.assert_not_called()
        isde.remove_path.assert_not_called()
        IconScoreDeployer.deploy.assert_called_with(self.score_deploy_path, None, 2)
        mocker.stopall()

    @pytest.mark.parametrize('revision', [revision.value for revision in Revision if 0 <= revision.value < 2])
    def test_write_score_to_score_deploy_path_revision_lt2(self, mock_engine, context, mocker, revision):
        """case when revision < 2"""
        self.set_test(mocker, self.score_path, self.score_deploy_path, revision)

        mock_engine._write_score_to_score_deploy_path(context, GOVERNANCE_SCORE_ADDRESS, context.tx.hash, None)

        isde.get_score_deploy_path.assert_called_with(context.score_root_path,
                                                      GOVERNANCE_SCORE_ADDRESS, context.tx.hash)
        os.path.join.assert_not_called()
        isde.remove_path.assert_not_called()
        IconScoreDeployer.deploy.assert_not_called()
        IconScoreDeployer.deploy_legacy.assert_called_with(self.score_deploy_path, None)
        mocker.stopall()


class TestInitializeScore:
    mock_score = Mock()
    on_install = None
    on_update = None
    on_invalid = None
    params = {"param1": "0x1", "param2": "string"}

    def set_test(self, mocker):
        mocker.patch.object(TypeConverter, "adjust_params_to_method")
        self.mock_score.on_install = self.on_install = Mock()
        self.mock_score.on_update = self.on_update = Mock()
        self.mock_score.on_invalid = self.on_invalid = Mock()

    @pytest.mark.skip("TypeConverter is replaced with convert_score_parameters()")
    def test_initialize_score_on_install(self, mock_engine, mocker):
        """case on_install"""
        deploy_type = DeployType.INSTALL

        self.set_test(mocker)

        mock_engine._initialize_score(deploy_type, self.mock_score, self.params)
        TypeConverter.adjust_params_to_method.assert_called_with(self.on_install, self.params)
        self.on_install.assert_called_with(**self.params)
        self.on_update.assert_not_called()
        self.on_invalid.assert_not_called()
        mocker.stopall()

    @pytest.mark.skip("TypeConverter is replaced with convert_score_parameters()")
    def test_initialize_score_case_on_update(self, mock_engine, mocker):
        """case on_update"""
        deploy_type = DeployType.UPDATE

        self.set_test(mocker)

        mock_engine._initialize_score(deploy_type, self.mock_score, self.params)
        TypeConverter.adjust_params_to_method.assert_called_with(self.on_update, self.params)
        self.on_install.assert_not_called()
        self.on_update.assert_called_with(**self.params)
        self.on_invalid.assert_not_called()
        mocker.stopall()

    def test_initialize_score_invalid(self, mock_engine, mocker):
        """case invalid method name"""
        deploy_type = 'invalid'

        self.set_test(mocker)

        with pytest.raises(InvalidParamsException) as e:
            mock_engine._initialize_score(deploy_type, self.mock_score, self.params)

        assert e.value.code == ExceptionCode.INVALID_PARAMETER
        assert e.value.message == f"Invalid deployType: {deploy_type}"
        TypeConverter.adjust_params_to_method.assert_not_called()
        self.on_install.assert_not_called()
        self.on_update.assert_not_called()
        self.on_invalid.assert_not_called()
        mocker.stopall()

