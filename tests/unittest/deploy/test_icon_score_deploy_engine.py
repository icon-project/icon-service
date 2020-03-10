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
from unittest.mock import Mock

import pytest

from iconservice.base.address import AddressPrefix, ZERO_SCORE_ADDRESS, GOVERNANCE_SCORE_ADDRESS, Address
from iconservice.base.block import Block
from iconservice.base.exception import InvalidParamsException, ExceptionCode
from iconservice.base.message import Message
from iconservice.base.transaction import Transaction
from iconservice.base.type_converter import TypeConverter
from iconservice.deploy import engine as isde
from iconservice.deploy.icon_score_deployer import IconScoreDeployer
from iconservice.deploy.storage import IconScoreDeployTXParams, IconScoreDeployInfo
from iconservice.icon_constant import DeployType
from iconservice.icon_constant import IconServiceFlag
from iconservice.iconscore.context.context import ContextContainer
from iconservice.iconscore.icon_score_context import IconScoreContext
from iconservice.iconscore.icon_score_context_util import IconScoreContextUtil
from iconservice.iconscore.icon_score_mapper import IconScoreMapper
from iconservice.icx import IcxEngine
from tests import create_address, create_tx_hash, create_block_hash


EOA1 = create_address(AddressPrefix.EOA)
EOA2 = create_address(AddressPrefix.EOA)
SCORE_ADDRESS = create_address(AddressPrefix.CONTRACT)


class MockScore(object):
    pass


@pytest.fixture(scope="function")
def context():
    ctx = Mock(spec=IconScoreContext)

    tx = Mock(spec=Transaction)
    tx.configure_mock(tx_hash=create_tx_hash(), origin=EOA1)
    ctx.attach_mock(tx, "tx")

    block = Mock(spec=Block)
    block.configure_mock(height=0, block_hash=create_block_hash(), timestamp=0,
                         prev_hash=None, cumulative_fee=0)
    ctx.attach_mock(block, "block")

    msg = Mock(spec=Message)
    msg.configure_mock(sender=EOA1, value=0)
    ctx.attach_mock(msg, "msg")

    icon_score_mapper = Mock(spec=IconScoreMapper)
    ctx.attach_mock(icon_score_mapper, "icon_score_mapper")

    ctx.attach_mock(Mock(spec=IcxEngine), "icx")
    ctx.new_icon_score_mapper = {}
    ctx.revision = 0

    ctx.attach_mock(Mock(spec=list), "event_logs")
    ctx.attach_mock(Mock(spec=list), "traces")
    ctx.attach_mock(Mock(spec=Address), "current_address")

    ContextContainer._push_context(ctx)
    yield ctx
    ContextContainer._pop_context()


def test_invoke(context, mocker):
    """case when icon_score_address is in (None, ZERO_ADDRESS)"""
    mocker.patch.object(IconScoreContextUtil, "validate_score_blacklist")
    mocker.patch.object(IconScoreContextUtil, "is_service_flag_on")
    mocker.patch.object(isde.Engine, "_is_audit_needed", return_value=True)
    mocker.patch.object(isde.Engine, "deploy")
    score_deploy_engine = isde.Engine()
    score_deploy_engine.deploy = Mock()

    score_deploy_engine.open()

    with pytest.raises(AssertionError):
        score_deploy_engine.invoke(context, GOVERNANCE_SCORE_ADDRESS, ZERO_SCORE_ADDRESS, {})
    IconScoreContextUtil.validate_score_blacklist.assert_not_called()
    context.storage.deploy.put_deploy_info_and_tx_params.assert_not_called()
    score_deploy_engine._is_audit_needed.assert_not_called()
    score_deploy_engine.deploy.assert_not_called()

    with pytest.raises(AssertionError):
        score_deploy_engine.invoke(context, GOVERNANCE_SCORE_ADDRESS, None, {})
    IconScoreContextUtil.validate_score_blacklist.assert_not_called()
    context.storage.deploy.put_deploy_info_and_tx_params.assert_not_called()
    score_deploy_engine._is_audit_needed.assert_not_called()
    score_deploy_engine.deploy.assert_not_called()


