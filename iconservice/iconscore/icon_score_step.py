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

import json
from enum import Enum, auto
from typing import TYPE_CHECKING, Any, List, Tuple, Optional

from ..base.exception import ExceptionCode, IconServiceBaseException, InvalidRequestException
from ..icon_constant import MAX_EXTERNAL_CALL_COUNT, Revision
from ..utils import to_camel_case, is_lowercase_hex_string, byte_length_of_int

if TYPE_CHECKING:
    from .icon_score_context import IconScoreContextType
    from ..inv.container import Container as INVContainer


def get_input_data_size(revision: int, input_data: Any) -> int:
    """
    Returns size of input data of a transaction

    :param revision: current revision
    :param input_data: input data of transaction
    :return: size of input data
    """
    if revision < Revision.THREE.value:
        return get_data_size_recursively(input_data)

    if revision >= Revision.FOUR.value and input_data is None:
        return 0

    return get_data_size_using_json_dumps(input_data)


def get_data_size_using_json_dumps(data) -> int:
    data = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
    return len(data.encode())


def get_deploy_content_size(revision: int, content: str) -> int:
    """
    Returns size of deploying content.

    If the content is not binary hex string, it raises an exception.

    :param revision: current revision
    :param content: deploying content of transaction
    :return: size of input content
    """
    if revision < Revision.THREE.value:
        return get_data_size_recursively(content)

    if isinstance(content, str) \
            and content.startswith('0x') \
            and is_lowercase_hex_string(content[2:]) \
            and len(content) % 2 == 0:

        return len(content[2:]) // 2
    else:
        raise InvalidRequestException('Invalid content data')


def get_data_size_recursively(data) -> int:
    """
    Deprecated (Only for revision 2 and below).
    Returns size of data(input data or deploying content) by recursive traversal

    :param data: input data or deploying content
    :return: size of data
    """
    size = 0
    if data:
        if isinstance(data, dict):
            for v in data.values():
                size += get_data_size_recursively(v)
        elif isinstance(data, list):
            for v in data:
                size += get_data_size_recursively(v)
        elif isinstance(data, str):
            # If the value is hexstring, it is calculated as bytes otherwise
            # string
            data_body = data[2:] if data.startswith('0x') else data
            if is_lowercase_hex_string(data_body):
                data_body_length = len(data_body)
                size = data_body_length // 2
                if data_body_length % 2 == 1:
                    size += 1
            else:
                size = len(data.encode('utf-8'))
        else:
            # int and bool
            if isinstance(data, int):
                size = byte_length_of_int(data)
    return size


class AutoValueEnum(Enum):
    # noinspection PyMethodParameters
    def _generate_next_value_(name, start, count, last_values):
        # Generates value from the camel-cased name
        return to_camel_case(name.lower())


class StepType(AutoValueEnum):
    DEFAULT = auto()
    CONTRACT_CALL = auto()
    CONTRACT_CREATE = auto()
    CONTRACT_UPDATE = auto()
    CONTRACT_DESTRUCT = auto()
    CONTRACT_SET = auto()
    GET = auto()
    SET = auto()
    REPLACE = auto()
    DELETE = auto()
    INPUT = auto()
    EVENT_LOG = auto()
    API_CALL = auto()


class OutOfStepException(IconServiceBaseException):
    """ An Exception which is thrown when steps are exhausted.
    """

    def __init__(self,
                 step_limit: int,
                 step_used: int,
                 requested_step: int,
                 step_type: StepType):
        """Constructor

        :param step_limit: step limit of the transaction
        :param step_used: used steps in the transaction
        :param requested_step: consuming steps before the exception is thrown
        :param step_type: step type that
        the exception has been thrown when processing
        """
        self.__step_limit: int = step_limit
        self.__step_used = step_used
        self.__requested_step = requested_step
        self.__step_type = step_type

    @property
    def code(self) -> int:
        return ExceptionCode.OUT_OF_STEP

    @property
    def message(self) -> str:
        """
        Returns the exception message
        :return: the exception message
        """
        return f'Out of step: {self.__step_type.value}'

    @property
    def step_limit(self) -> int:
        """
        Returns step limit of the transaction
        :return: step limit of the transaction
        """
        return self.__step_limit

    @property
    def step_used(self) -> int:
        """
        Returns used steps before the exception is thrown in the transaction
        :return: used steps in the transaction
        """
        return self.__step_used

    # TODO unused code
    @property
    def requested_step(self) -> int:
        """
        Returns consuming steps before the exception is thrown.
        :return: Consuming steps before the exception is thrown.
        """
        return self.__requested_step


