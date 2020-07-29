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

import pytest

from iconservice.inv.container import ValueConverter
from iconservice.inv.data.value import *
from tests import create_address

DUMMY_ADDRESS_FOR_TEST = create_address()


class TestValueConverter:

    @pytest.mark.parametrize("inv_type, inv_value, expected_inv_value", [
        (IconNetworkValueType.REVISION_CODE, 1, RevisionCode(1)),
        (IconNetworkValueType.REVISION_NAME, "1.1.1", RevisionName("1.1.1")),
        (IconNetworkValueType.SCORE_BLACK_LIST, [DUMMY_ADDRESS_FOR_TEST], ScoreBlackList([DUMMY_ADDRESS_FOR_TEST])),
        (IconNetworkValueType.STEP_PRICE, 10, StepPrice(10)),
        (IconNetworkValueType.STEP_COSTS, {'default': 0}, StepCosts({StepType('default'): 0})),
        (IconNetworkValueType.MAX_STEP_LIMITS, {"invoke": 10}, MaxStepLimits({IconScoreContextType.INVOKE: 10})),
        (IconNetworkValueType.SERVICE_CONFIG, 1, ServiceConfig(1)),
        (IconNetworkValueType.IMPORT_WHITE_LIST, {"iconservice": ['*']}, ImportWhiteList({"iconservice": ['*']})),
        (IconNetworkValueType.IREP, 1000, IRep(1000)),
    ])
    def test_convert_for_icon_service(self, inv_type, inv_value, expected_inv_value):
        actual_converted_value: 'Value' = ValueConverter.convert_for_icon_service(inv_type, inv_value)

        assert type(actual_converted_value) == type(expected_inv_value)
        assert actual_converted_value.value == expected_inv_value.value

    @pytest.mark.parametrize("invalid_max_step_limits", [
        {"direct": 10},
        {"estimation": 10},
        {1: 10},
        {b'bytes': 10}
    ])
    def test_when_convert_invalid_convert_max_step_limits_should_raise_exception(self, invalid_max_step_limits):
        with pytest.raises(BaseException):
            ValueConverter.convert_for_icon_service(IconNetworkValueType.MAX_STEP_LIMITS, invalid_max_step_limits)

    def test_when_convert_unknown_step_type_key_should_pass(self):
        step_costs = {
            'default': 10,
            'contractCall': 10,
            'unknown_type': 0
        }
        expected_step_costs = {
            StepType('default'): 10,
            StepType('contractCall'): 10,
        }

        converted_step_costs = ValueConverter.convert_for_icon_service(IconNetworkValueType.STEP_COSTS, step_costs)

        assert converted_step_costs.value == expected_step_costs

    @pytest.mark.parametrize("inv_type, inv_value, expected_inv_value", [
        (IconNetworkValueType.REVISION_CODE, 1, 1),
        (IconNetworkValueType.REVISION_NAME, "1.1.1", "1.1.1"),
        (IconNetworkValueType.SCORE_BLACK_LIST, [DUMMY_ADDRESS_FOR_TEST], [DUMMY_ADDRESS_FOR_TEST]),
        (IconNetworkValueType.STEP_PRICE, 10, 10),
        (IconNetworkValueType.STEP_COSTS, {StepType('default'): 0}, {'default': 0}),
        (IconNetworkValueType.MAX_STEP_LIMITS, {IconScoreContextType.INVOKE: 10}, {"invoke": 10}),
        (IconNetworkValueType.SERVICE_CONFIG, 1, 1),
        (IconNetworkValueType.IMPORT_WHITE_LIST, {"iconservice": ['*']}, {"iconservice": ['*']}),
    ])
    def test_convert_for_governance(self, inv_type, inv_value, expected_inv_value):
        actual_converted_value: Any = ValueConverter.convert_for_governance(inv_type, inv_value)

        assert actual_converted_value == expected_inv_value