def test_is_audit_needed_case1(context, mocker):
    """case when revision0, owner, audit false"""
    mocker.patch.object(IconScoreContextUtil, "is_service_flag_on", return_value=False)
    mocker.patch.object(IconScoreContextUtil, "get_owner", return_value=EOA1)
    score_deploy_engine = isde.Engine()
    score_deploy_engine.open()

    result = score_deploy_engine._is_audit_needed(context, SCORE_ADDRESS)
    IconScoreContextUtil.get_owner.assert_called_with(context, SCORE_ADDRESS)
    IconScoreContextUtil.is_service_flag_on.assert_called_with(context, IconServiceFlag.AUDIT)
    assert result is False


def test_is_audit_needed_case2(context, mocker):
    """case when revision0, owner x, audit false"""
    mocker.patch.object(IconScoreContextUtil, "is_service_flag_on", return_value=False)
    mocker.patch.object(IconScoreContextUtil, "get_owner", return_value=EOA2)
    score_deploy_engine = isde.Engine()
    score_deploy_engine.open()

    result = score_deploy_engine._is_audit_needed(context, SCORE_ADDRESS)
    IconScoreContextUtil.get_owner.assert_called_with(context, SCORE_ADDRESS)
    IconScoreContextUtil.is_service_flag_on.assert_called_with(context, IconServiceFlag.AUDIT)
    assert result is False


def test_is_audit_needed_case3(context, mocker):
    """case when revision0, owner, audit true"""
    mocker.patch.object(IconScoreContextUtil, "is_service_flag_on", return_value=True)
    mocker.patch.object(IconScoreContextUtil, "get_owner", return_value=EOA1)
    score_deploy_engine = isde.Engine()
    score_deploy_engine.open()

    result = score_deploy_engine._is_audit_needed(context, SCORE_ADDRESS)
    IconScoreContextUtil.get_owner.assert_called_with(context, SCORE_ADDRESS)
    IconScoreContextUtil.is_service_flag_on.assert_called_with(context, IconServiceFlag.AUDIT)
    assert result is True


def test_is_audit_needed_case4(context, mocker):
    """case when revision0, owner x, audit true"""
    mocker.patch.object(IconScoreContextUtil, "is_service_flag_on", return_value=True)
    mocker.patch.object(IconScoreContextUtil, "get_owner", return_value=EOA2)
    score_deploy_engine = isde.Engine()
    score_deploy_engine.open()

    result = score_deploy_engine._is_audit_needed(context, SCORE_ADDRESS)
    IconScoreContextUtil.get_owner.assert_called_with(context, SCORE_ADDRESS)
    IconScoreContextUtil.is_service_flag_on.assert_called_with(context, IconServiceFlag.AUDIT)
    assert result is True


def test_is_audit_needed_case5(context, mocker):
    """case when revision2, transaction requested by owner, audit true, system_score"""
    context.revision = 2
    mocker.patch.object(IconScoreContextUtil, "is_service_flag_on", return_value=True)
    mocker.patch.object(IconScoreContextUtil, "get_owner", return_value=EOA1)
    score_deploy_engine = isde.Engine()
    score_deploy_engine.open()

    result = score_deploy_engine._is_audit_needed(context, GOVERNANCE_SCORE_ADDRESS)
    IconScoreContextUtil.get_owner.assert_called_with(context, GOVERNANCE_SCORE_ADDRESS)
    IconScoreContextUtil.is_service_flag_on.assert_called_with(context, IconServiceFlag.AUDIT)
    assert result is False


def test_is_audit_needed_case6(context, mocker):
    """case when revision2, transaction requested by stranger, audit true, system_score"""
    context.revision = 2
    mocker.patch.object(IconScoreContextUtil, "is_service_flag_on", return_value=True)
    mocker.patch.object(IconScoreContextUtil, "get_owner", return_value=EOA2)
    score_deploy_engine = isde.Engine()
    score_deploy_engine.open()

    result = score_deploy_engine._is_audit_needed(context, GOVERNANCE_SCORE_ADDRESS)
    IconScoreContextUtil.get_owner.assert_called_with(context, GOVERNANCE_SCORE_ADDRESS)
    IconScoreContextUtil.is_service_flag_on.assert_called_with(context, IconServiceFlag.AUDIT)
    assert result is True


