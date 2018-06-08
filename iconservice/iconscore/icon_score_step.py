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
from enum import Enum, unique
from ..base.exception import IconServiceBaseException


@unique
class StepType(Enum):
    TRANSACTION = 0
    STORAGE_SET = 1
    STORAGE_REPLACE = 2
    STORAGE_DELETE = 3
    TRANSFER = 4
    CALL = 5
    EVENTLOG = 6


class IconScoreStepCounterFactory(object):
    """Creates a step counter for the transaction
    """

    def __init__(self) -> None:
        self.__step_unit_dict = dict()

    def set_step_unit(self, step_type: StepType, value: int):
        """Sets a step unit for specific action.

        :param step_type: specific action
        :param value: step unit value
        """
        self.__step_unit_dict[step_type] = value

    def create(self, step_limit: int) -> 'IconScoreStepCounter':
        """Creates a step counter for the transaction

        :param step_limit: step limit of the transaction
        :return: step counter
        """
        # Copying a `dict` so as not to change step units when processing a
        # transaction.
        return IconScoreStepCounter(self.__step_unit_dict.copy(), step_limit)


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

    def __init__(self, step_unit_dict: dict, step_limit: int) -> None:
        """Constructor

        :param step_unit_dict: a dict of base step units
        :param step_limit: step limit for the transaction
        """
        self.__step_unit_dict: dict = step_unit_dict
        self.__step_limit: int = step_limit
        self.__step_used: int = \
            self.__step_unit_dict.get(StepType.TRANSACTION, 0)

    @property
    def step_used(self) -> int:
        """
        Returns used steps in the transaction
        :return: used steps in the transaction
        """
        if self.__step_used < 0:
            return 0
        return self.__step_used

    @property
    def step_limit(self) -> int:
        """
        Returns step limit of the transaction
        :return: step limit of the transaction
        """
        return self.__step_limit

    def increase_step(self, step_type: StepType, count: int) -> int:
        """ Increases steps for given step unit
        """
        step_to_increase = self.__step_unit_dict.get(step_type, 0) * count
        return self.__increase_step(step_to_increase)

    def __increase_step(self, step_to_increase) -> int:
        """ Increases step
        """
        if step_to_increase + self.step_used > self.__step_limit:
            raise OutOfStepException(self.__step_limit, self.step_used,
                                     step_to_increase)
        self.__step_used += step_to_increase
        return self.__step_used
