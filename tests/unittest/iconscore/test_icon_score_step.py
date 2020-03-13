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

from enum import auto
from unittest import mock

import pytest

import iconservice.iconscore.icon_score_step as step_module
from iconservice.base.exception import InvalidRequestException
from iconservice.icon_constant import Revision, IconScoreContextType, MAX_EXTERNAL_CALL_COUNT
from iconservice.icon_network.container import Container as INVContainer
from iconservice.iconscore.icon_score_step import \
    StepType, get_data_size_recursively, get_deploy_content_size, AutoValueEnum, StepTracer, \
    get_input_data_size, IconScoreStepCounterFactory, IconScoreStepCounter, OutOfStepException


@pytest.fixture
def mock_get_data_size_recursively(mocker):
    return mocker.patch.object(step_module, "get_data_size_recursively")


class TestGetInputDataSize:
    INPUT = [
        None,
        "",
        0,
        [],
        [1, 2, 3],
        ["a", "b", "c"],
        [None],
        {"1": 1},
        {1: 1},
        {1: "1"},
        {1: "1", 2: "2"}
    ]

    @pytest.fixture
    def mock_get_data_size_using_json_dumps(self, mocker):
        return mocker.patch.object(step_module, 'get_data_size_using_json_dumps')

    @pytest.mark.parametrize("revision", [r.value for r in Revision if r.value < Revision.THREE.value])
    @pytest.mark.parametrize("input_data, expected_call_data", [(x, [mock.call(x)]) for x in INPUT])
    def test_less_than_revision_three(self,
                                      mock_get_data_size_recursively, mock_get_data_size_using_json_dumps,
                                      revision, input_data, expected_call_data):
        get_input_data_size(revision, input_data)
        mock_get_data_size_recursively.assert_called_once_with(input_data)
        mock_get_data_size_using_json_dumps.assert_not_called()

    @pytest.mark.parametrize("revision", [Revision.THREE.value])
    @pytest.mark.parametrize("input_data, expected_call_data", [(x, [mock.call(x)]) for x in INPUT])
    def test_revision_three(self,
                            mock_get_data_size_recursively, mock_get_data_size_using_json_dumps,
                            revision, input_data, expected_call_data):
        get_input_data_size(revision, input_data)
        mock_get_data_size_using_json_dumps.assert_called_once_with(input_data)
        mock_get_data_size_recursively.assert_not_called()

    @pytest.mark.parametrize("revision", [r.value for r in Revision if r.value > Revision.THREE.value])
    @pytest.mark.parametrize("input_data, expected_call_data", [(x, [mock.call(x)]) for x in INPUT])
    def test_greater_than_revision_three(self,
                                         mock_get_data_size_recursively, mock_get_data_size_using_json_dumps,
                                         revision, input_data, expected_call_data):
        data_size = get_input_data_size(revision, input_data)
        if input_data is None:
            assert data_size == 0
            mock_get_data_size_recursively.assert_not_called()
            mock_get_data_size_using_json_dumps.assert_not_called()
        else:
            mock_get_data_size_using_json_dumps.assert_called_once_with(input_data)
            mock_get_data_size_recursively.assert_not_called()


class TestGetDeployContentSize:
    VALID_CONTENTS_DATA = f"0x{b'deploy_contents_data'.hex()}"
    INPUT = [
        b'deploy_contents_data'.hex(),
        f"0x{str.upper(b'DEPLOY_CONTENTS_DATA'.hex())}",
        f"0x{b'odd_length_deploy_content_data'.hex()}_",
    ]

    @pytest.mark.parametrize("revision", [r.value for r in Revision if r.value < Revision.THREE.value])
    @pytest.mark.parametrize("input_data", [c for c in INPUT])
    def test_get_deploy_content_size_less_than_revision_three(self,
                                                              mock_get_data_size_recursively,
                                                              revision, input_data):
        get_deploy_content_size(revision, input_data)
        mock_get_data_size_recursively.assert_called_once_with(input_data)

    @pytest.mark.parametrize("revision", [r.value for r in Revision if r.value > Revision.THREE.value])
    @pytest.mark.parametrize("input_data", [VALID_CONTENTS_DATA])
    def test_valid_get_deploy_content_size_greater_than_revision_three(self,
                                                                       mock_get_data_size_recursively,
                                                                       revision, input_data):
        actual = get_deploy_content_size(revision, input_data)
        mock_get_data_size_recursively.assert_not_called()
        assert actual == len(input_data[2:]) // 2

    @pytest.mark.parametrize("revision", [r.value for r in Revision if r.value > Revision.THREE.value])
    @pytest.mark.parametrize("input_data", [i for i in INPUT])
    def test_invalid_get_deploy_content_size_greater_than_revision_three(self,
                                                                         mock_get_data_size_recursively,
                                                                         revision, input_data):
        with pytest.raises(InvalidRequestException) as e:
            get_deploy_content_size(revision, input_data)

        assert 'Invalid content data' == e.value.args[0]
        mock_get_data_size_recursively.assert_not_called()


