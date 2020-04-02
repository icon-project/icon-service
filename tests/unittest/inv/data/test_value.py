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

from random import random

import pytest

from iconservice.inv.data.value import *
from tests import create_address


class TestValue:
    def _modify_if_collection_type(self, value: Any):
        if isinstance(value, list):
            value.append("dump")
            for val in value:
                if isinstance(val, (list, set, dict)):
                    self._modify_if_collection_type(val)
        if isinstance(value, set):
            value.add("dump")
            for val in value:
                if isinstance(val, (list, set, dict)):
                    self._modify_if_collection_type(val)
        elif isinstance(value, dict):
            value["dump_key"] = "dump_value"
            for val in value.values():
                if isinstance(val, (list, set, dict)):
                    self._modify_if_collection_type(val)

    @pytest.mark.parametrize("icon_network_value, value", [
        (RevisionCode(5), 5),
        (RevisionName("1.1.5"), "1.1.5"),
        (ScoreBlackList([]), []),
        (StepPrice(10_000), 10_000),
        (StepCosts({StepType('default'): 10_000}), {StepType('default'): 10_000}),
        (MaxStepLimits({
            IconScoreContextType.INVOKE: 100_000_000,
            IconScoreContextType.QUERY: 100_000_000
        }), {
             IconScoreContextType.INVOKE: 100_000_000,
             IconScoreContextType.QUERY: 100_000_000
         }),
        (ServiceConfig(5), 5),
        (ImportWhiteList({"iconservice": ['*'], "os": ["path"]}), {"iconservice": ['*'], "os": ["path"]})
    ])
    def test_from_to_bytes(self, icon_network_value: 'Value', value):
        # TEST: Check key is generated as expected
        expected_bytes_key = b'inv' + icon_network_value.TYPE.value

        bytes_key: bytes = icon_network_value.make_key()

        assert bytes_key == expected_bytes_key

        # TEST: encoded_value should include the version information and encoded by msgpack
        encoded_value: bytes = icon_network_value.to_bytes()

        unpacked_value: list = MsgPackForDB.loads(encoded_value)
        expected_version = 0

        assert len(unpacked_value) == 2
        assert unpacked_value[0] == expected_version

        # TEST: decoded value has same value with original
        decoded_value: 'Value' = icon_network_value.from_bytes(encoded_value)

        assert decoded_value.value == icon_network_value.value

        # TEST: returned value property should not effect on Value instances' value when modify
        returned_value: Any = icon_network_value.value

        # Act
        self._modify_if_collection_type(returned_value)

        assert value == icon_network_value.value

    # Below tests each Value's initialization

    @pytest.mark.parametrize("value", [
        {
            type_: random() for type_ in StepType
        },
        {
            StepType('delete'): -150
        },
        {
            StepType('contractDestruct'): -100,
        }
    ])
    def test_step_costs_initialization(self, value):
        step_costs: 'StepCosts' = StepCosts(value)

        assert step_costs.value == value

    @pytest.mark.parametrize("value", [{type_: -1} for type_ in StepType if
                                       type_ != StepType.CONTRACT_DESTRUCT and type_ != StepType.DELETE])
    def test_step_costs_should_raise_exception_when_setting_minus_costs(self, value):
        with pytest.raises(InvalidParamsException) as e:
            _: 'StepCosts' = StepCosts(value)

        assert e.value.message.startswith("Invalid step costs:")

    @pytest.mark.parametrize("value", [["list"], "str", 1, True, ("1", "2"), 0.1, b'bytes'])
    def test_step_costs_should_raise_exception_when_input_invalid_type_value(self, value):
        with pytest.raises(TypeError) as e:
            _: 'StepCosts' = StepCosts(value)

        assert e.value.args[0].startswith("Invalid Step costs type:")

    @pytest.mark.parametrize("value", [{"dict": 1}, ["list"], "str", True, ("1", "2"), 0.1, -1, b'bytes'])
    def test_step_price_should_raise_exception_when_input_invalid_value(self, value):
        with pytest.raises(BaseException):
            _: 'StepPrice' = StepPrice(value)

    @pytest.mark.parametrize("value", [
        {IconScoreContextType.INVOKE: -1, IconScoreContextType.QUERY: 0},
        {IconScoreContextType.INVOKE: 0, IconScoreContextType.QUERY: -1},
        ["list"], "str", True, ("1", "2"), 0.1, -1, b'bytes'
    ])
    def test_max_step_limits_should_raise_exception_when_input_invalid_value(self, value):
        with pytest.raises(BaseException):
            _: 'MaxStepLimits' = MaxStepLimits(value)

    @pytest.mark.parametrize("value, expected_invoke, expected_query", [
        ({}, 0, 0),
        ({IconScoreContextType.INVOKE: 1}, 1, 0),
        ({IconScoreContextType.QUERY: 1}, 0, 1)
    ])
    def test_max_step_limits_should_supplement_value(self, value, expected_invoke, expected_query):
        max_step_limits: 'MaxStepLimits' = MaxStepLimits(value)

        assert max_step_limits.value[IconScoreContextType.INVOKE] == expected_invoke
        assert max_step_limits.value[IconScoreContextType.QUERY] == expected_query

    @pytest.mark.parametrize("value", [
        [1],
        [b'bytes'],
        ["str"],
        [create_address(), "str"],
        {"dict": "value"}, "str", True, ("1", "2"), 0.1, -1, b'bytes'
    ])
    def test_score_black_list_should_raise_exception_when_input_invalid_value(self, value):
        with pytest.raises(BaseException):
            _: 'ScoreBlackList' = ScoreBlackList(value)

    @pytest.mark.parametrize("value", [
        {1: ["path"]},
        {b'bytes': ["path"]},
        {"key": [1]},
        {"key": {"dict": "value"}},
        {"key": ("1", "2")},
        {"key": ("1", "2")},
        {"dict": "value"},
        {"dict": 1},
        {"dict": b'bytes'},
        {"dict": True},
        "str", True, ("1", "2"), 0.1, -1, b'bytes'
    ])
    def test_import_white_list_should_raise_exception_when_input_invalid_value(self, value):
        with pytest.raises(BaseException):
            _: 'ImportWhiteList' = ImportWhiteList(value)

    @pytest.mark.parametrize("value", [
        -1,
        sum(IconServiceFlag) + 1,
        {"dict": True}, "str", ("1", "2"), b'bytes'
    ])
    def test_service_config_should_raise_exception_when_input_invalid_value(self, value):
        with pytest.raises(BaseException):
            _: 'ServiceConfig' = ServiceConfig(value)