def test_is_audit_needed_case7(context, mocker):
    """case when revision2, transaction requested by owner, audit false, system_score"""
    context.revision = 2
    mocker.patch.object(IconScoreContextUtil, "is_service_flag_on", return_value=False)
    mocker.patch.object(IconScoreContextUtil, "get_owner", return_value=EOA1)
    score_deploy_engine = isde.Engine()
    score_deploy_engine.open()

    result = score_deploy_engine._is_audit_needed(context, GOVERNANCE_SCORE_ADDRESS)
    IconScoreContextUtil.get_owner.assert_called_with(context, GOVERNANCE_SCORE_ADDRESS)
    IconScoreContextUtil.is_service_flag_on.assert_called_with(context, IconServiceFlag.AUDIT)
    assert result is False


def test_is_audit_needed_case8(context, mocker):
    """case when revision2, transaction requested by stranger, audit false, system_score"""
    context.revision = 2
    mocker.patch.object(IconScoreContextUtil, "is_service_flag_on", return_value=False)
    mocker.patch.object(IconScoreContextUtil, "get_owner", return_value=EOA1)
    score_deploy_engine = isde.Engine()
    score_deploy_engine.open()

    result = score_deploy_engine._is_audit_needed(context, GOVERNANCE_SCORE_ADDRESS)
    IconScoreContextUtil.get_owner.assert_called_with(context, GOVERNANCE_SCORE_ADDRESS)
    IconScoreContextUtil.is_service_flag_on.assert_called_with(context, IconServiceFlag.AUDIT)
    assert result is False


def test_is_audit_needed_case9(context, mocker):
    """case when revision2, transaction requested by owner, audit true, normal_score"""
    context.revision = 2
    mocker.patch.object(IconScoreContextUtil, "is_service_flag_on", return_value=True)
    mocker.patch.object(IconScoreContextUtil, "get_owner", return_value=EOA1)
    score_deploy_engine = isde.Engine()
    score_deploy_engine.open()

    result = score_deploy_engine._is_audit_needed(context, SCORE_ADDRESS)
    IconScoreContextUtil.get_owner.assert_called_with(context, SCORE_ADDRESS)
    IconScoreContextUtil.is_service_flag_on.assert_called_with(context, IconServiceFlag.AUDIT)
    assert result is True


def test_is_audit_needed_case10(context, mocker):
    """case when revision2, transaction requested by stranger, audit true, normal_score"""
    context.revision = 2
    mocker.patch.object(IconScoreContextUtil, "is_service_flag_on", return_value=True)
    mocker.patch.object(IconScoreContextUtil, "get_owner", return_value=EOA2)
    score_deploy_engine = isde.Engine()
    score_deploy_engine.open()

    result = score_deploy_engine._is_audit_needed(context, SCORE_ADDRESS)
    IconScoreContextUtil.get_owner.assert_called_with(context, SCORE_ADDRESS)
    IconScoreContextUtil.is_service_flag_on.assert_called_with(context, IconServiceFlag.AUDIT)
    assert result is True


def test_is_audit_needed_case11(context, mocker):
    """case when revision2, transaction requested by owner, audit false, normal_score"""
    context.revision = 2
    mocker.patch.object(IconScoreContextUtil, "is_service_flag_on", return_value=False)
    mocker.patch.object(IconScoreContextUtil, "get_owner", return_value=EOA1)
    score_deploy_engine = isde.Engine()
    score_deploy_engine.open()

    result = score_deploy_engine._is_audit_needed(context, GOVERNANCE_SCORE_ADDRESS)
    IconScoreContextUtil.get_owner.assert_called_with(context, GOVERNANCE_SCORE_ADDRESS)
    IconScoreContextUtil.is_service_flag_on.assert_called_with(context, IconServiceFlag.AUDIT)
    assert result is False