class StepTracer(object):
    def __init__(self):
        super().__init__()
        self._cumulative_step: int = 0
        self._steps: List[Tuple[StepType, int, int]] = []

    def __str__(self) -> str:
        if len(self._steps) == 0:
            return ""

        lines: List[str] = []

        for i in range(len(self._steps)):
            item: Tuple[StepType, int, int] = self._steps[i]
            # index | stepType | step | cumulativeStep
            lines.append(f"{i:2} | {item[0].name} | {item[1]} | {item[2]}")

        return "\n".join(lines)

    def __len__(self) -> int:
        return len(self._steps)

    @property
    def cumulative_step(self) -> int:
        return self._cumulative_step

    @property
    def steps(self) -> List[Tuple[StepType, int, int]]:
        return self._steps

    def reset(self):
        self._cumulative_step = 0
        self._steps.clear()

    def add(self, step_type: 'StepType', step: int, cumulative_step: int):
        assert cumulative_step == self._cumulative_step + step

        self._cumulative_step += step
        self._steps.append((step_type, step, cumulative_step))


class IconScoreStepCounter(object):
    """ Counts steps in a transaction
    """

    def __init__(self,
                 step_price: int,
                 step_costs: dict,
                 step_limit: int,
                 step_trace_flag: bool = False) -> None:
        """Constructor

        :param step_price: step price
        :param step_costs: a dict of base step costs
        :param step_limit: step limit for current context type
        """

        self._step_price = step_price
        self._step_costs: dict = step_costs
        self._step_limit: int = step_limit
        self._step_used: int = 0
        self._external_call_count: int = 0
        self._max_step_used: int = 0
        self._step_tracer: Optional[StepTracer] = StepTracer() if step_trace_flag else None

    @property
    def step_price(self) -> int:
        """
        Returns the step price
        :return: step price
        """
        return self._step_price

    @property
    def step_limit(self) -> int:
        """
        Returns step limit of the transaction
        :return: step limit of the transaction
        """
        return self._step_limit

    @property
    def step_used(self) -> int:
        """
        Returns used steps in the transaction
        :return: used steps in the transaction
        """
        return max(self._step_used,
                   self._step_costs.get(StepType.DEFAULT, 0))

    @property
    def max_step_used(self) -> int:
        """
        Returns max used steps in the transaction
        :return: max used steps in the transaction
        """
        return self._max_step_used

    @property
    def step_tracer(self) -> Optional[StepTracer]:
        return self._step_tracer

    def apply_step(self, step_type: StepType, count: int) -> int:
        """ Increases steps for given step cost
        """

        if step_type == StepType.CONTRACT_CALL:
            self._external_call_count += 1
            if self._external_call_count > MAX_EXTERNAL_CALL_COUNT:
                raise InvalidRequestException('Too many external calls')

        step: int = self._step_costs.get(step_type, 0) * count

        return self.consume_step(step_type, step)

    def consume_step(self, step_type: StepType, step: int) -> int:
        step_used: int = self._step_used + step

        self._max_step_used = max(self._max_step_used, step_used)

        if step_used > self._step_limit:
            step_used = self._step_used
            self._step_used = self._step_limit
            raise OutOfStepException(
                self._step_limit, step_used, step, step_type)

        self._step_used = step_used

        # Save the step info to StepTracer to trace step cost
        self._trace_step(step_type, step)

        return step_used

    def _trace_step(self, step_type: StepType, step: int):
        if self._step_tracer is not None:
            self._step_tracer.add(step_type, step, self._step_used)

    def get_step_cost(self, step_type: StepType) -> int:
        return self._step_costs.get(step_type, 0)
