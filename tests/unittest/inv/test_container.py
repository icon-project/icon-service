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


class TestBatchDict:
    @pytest.mark.parametrize("invalid_key", [
        "string",
        5,
        b'bytes_key'
    ])
    def test_set_invalid_key(self, invalid_key):
        batch_dict = INVContainer.BatchDict()
        temp_value = "value"

        with pytest.raises(ValueError) as e:
            batch_dict[invalid_key] = temp_value

        assert e.value.args[0].startswith("Invalid value key")

    @pytest.mark.parametrize("invalid_value", [
        "string",
        5,
        b'bytes_key'
    ])
    def test_set_invalid_value_type(self, invalid_value):
        batch_dict = INVContainer.BatchDict()
        valid_key_type = IconNetworkValueType.STEP_COSTS

        with pytest.raises(ValueError) as e:
            batch_dict[valid_key_type] = invalid_value

        assert e.value.args[0].startswith("Invalid value type")

    # This test is deprecated as do not check wheather the key and value match
    # @pytest.mark.parametrize("key", [type_key for type_key in IconNetworkValueType])
    # def test_key_value_mismatch(self, key, dummy_invs):
    #     batch_dict = INVContainer.BatchDict()
    #
    #     for icon_network_value in dummy_invs.values():
    #         if icon_network_value.TYPE == key:
    #             batch_dict[key] = icon_network_value
    #         else:
    #             with pytest.raises(ValueError) as e:
    #                 batch_dict[key] = icon_network_value
    #             assert e.value.args[0] == "Do not match key and value"


class TestContainer:

    def test_migration_with_insufficient_data_should_raise_exception(self, context, dummy_invs, inv_container):
        dummy_inv_list: list = [value for value in dummy_invs.values()]
        data_len: int = len(dummy_inv_list)

        for i in range(data_len):
            insufficient_inv_list: list = dummy_inv_list[:i]
            with pytest.raises(InvalidParamsException) as e:
                inv_container.migrate(insufficient_inv_list)

            assert e.value.message == "Icon Network Values are insufficient"
            assert len(inv_container._tx_batch) == 0
            assert inv_container._tx_batch.is_migration_triggered() is False
            context.storage.inv.put_migration_flag.assert_not_called()

    def test_migration_success(self, context, dummy_invs, inv_container):
        dummy_inv_list: list = [value for value in dummy_invs.values()]

        inv_container.migrate(dummy_inv_list)

        assert len(inv_container._tx_batch) == len(dummy_inv_list)
        assert inv_container._tx_batch.is_migration_triggered() is True

    @staticmethod
    def _check_each_inv_is_different(actual_invs, expected_invs):
        for type_, value in expected_invs.items():
            assert actual_invs[type_] != value

    def test_update_migration_if_success(self, context, dummy_invs, inv_container):
        black_score = create_address()
        expected_invs = {
            IconNetworkValueType.REVISION_CODE: RevisionCode(5),
            IconNetworkValueType.REVISION_NAME: RevisionName("1.1.5"),
            IconNetworkValueType.SCORE_BLACK_LIST: ScoreBlackList([black_score]),
            IconNetworkValueType.STEP_PRICE: StepPrice(10_000),
            IconNetworkValueType.STEP_COSTS: StepCosts({
                StepType('default'): 10_000
            }),
            IconNetworkValueType.MAX_STEP_LIMITS: MaxStepLimits({
                IconScoreContextType.INVOKE: 100_000_000,
                IconScoreContextType.QUERY: 100_000_000
            }),
            IconNetworkValueType.SERVICE_CONFIG: ServiceConfig(5),
            IconNetworkValueType.IMPORT_WHITE_LIST: ImportWhiteList({"iconservice": ['*'], "os": ["path"]})
        }
        data: list = [value for value in expected_invs.values()]
        self._check_each_inv_is_different(inv_container._icon_network_values, expected_invs)

        # Act
        inv_container.migrate(data)
        inv_container.update_migration_if_succeed()

        assert inv_container.is_migrated is True
        for type_, value in expected_invs.items():
            assert inv_container._icon_network_values[type_] == value

    @pytest.mark.parametrize("is_migrated, is_open", [
        (False, False),
        (False, True),
        (True, True)
    ])
    def test_set_inv(self, inv_container, is_migrated, is_open):
        inv_container._is_migrated = is_migrated
        dummy_inv_value = RevisionCode(5)

        inv_container.set_inv(dummy_inv_value, is_open)

        assert inv_container.revision_code == dummy_inv_value.value

    def test_when_set_inv_after_migration_and_not_open(self, inv_container):
        is_migrated, is_open = True, False
        inv_container._is_migrated = is_migrated
        dummy_inv_value = RevisionCode(5)

        with pytest.raises(PermissionError) as e:
            inv_container.set_inv(dummy_inv_value, is_open)

        assert e.value.args[0].startswith("Invalid case of setting ICON Network value from icon-service")

    def test_set_tx_batch_before_migration(self, context, inv_container):
        dummy_inv_value = RevisionCode(5)

        with pytest.raises(AssertionError):
            inv_container.set_inv_to_tx_batch(dummy_inv_value)

        context.storage.inv.put_value.assert_not_called()

    def test_set_tx_batch_after_migration(self, context, inv_container):
        inv_container._is_migrated = True
        dummy_inv_value = RevisionCode(5)

        inv_container.set_inv_to_tx_batch(dummy_inv_value)

        assert inv_container.revision_code == dummy_inv_value.value

    def test_copy_container(self, inv_container):
        inv_container._tx_batch[RevisionCode.TYPE] = RevisionCode(5)

        copied_container = inv_container.copy()

        assert id(copied_container) != id(inv_container)
        assert id(copied_container._tx_batch) != id(inv_container._tx_batch)
        assert len(copied_container._tx_batch) == 0 != len(inv_container._tx_batch)
        assert id(copied_container._icon_network_values) != id(inv_container._icon_network_values)
        for type_, value in inv_container._icon_network_values.items():
            # Do not copy each value (as just set the value when there is change)
            assert id(copied_container._icon_network_values[type_]) == id(value)
