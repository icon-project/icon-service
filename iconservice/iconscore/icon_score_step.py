# -*- coding: utf-8 -*-

# Copyright 2017-2018 theloop Inc.
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

from iconservice.utils import to_camel_case
from ..base.exception import IconServiceBaseException


class AutoValueEnum(Enum):
    # noinspection PyMethodParameters
    def _generate_next_value_(name, start, count, last_values):
        # Generates value from the camel-cased name
        return to_camel_case(name.lower())


class StepType(AutoValueEnum):
    C = auto()
    CONTRACT_CALL = auto()
    CONTRACT_CREATE = auto()
    CONTRACT_UPDATE = auto()
    CONTRACT_DESTRUCT = auto()
    CONTRACT_SET = auto()
    SET = auto()
    REPLACE = auto()
    DELETE = auto()
    INPUT = auto()
    EVENT_LOG = auto()


class IconScoreStepCounterFactory(object):
    """Creates a step counter for the transaction
    """

    def __init__(self) -> None:
        self.__step_cost_dict = {}

    def get_step_cost(self, step_type: 'StepType') -> int:
        return self.__step_cost_dict.get(step_type, 0)

    def set_step_cost(self, step_type: 'StepType', value: int):
        """Sets the step cost for specific action.

        :param step_type: specific action
        :param value: step cost
        """
        self.__step_cost_dict[step_type] = value

    def create(self,
               step_limit: int, step_price: int) -> 'IconScoreStepCounter':
        """Creates a step counter for the transaction

        :param step_limit: step limit of the transaction
        :param step_price:
        :return: step counter
        """
        # Copying a `dict` so as not to change step costs when processing a
        # transaction.
        return IconScoreStepCounter(
            self.__step_cost_dict.copy(), step_limit, step_price)


class OutOfStepException(IconServiceBaseException):
    """ An Exception which is thrown when steps are exhausted.
    """

    def __init__(self, step_limit: int, step_used: int,
                 requested_step: int) -> None:
        """Constructor

        :param step_limit: step limit of the transaction
        :param step_used: used steps in the transaction
        :param requested_step: consuming steps before the exception is thrown
        """
        self.__step_limit: int = step_limit
        self.__step_used = step_used
        self.__requested_step = requested_step

    @property
    def message(self) -> str:
        """
        Returns the exception message
        :return: the exception message
        """
        return f'\'Requested steps\': {self.requested_step}, ' \
               f'\'Remaining steps\': {self.step_limit - self.step_used} '

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
        """
        self.__step_cost_dict: dict = step_cost_dict
        self.__step_limit: int = step_limit
        self.step_price = step_price
        self.__step_used: int = 0

    @property
    def step_used(self) -> int:
        """
        Returns used steps in the transaction
        :return: used steps in the transaction
        """
        return max(self.__step_used, self.__step_cost_dict.get(StepType.C, 0))

    @property
    def step_limit(self) -> int:
        """
        Returns step limit of the transaction
        :return: step limit of the transaction
        """
        return self.__step_limit

    def append_step(self, step_type: StepType, count: int) -> int:
        """ Increases steps for given step cost
        """
        step_to_append = self.__step_cost_dict.get(step_type, 0) * count
        return self.__append_step(step_to_append)

    def __append_step(self, step_to_append) -> int:
        """ Increases step
        """
        # If step_price is 0, do not raise OutOfStepException
        if self.step_price > 0:
            if step_to_append + self.__step_used > self.__step_limit:
                self.__step_used = self.__step_limit
                raise OutOfStepException(
                    self.__step_limit, self.step_used, step_to_append)

        self.__step_used += step_to_append

        return self.step_used