@pytest.mark.parametrize("data, expected", [
    ({"key_very_long_distance": "value"}, len("value".encode())),

    ({"key": "value"}, len("value".encode())),
    ({"key": hex(1_000_000)}, 3),
    ({"key": hex(10_000_000)}, 3),
    ({"key": "1_000_000_000"}, 13),
    ({"key": 1_000_000_000}, 4),
    ({"key": hex(True)}, 1),

    (["value"], len("value".encode())),
    ([hex(1_000_000)], 3),
    ([hex(10_000_000)], 3),
    (["1_000_000_000"], 13),
    ([1_000_000_000], 4),
    ([hex(True)], 1),

    (["value", ["value"]], 2 * len("value".encode())),
    ([hex(1_000_000), [1_000_000_000]], 3 + 4),
    ([hex(10_000_000), [[1_000_000_000]]], 3 + 4),
    ([[["1_000_000_000"]]], 13),
    ([1_000_000_000], 4),
    ([hex(True)], 1),

    ("value", len("value".encode())),
    (hex(1_000_000), 3),
    (hex(10_000_000), 3),
    ("1_000_000_000", 13),
    (1_000_000_000, 4),
    (hex(True), 1),
])
def test_get_data_size_recursively(data, expected):
    ret = get_data_size_recursively(data)
    assert expected == ret


class TestAutoValueEnum:
    class Sample1(AutoValueEnum):
        Abc = auto()
        Def = auto()

    class Sample2(AutoValueEnum):
        NONE = auto()
        ONE = auto()

    class Sample3(AutoValueEnum):
        NONE_VALUE = auto()
        ONE_VALUE = auto()

    @pytest.mark.parametrize("data, expected", [
        (["abc", "def"], [x.value for x in Sample1]),
        (["none", "one"], [x.value for x in Sample2]),
        (["noneValue", "oneValue"], [x.value for x in Sample3])
    ])
    def test_auto_value_enum(self, data, expected):
        assert data == expected


class TestStepTracer:

    def test_step_tracer(self):
        step_tracer = StepTracer()
        assert str(step_tracer) == ""

    def test_step_tracer_reset(self):
        step_tracer = StepTracer()
        step_tracer._cumulative_step = 10

        step_tracer.reset()

        assert step_tracer.cumulative_step == 0
        assert str(step_tracer) == ""

    @pytest.mark.parametrize("step, expected", [
        (0, " 0 | DEFAULT | 0 | 0\n"
            " 1 | CONTRACT_CALL | 0 | 0\n"
            " 2 | CONTRACT_CREATE | 0 | 0\n"
            " 3 | CONTRACT_UPDATE | 0 | 0\n"
            " 4 | CONTRACT_DESTRUCT | 0 | 0\n"
            " 5 | CONTRACT_SET | 0 | 0\n"
            " 6 | GET | 0 | 0\n"
            " 7 | SET | 0 | 0\n"
            " 8 | REPLACE | 0 | 0\n"
            " 9 | DELETE | 0 | 0\n"
            "10 | INPUT | 0 | 0\n"
            "11 | EVENT_LOG | 0 | 0\n"
            "12 | API_CALL | 0 | 0"),

        (1, " 0 | DEFAULT | 1 | 1\n"
            " 1 | CONTRACT_CALL | 1 | 2\n"
            " 2 | CONTRACT_CREATE | 1 | 3\n"
            " 3 | CONTRACT_UPDATE | 1 | 4\n"
            " 4 | CONTRACT_DESTRUCT | 1 | 5\n"
            " 5 | CONTRACT_SET | 1 | 6\n"
            " 6 | GET | 1 | 7\n"
            " 7 | SET | 1 | 8\n"
            " 8 | REPLACE | 1 | 9\n"
            " 9 | DELETE | 1 | 10\n"
            "10 | INPUT | 1 | 11\n"
            "11 | EVENT_LOG | 1 | 12\n"
            "12 | API_CALL | 1 | 13"),

        (10, " 0 | DEFAULT | 10 | 10\n"
             " 1 | CONTRACT_CALL | 10 | 20\n"
             " 2 | CONTRACT_CREATE | 10 | 30\n"
             " 3 | CONTRACT_UPDATE | 10 | 40\n"
             " 4 | CONTRACT_DESTRUCT | 10 | 50\n"
             " 5 | CONTRACT_SET | 10 | 60\n"
             " 6 | GET | 10 | 70\n"
             " 7 | SET | 10 | 80\n"
             " 8 | REPLACE | 10 | 90\n"
             " 9 | DELETE | 10 | 100\n"
             "10 | INPUT | 10 | 110\n"
             "11 | EVENT_LOG | 10 | 120\n"
             "12 | API_CALL | 10 | 130")
    ])
    def test_step_tracer(self, step, expected):
        step_tracer = StepTracer()
        cumulative_step: int = 0

        for step_type in StepType:
            cumulative_step += step
            step_tracer.add(step_type, step, cumulative_step)

        assert step_tracer.cumulative_step == cumulative_step
        assert str(step_tracer) == expected