def test_is_audit_needed_case12(context, mocker):
    """case when revision2, transaction requested by stranger, audit false, normal_score"""
    context.revision = 2
    mocker.patch.object(IconScoreContextUtil, "is_service_flag_on", return_value=False)
    mocker.patch.object(IconScoreContextUtil, "get_owner", return_value=EOA1)
    score_deploy_engine = isde.Engine()
    score_deploy_engine.open()

    result = score_deploy_engine._is_audit_needed(context, GOVERNANCE_SCORE_ADDRESS)
    IconScoreContextUtil.get_owner.assert_called_with(context, GOVERNANCE_SCORE_ADDRESS)
    IconScoreContextUtil.is_service_flag_on.assert_called_with(context, IconServiceFlag.AUDIT)
    assert result is False


def test_deploy_case1(context):
    """case when tx_param is None"""
    score_deploy_engine = isde.Engine()
    score_deploy_engine.open()
    score_deploy_engine._score_deploy = Mock()
    context.storage.deploy.update_score_info = Mock()
    context.storage.deploy.get_deploy_tx_params = Mock(return_value=None)

    with pytest.raises(InvalidParamsException) as e:
        score_deploy_engine.deploy(context, context.tx.hash)

    context.storage.deploy.get_deploy_tx_params.assert_called_with(context, context.tx.hash)
    assert e.value.code == ExceptionCode.INVALID_PARAMETER
    score_deploy_engine._score_deploy.assert_not_called()
    context.storage.deploy.update_score_info.assert_not_called()


def test_deploy_case2(context):
    """case when tx_param is not None"""
    score_deploy_engine = isde.Engine()
    score_deploy_engine.open()
    tx_params = Mock(spec=IconScoreDeployTXParams)
    tx_params.configure_mock(score_address=GOVERNANCE_SCORE_ADDRESS)
    score_deploy_engine._score_deploy = Mock()
    context.storage.deploy.update_score_info = Mock()
    context.storage.deploy.get_deploy_tx_params = Mock(return_value=tx_params)

    score_deploy_engine.deploy(context, context.tx.hash)

    score_deploy_engine._score_deploy.assert_called_with(context, tx_params)
    context.storage.deploy. \
        update_score_info.assert_called_with(context, GOVERNANCE_SCORE_ADDRESS, context.tx.hash)


def test_score_deploy_case1(context):
    """test for tbears mode, legacy_tbears_mode is True"""
    score_deploy_engine = isde.Engine()
    score_deploy_engine.open()
    score_deploy_engine._on_deploy = Mock()
    context.legacy_tbears_mode = True
    tx_params = Mock(spec=IconScoreDeployTXParams)
    tx_params.configure_mock(deploy_data={'contentType': 'application/tbears', 'content': '0x1234'})

    score_deploy_engine._score_deploy(context, tx_params)

    score_deploy_engine._on_deploy.assert_called_with(context, tx_params)


def test_score_deploy_case2(context):
    """test for tbears mode, and legacy_tbears_mode is False"""
    score_deploy_engine = isde.Engine()
    score_deploy_engine.open()
    score_deploy_engine._on_deploy = Mock()
    score_deploy_engine._on_deploy = Mock()
    context.legacy_tbears_mode = False
    tx_params = Mock(spec=IconScoreDeployTXParams)
    tx_params.configure_mock(deploy_data={'contentType': 'application/tbears', 'content': '0x1234'})

    with pytest.raises(InvalidParamsException) as e:
        score_deploy_engine._score_deploy(context, tx_params)
    assert e.value.code == ExceptionCode.INVALID_PARAMETER
    assert e.value.message == "Invalid contentType: application/tbears"
    score_deploy_engine._on_deploy.assert_not_called()


def test_score_deploy_case3(context):
    """test for zip mode"""
    score_deploy_engine = isde.Engine()
    score_deploy_engine.open()
    score_deploy_engine._on_deploy = Mock()
    score_deploy_engine._on_deploy = Mock()
    context.legacy_tbears_mode = False
    tx_params = Mock(spec=IconScoreDeployTXParams)
    tx_params.configure_mock(deploy_data={'contentType': 'application/zip', 'content': '0x1234'})

    score_deploy_engine._score_deploy(context, tx_params)

    score_deploy_engine._on_deploy.assert_called_with(context, tx_params)


