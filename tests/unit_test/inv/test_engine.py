# -*- coding: utf-8 -*-

# Copyright 2019 ICON Foundation
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

from unittest.mock import Mock

import pytest

from iconservice.base.address import GOVERNANCE_SCORE_ADDRESS
from iconservice.iconscore.icon_score_context import IconScoreContext
from iconservice.iconscore.icon_score_result import TransactionResult
from iconservice.inv import INVContainer, INVStorage, INVEngine
from iconservice.inv.data.value import *
from iconservice.utils import ContextStorage
from tests import create_address

DUMMY_ADDRESS_FOR_TEST = create_address()


@pytest.fixture(scope="module")
def dummy_invs():
    dummy_revision_code = 1
    dummy_revision_name = "1.1.1"
    dummy_service_config: int = 0
    dummy_step_costs = {
        'default': 0,
        'contractCall': 0
    }
    dummy_step_costs = {StepType(key): val for key, val in dummy_step_costs.items()}
    dummy_max_step_limits: dict = {
        IconScoreContextType.INVOKE: 2_500_000_000,
        IconScoreContextType.QUERY: 50_000_000
    }
    dummy_step_price: int = 0
    dummy_score_black_list: list = []
    dummy_import_white_list = {"iconservice": ['*']}
    dummy_invs = {
        IconNetworkValueType.REVISION_CODE: RevisionCode(dummy_revision_code),
        IconNetworkValueType.REVISION_NAME: RevisionName(dummy_revision_name),
        IconNetworkValueType.SCORE_BLACK_LIST: ScoreBlackList(dummy_score_black_list),
        IconNetworkValueType.STEP_PRICE: StepPrice(dummy_step_price),
        IconNetworkValueType.STEP_COSTS: StepCosts(dummy_step_costs),
        IconNetworkValueType.MAX_STEP_LIMITS: MaxStepLimits(dummy_max_step_limits),
        IconNetworkValueType.SERVICE_CONFIG: ServiceConfig(dummy_service_config),
        IconNetworkValueType.IMPORT_WHITE_LIST: ImportWhiteList(dummy_import_white_list)
    }
    return dummy_invs


@pytest.fixture(scope="function")
def inv_container(dummy_invs):
    container = INVContainer(False)
    for value in dummy_invs.values():
        container.set_inv(value)

    assert len(container._tx_batch) == 0
    return container


@pytest.fixture
def context():
    IconScoreContext.storage = ContextStorage(deploy=Mock(spec=INVStorage))
    context = Mock(spec=IconScoreContext)
    return context


@pytest.fixture
def tx_result():
    return Mock(spec=TransactionResult)


@pytest.fixture
def inv_engine(mocker):
    mocker.patch.object(INVEngine, "_sync_inv_container_with_governance")
    engine: 'INVEngine' = INVEngine()
    return engine


class TestEngine:
    def test_update_inv_container_when_tx_success_and_to_is_gs_before_migration(self,
                                                                                context, inv_engine,
                                                                                inv_container, tx_result):
        context.inv_container = inv_container
        tx_result.status = TransactionResult.SUCCESS
        tx_result.to = GOVERNANCE_SCORE_ADDRESS

        inv_engine.update_inv_container_by_result(context, tx_result)

        inv_engine._sync_inv_container_with_governance.assert_called()

    @pytest.mark.parametrize("is_tx_succeed, to_address", [
        (TransactionResult.SUCCESS, str(DUMMY_ADDRESS_FOR_TEST)),
        (TransactionResult.FAILURE, GOVERNANCE_SCORE_ADDRESS),
        (TransactionResult.FAILURE, str(DUMMY_ADDRESS_FOR_TEST))
    ])
    def test_do_not_update_inv_container(self,
                                         context, inv_engine, inv_container, tx_result,
                                         is_tx_succeed, to_address):
        context.inv_container = inv_container
        tx_result.status = is_tx_succeed
        tx_result.to = to_address

        inv_engine.update_inv_container_by_result(context, tx_result)

        inv_engine._sync_inv_container_with_governance.assert_not_called()

    @pytest.mark.parametrize("is_tx_succeed, new_revision_code, expected_revision_code", [
        (TransactionResult.SUCCESS, 10, 10),
        (TransactionResult.FAILURE, 10, 1)
    ])
    def test_update_inv_container_after_migration(self, context, inv_engine, inv_container, tx_result,
                                                  is_tx_succeed, new_revision_code, expected_revision_code):
        # Constant
        inv_container._is_migrated = True
        inv_container._tx_batch[IconNetworkValueType.REVISION_CODE] = RevisionCode(new_revision_code)
        context.inv_container = inv_container
        # Variable
        tx_result.status = is_tx_succeed

        # Act
        inv_engine.update_inv_container_by_result(context, tx_result)

        actual_revision_code: int = inv_container._icon_network_values[IconNetworkValueType.REVISION_CODE].value
        assert actual_revision_code == expected_revision_code
        assert len(inv_container._tx_batch) == 0
