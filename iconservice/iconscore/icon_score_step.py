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
from enum import Enum, auto
from typing import TYPE_CHECKING

from iconservice.icon_constant import MAX_EXTERNAL_CALL_COUNT
from iconservice.utils import to_camel_case
from ..base.exception import IconServiceBaseException, ExceptionCode, InvalidRequestException

if TYPE_CHECKING:
    from iconservice.iconscore.icon_score_context import IconScoreContextType


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


class IconScoreStepCounterFactory(object):
    """Creates a step counter for the transaction
    """

    def __init__(self) -> None:
        self._step_cost_dict = {}
        self._step_price = 0
        self._max_step_limits = {}

    def get_step_cost(self, step_type: 'StepType') -> int:
        return self._step_cost_dict.get(step_type, 0)

    def set_step_cost(self, step_type: 'StepType', value: int):
        """Sets the step cost for specific action.

        :param step_type: specific action
        :param value: step cost
        """
        self._step_cost_dict[step_type] = value

    def get_step_price(self):
        """Returns the step price

        :return: step price
        """
        return self._step_price

    def set_step_price(self, step_price: int):
        """Sets the step price

        :param step_price: step price
        """
        self._step_price = step_price

    def get_max_step_limit(self, context_type: 'IconScoreContextType'):
        """Returns the max step limit

        :return: the max step limit
        """
        return self._max_step_limits.get(context_type, 0)

    def set_max_step_limit(
            self, context_type: 'IconScoreContextType', max_step_limit: int):
        """Sets the max step limit

        :param context_type: context type
        :param max_step_limit: the max step limit for the context type
        """
        self._max_step_limits[context_type] = max_step_limit

    def create(self, step_limit: int) \
            -> 'IconScoreStepCounter':
        """Creates a step counter for the transaction

        :param step_limit: step limit of the transaction.
        :return: step counter
        """

        # Copying a `dict` so as not to change step costs when processing a
        # transaction.
        return IconScoreStepCounter(
            self._step_cost_dict.copy(), step_limit, self._step_price)


class OutOfStepException(IconServiceBaseException):
    """ An Exception which is thrown when steps are exhausted.
    """

    def __init__(self, step_limit: int, step_used: int,
                 requested_step: int, step_type: StepType) -> None:
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
        return ExceptionCode.SCORE_ERROR

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

    @property
    def requested_step(self) -> int:
        """
        Returns consuming steps before the exception is thrown.
        :return: Consuming steps before the exception is thrown.
        """
        return self.__requested_step


class IconScoreStepCounter(object):
    """ Counts steps in a transaction
    """

    def __init__(self,
                 step_cost_dict: dict,
                 step_limit: int,
                 step_price: int) -> None:
        """Constructor

        :param step_cost_dict: a dict of base step costs
        :param step_limit: step limit for the transaction
        :param step_price: step price
        """
        self._step_cost_dict: dict = step_cost_dict
        self._step_limit: int = step_limit
        self._step_price = step_price
        self._step_used: int = 0
        self._external_call_count: int = 0

    @property
    def step_used(self) -> int:
        """
        Returns used steps in the transaction
        :return: used steps in the transaction
        """
        return max(self._step_used,
                   self._step_cost_dict.get(StepType.DEFAULT, 0))

    @property
    def step_limit(self) -> int:
        """
        Returns step limit of the transaction
        :return: step limit of the transaction
        """
        return self._step_limit

    @property
    def step_price(self) -> int:
        """
        Returns the step price
        :return: step price
        """
        return self._step_price

    def apply_step(self, step_type: StepType, count: int) -> int:
        """ Increases steps for given step cost
        """

        if step_type == StepType.CONTRACT_CALL:
            self._external_call_count += 1
            if self._external_call_count > MAX_EXTERNAL_CALL_COUNT:
                raise InvalidRequestException('Too many external calls')

        step_to_apply = self._step_cost_dict.get(step_type, 0) * count
        if step_to_apply + self._step_used > self._step_limit:
            step_used = self._step_used
            self._step_used = self._step_limit
            raise OutOfStepException(
                self._step_limit, step_used, step_to_apply, step_type)

        self._step_used += step_to_apply

        return self.step_used