def test_score_deploy_case4(context):
    """test for wrong contentType"""
    score_deploy_engine = isde.Engine()
    score_deploy_engine.open()
    score_deploy_engine._on_deploy = Mock()
    score_deploy_engine._on_deploy = Mock()
    context.legacy_tbears_mode = False
    tx_params = Mock(spec=IconScoreDeployTXParams)
    tx_params.configure_mock(deploy_data={'contentType': 'wrong/content', 'content': '0x1234'})

    with pytest.raises(InvalidParamsException) as e:
        score_deploy_engine._score_deploy(context, tx_params)
    assert e.value.code == ExceptionCode.INVALID_PARAMETER
    assert e.value.message == 'Invalid contentType: wrong/content'
    score_deploy_engine._on_deploy.assert_not_called()


def test_write_score_to_filesystem_case1(context):
    """tbears mode"""
    score_deploy_engine = isde.Engine()
    score_deploy_engine.open()
    content = '0x1234'
    deploy_data = {'contentType': 'application/tbears', 'content': content}
    score_deploy_engine._write_score_to_score_deploy_path_on_tbears_mode = Mock()

    score_deploy_engine._write_score_to_filesystem(context, GOVERNANCE_SCORE_ADDRESS, context.tx.hash, deploy_data)
    score_deploy_engine._write_score_to_score_deploy_path_on_tbears_mode.\
        assert_called_with(context, GOVERNANCE_SCORE_ADDRESS, context.tx.hash, content)


def test_write_score_to_filesystem_case2(context):
    """normal mode"""
    score_deploy_engine = isde.Engine()
    score_deploy_engine.open()
    content = '0x1234'
    deploy_data = {'contentType': 'application/zip', 'content': content}
    score_deploy_engine._write_score_to_score_deploy_path = Mock()

    score_deploy_engine._write_score_to_filesystem(context, GOVERNANCE_SCORE_ADDRESS, context.tx.hash, deploy_data)
    score_deploy_engine._write_score_to_score_deploy_path. \
        assert_called_with(context, GOVERNANCE_SCORE_ADDRESS, context.tx.hash, content)


def test_create_score_info_case1(context, mocker):
    """case when current_score_info is None"""
    score_deploy_engine = isde.Engine()
    score_deploy_engine.open()
    mocker.patch.object(IconScoreContextUtil, "get_score_info", return_value=None)
    mocker.patch.object(IconScoreContextUtil, "create_score_info")

    score_deploy_engine._create_score_info(context, GOVERNANCE_SCORE_ADDRESS, context.tx.hash)
    IconScoreContextUtil.create_score_info.assert_called_with(context, GOVERNANCE_SCORE_ADDRESS, context.tx.hash, None)


def test_create_score_info_case2(context, mocker):
    """case when current_score_info is not None"""
    db = 'db'
    score_deploy_engine = isde.Engine()
    score_deploy_engine.open()
    mocker.patch.object(IconScoreContextUtil, "get_score_info", return_value=None)
    mocker.patch.object(IconScoreContextUtil, "create_score_info")
    score_info_mock = Mock()
    score_info_mock.configure_mock(score_db=db)
    IconScoreContextUtil.get_score_info.return_value = score_info_mock

    score_deploy_engine._create_score_info(context, GOVERNANCE_SCORE_ADDRESS, context.tx.hash)
    IconScoreContextUtil.create_score_info.assert_called_with(context, GOVERNANCE_SCORE_ADDRESS, context.tx.hash, db)