class TestIconScoreStepCounterFactory:
    @pytest.mark.parametrize("max_step_limits", [{}] + [{t: mock.ANY} for t in IconScoreContextType])
    @pytest.mark.parametrize("context_type", [t for t in IconScoreContextType])
    @pytest.mark.parametrize("step_trace_flag", [True, False])
    def test_create_step_counter(self,
                                 max_step_limits,
                                 context_type, step_trace_flag):
        step_price = mock.ANY
        step_costs = {}

        container = mock.Mock(spec=INVContainer)
        type(container).step_price = mock.PropertyMock(return_value=step_price)
        type(container).step_costs = mock.PropertyMock(return_value=step_costs)
        type(container).max_step_limits = mock.PropertyMock(return_value=max_step_limits)
        actual = IconScoreStepCounterFactory.create_step_counter(container,
                                                                 context_type,
                                                                 step_trace_flag)
        assert step_price == actual.step_price
        assert step_costs == actual._step_costs
        assert max_step_limits.get(context_type, 0) == actual.max_step_limit
        if step_trace_flag:
            assert actual.step_tracer is not None
        else:
            assert actual.step_tracer is None


class TestIconScoreStepCounter:

    @pytest.fixture
    def mock_step_counter(self):
        counter = IconScoreStepCounter(step_price=mock.ANY,
                                       step_costs=mock.ANY,
                                       max_step_limit=mock.ANY,
                                       step_trace_flag=mock.ANY)
        return counter

    @pytest.fixture
    def mock_step_counter_for_apply_step(self, mock_step_counter):
        def _data(external_call_count, step_costs_get_return_value):
            mock_step_counter._external_call_count = external_call_count
            mock_step_counter._step_costs.get = mock.Mock(return_value=step_costs_get_return_value)
            mock_step_counter.consume_step = mock.Mock()
            return mock_step_counter
        return _data

    @pytest.mark.parametrize("mock_step_counter_step_costs_return_value", [0, 1])
    @pytest.mark.parametrize("mock_step_counter_external_call_count", [
        MAX_EXTERNAL_CALL_COUNT - 1,
        MAX_EXTERNAL_CALL_COUNT
    ])
    @pytest.mark.parametrize("step_type", [t for t in StepType])
    @pytest.mark.parametrize("count", [0, 1])
    def test_apply_step(self,
                        mock_step_counter_for_apply_step,
                        mock_step_counter_step_costs_return_value,
                        mock_step_counter_external_call_count,
                        step_type,
                        count):
        mock_step_counter_for_apply_step = \
            mock_step_counter_for_apply_step(external_call_count=mock_step_counter_external_call_count,
                                             step_costs_get_return_value=mock_step_counter_step_costs_return_value)

        if step_type == StepType.CONTRACT_CALL and \
                mock_step_counter_external_call_count > MAX_EXTERNAL_CALL_COUNT - 1:
            # raise exception
            with pytest.raises(InvalidRequestException) as e:
                mock_step_counter_for_apply_step.apply_step(step_type, count)
            assert e.value.args[0] == 'Too many external calls'
        else:
            expected_step = mock_step_counter_for_apply_step._step_costs.get(step_type, 0) * count
            mock_step_counter_for_apply_step.apply_step(step_type, count)
            mock_step_counter_for_apply_step.consume_step.assert_called_once_with(step_type, expected_step)

    @pytest.fixture
    def mock_step_counter_for_consume_step(self, mock_step_counter):
        def _data(max_step_used, step_used, step_limit):
            mock_step_counter._max_step_used = max_step_used
            mock_step_counter._step_used = step_used
            mock_step_counter._step_limit = step_limit
            mock_step_counter._trace_step = mock.Mock()
            return mock_step_counter
        return _data

    @pytest.mark.parametrize("mock_step_counter_step_used", {100 - 1, 100, 100 + 1})
    @pytest.mark.parametrize("mock_step_counter_step_limit", {100 - 1, 100, 100 + 1})
    @pytest.mark.parametrize("mock_step_counter_max_step_used", {100 - 1, 100, 100 + 1})
    @pytest.mark.parametrize("step_type", [t for t in StepType])
    @pytest.mark.parametrize("step", [0, 2])
    def test_consume_step(self,
                          mock_step_counter_for_consume_step,
                          mock_step_counter_step_used,
                          mock_step_counter_step_limit,
                          mock_step_counter_max_step_used,
                          step_type,
                          step):
        mock_step_counter_for_consume_step = \
            mock_step_counter_for_consume_step(max_step_used=mock_step_counter_max_step_used,
                                               step_used=mock_step_counter_step_used,
                                               step_limit=mock_step_counter_step_limit)

        expected_step_used = mock_step_counter_step_used + step

        if expected_step_used > mock_step_counter_step_limit:
            with pytest.raises(OutOfStepException) as e:
                mock_step_counter_for_consume_step.consume_step(step_type=step_type,
                                                                step=step)

            assert e.value.args[0] == mock_step_counter_step_limit
            assert e.value.args[1] == mock_step_counter_step_used
            assert e.value.args[2] == step
            assert e.value.args[3] == step_type
        else:
            step_used = mock_step_counter_for_consume_step.consume_step(step_type=step_type,
                                                                        step=step)
            mock_step_counter_for_consume_step._trace_step.assert_called_once_with(step_type, step)
            assert step_used == expected_step_used

    @pytest.fixture
    def mock_step_counter_for_reset(self, mock_step_counter):
        def _data(max_step_limit, mock_step_tracer, dirty_value):
            mock_step_counter._step_limit = dirty_value
            mock_step_counter._step_used = dirty_value
            mock_step_counter._external_call_count = dirty_value
            mock_step_counter._max_step_used = dirty_value

            mock_step_counter._max_step_limit = max_step_limit
            if mock_step_tracer:
                mock_step_tracer.attach_mock(mock.Mock(), "reset")
            mock_step_counter._step_tracer = mock_step_tracer
            return mock_step_counter
        return _data

    @pytest.mark.parametrize("step_limit", [100 - 1, 100, 100 + 1])
    @pytest.mark.parametrize("max_step_limit", [100 - 1, 100, 100 + 1])
    @pytest.mark.parametrize("mock_step_tracer", [None, mock.Mock()])
    def test_reset(self,
                   mock_step_counter_for_reset,
                   step_limit, max_step_limit, mock_step_tracer):

        dirty_value = 100
        mock_step_counter_for_reset = mock_step_counter_for_reset(max_step_limit=max_step_limit,
                                                                  mock_step_tracer=mock_step_tracer,
                                                                  dirty_value=dirty_value)
        mock_step_counter_for_reset.reset(step_limit)
        assert mock_step_counter_for_reset._step_limit == min(step_limit, max_step_limit)
        assert mock_step_counter_for_reset._step_used == 0
        assert mock_step_counter_for_reset._external_call_count == 0
        assert mock_step_counter_for_reset._max_step_used == 0

        if mock_step_counter_for_reset._step_tracer:
            mock_step_counter_for_reset._step_tracer.reset.assert_called()
