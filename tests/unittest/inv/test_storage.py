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

from iconservice.iconscore.icon_score_context import IconScoreContext
from iconservice.inv import INVContainer, INVStorage
from iconservice.inv.data.value import *
from iconservice.utils import ContextStorage
from tests import create_address

DUMMY_ADDRESS_FOR_TEST = create_address()


@pytest.fixture()
def inv_storage(context_db):
    return INVStorage(context_db)


@pytest.fixture(scope="module")
def dummy_invs():
    dummy_revision_number = 1
    dummy_revision_code = "1.1.1"
    dummy_service_config: int = 0
    dummy_step_costs = {
        'default': 0,
        'contractCall': 0,
        'contractCreate': 0,
        'contractUpdate': 0,
        'contractDestruct': 0,
        'contractSet': 0,
        'get': 0,
        'set': 0,
        'replace': 0,
        'delete': -150,
        'input': 0,
        'eventLog': 0,
        'apiCall': 0
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
        IconNetworkValueType.REVISION_CODE: RevisionCode(dummy_revision_number),
        IconNetworkValueType.REVISION_NAME: RevisionName(dummy_revision_code),
        IconNetworkValueType.SCORE_BLACK_LIST: ScoreBlackList(dummy_score_black_list),
        IconNetworkValueType.STEP_PRICE: StepPrice(dummy_step_price),
        IconNetworkValueType.STEP_COSTS: StepCosts(dummy_step_costs),
        IconNetworkValueType.MAX_STEP_LIMITS: MaxStepLimits(dummy_max_step_limits),
        IconNetworkValueType.SERVICE_CONFIG: ServiceConfig(dummy_service_config),
        IconNetworkValueType.IMPORT_WHITE_LIST: ImportWhiteList(dummy_import_white_list)
    }
    return dummy_invs


@pytest.fixture
def context():
    IconScoreContext.storage = ContextStorage(deploy=Mock(spec=INVStorage))
    context = Mock(spec=IconScoreContext)
    context.type = IconScoreContextType.DIRECT
    context.readonly = False
    return context


class TestINVStorage:

    def test_migrate_and_get_container_after_migration(self, context, inv_storage, dummy_invs):
        dummy_inv_list: list = [value for value in dummy_invs.values()]

        # TEST: when get container before migration (i.e. INVs have not been recorded on stateDB), should return None
        ret_container_before_migration = inv_storage.get_container(context)

        assert ret_container_before_migration is None

        # TEST: when get container after migration should return INVContainer and it's migration flag should be True
        inv_storage.migrate(context, dummy_inv_list)
        ret_container_after_migration = inv_storage.get_container(context)

        assert isinstance(ret_container_after_migration, INVContainer)
        assert ret_container_after_migration.is_migrated is True
        for type_, value in ret_container_after_migration._icon_network_values.items():
            assert value.value == dummy_invs[type_].value