def test_write_score_to_score_deploy_path_on_tbears_mode(context, mocker):
    score_deploy_path = 'score_deploy_path'
    score_path = 'score_path'
    score_deploy_engine = isde.Engine()
    score_deploy_engine.open()
    mocker.patch("iconservice.deploy.engine.get_score_deploy_path", return_value=score_deploy_path)
    mocker.patch("iconservice.deploy.engine.get_score_path", return_value=score_path)
    mocker.patch.object(os, "symlink")
    mocker.patch.object(os, "makedirs")

    score_deploy_engine._write_score_to_score_deploy_path_on_tbears_mode(context, GOVERNANCE_SCORE_ADDRESS,
                                                                         context.tx.hash, None)

    isde.get_score_path.assert_called_with(context.score_root_path, GOVERNANCE_SCORE_ADDRESS)
    os.makedirs.assert_called_with(score_path, exist_ok=True)
    os.symlink.assert_called_with(None, score_deploy_path, target_is_directory=True)


def test_write_score_to_score_deploy_path_case1(context, mocker):
    """case when revision3"""
    score_deploy_engine = isde.Engine()
    score_deploy_engine.open()
    score_path = 'score_path'
    score_deploy_path = 'score_deploy_path'
    mocker.patch.object(IconScoreDeployer, "deploy")
    mocker.patch("iconservice.deploy.engine.remove_path")
    mocker.patch("iconservice.deploy.engine.get_score_deploy_path", return_value=score_deploy_path)
    mocker.patch.object(os.path, "join", return_value=score_path)
    context.revision = 3
    isde.get_score_deploy_path.return_value = 'score_deploy_path'

    score_deploy_engine._write_score_to_score_deploy_path(context, GOVERNANCE_SCORE_ADDRESS, context.tx.hash, None)

    isde.get_score_deploy_path.assert_called_with(context.score_root_path, GOVERNANCE_SCORE_ADDRESS, context.tx.hash)
    os.path.join.assert_called_with(context.score_root_path, GOVERNANCE_SCORE_ADDRESS.to_bytes().hex(),
                                    f"0x{context.tx.hash.hex()}")
    isde.remove_path.assert_called_with(score_path)
    IconScoreDeployer.deploy.assert_called_with(score_deploy_path, None, 3)


def test_write_score_to_score_deploy_path_case2(context, mocker):
    """case when revision2"""
    score_deploy_engine = isde.Engine()
    score_deploy_engine.open()
    score_path = 'score_path'
    score_deploy_path = 'score_deploy_path'
    mocker.patch.object(IconScoreDeployer, "deploy")
    mocker.patch("iconservice.deploy.engine.remove_path")
    mocker.patch("iconservice.deploy.engine.get_score_deploy_path", return_value=score_deploy_path)
    mocker.patch.object(os.path, "join", return_value=score_path)
    context.revision = 2
    score_deploy_engine._write_score_to_score_deploy_path(context, GOVERNANCE_SCORE_ADDRESS, context.tx.hash, None)

    isde.get_score_deploy_path.assert_called_with(context.score_root_path, GOVERNANCE_SCORE_ADDRESS, context.tx.hash)
    os.path.join.assert_not_called()
    isde.remove_path.assert_not_called()
    IconScoreDeployer.deploy.assert_called_with(score_deploy_path, None, 2)


def test_write_score_to_score_deploy_path_case3(context, mocker):
    """case when revision0"""
    score_deploy_engine = isde.Engine()
    score_deploy_engine.open()
    score_path = 'score_path'
    score_deploy_path = 'score_deploy_path'
    isde.get_score_deploy_path.return_value = 'score_deploy_path'
    mocker.patch.object(IconScoreDeployer, "deploy")
    mocker.patch.object(IconScoreDeployer, "deploy_legacy")
    mocker.patch("iconservice.deploy.engine.remove_path")
    mocker.patch("iconservice.deploy.engine.get_score_deploy_path", return_value=score_deploy_path)
    mocker.patch.object(os.path, "join", return_value=score_path)
    score_deploy_engine._write_score_to_score_deploy_path(context, GOVERNANCE_SCORE_ADDRESS, context.tx.hash, None)

    isde.get_score_deploy_path.assert_called_with(context.score_root_path, GOVERNANCE_SCORE_ADDRESS, context.tx.hash)
    os.path.join.assert_not_called()
    isde.remove_path.assert_not_called()
    IconScoreDeployer.deploy.assert_not_called()
    IconScoreDeployer.deploy_legacy.assert_called_with(score_deploy_path, None)


def test_initialize_score_case1(mocker):
    """case on_install"""
    score_deploy_engine = isde.Engine()
    score_deploy_engine.open()
    mocker.patch.object(TypeConverter, "make_annotations_from_method", return_value="annotations")
    mocker.patch.object(TypeConverter, "convert_data_params")
    mock_score = MockScore()
    on_install = Mock()
    mock_score.on_install = on_install
    deploy_type = DeployType.INSTALL
    params = {"param1": '0x1', "param2": "string"}

    score_deploy_engine._initialize_score(deploy_type, mock_score, params)
    TypeConverter.make_annotations_from_method.assert_called_with(on_install)
    TypeConverter.convert_data_params.assert_called_with('annotations', params)
    on_install.assert_called_with(**params)


def test_initialize_score_case2(mocker):
    """case on_update"""
    score_deploy_engine = isde.Engine()
    score_deploy_engine.open()
    mocker.patch.object(TypeConverter, "make_annotations_from_method", return_value="annotations")
    mocker.patch.object(TypeConverter, "convert_data_params")
    mock_score = MockScore()
    on_update = Mock()
    mock_score.on_update = on_update
    deploy_type = DeployType.UPDATE
    params = {"param1": '0x1', "param2": "string"}

    score_deploy_engine._initialize_score(deploy_type, mock_score, params)
    TypeConverter.make_annotations_from_method.assert_called_with(on_update)
    TypeConverter.convert_data_params.assert_called_with('annotations', params)
    on_update.assert_called_with(**params)


def test_initialize_score_case3(mocker):
    """case strange method name"""
    score_deploy_engine = isde.Engine()
    score_deploy_engine.open()
    mocker.patch.object(TypeConverter, "make_annotations_from_method", return_value="annotations")
    mocker.patch.object(TypeConverter, "convert_data_params")
    mock_score = MockScore()
    on_strange = Mock()
    mock_score.on_install = on_strange
    deploy_type = "strange"
    params = {"param1": '0x1', "param2": "string"}

    with pytest.raises(InvalidParamsException) as e:
        score_deploy_engine._initialize_score(deploy_type, mock_score, params)

    assert e.value.code == ExceptionCode.INVALID_PARAMETER
    assert e.value.message == f"Invalid deployType: {deploy_type}"
    TypeConverter.make_annotations_from_method.assert_not_called()
    TypeConverter.convert_data_params.assert_not_called()
    on_strange.assert_not_called()


def test_on_deploy(context, mocker):
    """Case when deploy_info is not None, zip, revision0, score validator flag False, SCORE is not None"""
    score_deploy_engine = isde.Engine()
    score_deploy_engine.open()
    mocker.patch.object(IconScoreContextUtil, 'validate_score_package')
    mock_score = MockScore()
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

    score_deploy_engine._write_score_to_filesystem = Mock()
    score_info = Mock()
    score_info.configure_mock(get_score=Mock(return_value=mock_score))
    score_deploy_engine._create_score_info = Mock(return_value=score_info)
    context.storage.deploy.get_deploy_info = Mock(return_value=deploy_info)
    score_deploy_engine._initialize_score = Mock()

    score_deploy_engine._on_deploy(context, tx_params)

    context.storage.deploy.get_deploy_info.assert_called_with(context, SCORE_ADDRESS)
    score_deploy_engine._write_score_to_filesystem.assert_called_with(context, SCORE_ADDRESS, next_tx_hash, deploy_data)
    IconScoreContextUtil.validate_score_package.assert_called_with(context, SCORE_ADDRESS,
                                                                   next_tx_hash)
    score_deploy_engine._create_score_info.assert_called_with(context, SCORE_ADDRESS, next_tx_hash)
    score_info.get_score.assert_called_with(context.revision)
    score_deploy_engine._initialize_score.assert_called_with(deploy_type, mock_score, deploy_params)

    assert context.msg == backup_msg
    assert context.tx == backup_tx
