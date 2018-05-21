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
from ..base.exception import IconServiceBaseException


class IconScoreStepCounterFactory(object):
    """Creates a step counter for the transaction
    """

    def __init__(
            self,
            storage_step_unit: int = 0,
            transfer_step_unit: int = 0,
            message_call_step_unit: int = 0,
            log_step_unit: int = 0) -> None:
        """Constructor

        :param storage_step_unit: a base step unit for storing to db
        :param transfer_step_unit: a base step unit for transferring icx
        :param message_call_step_unit: a base step unit for calling to another SCORE
        :param log_step_unit: a base step unit for logging.
        """
        self.storage_step_unit = storage_step_unit
        self.transfer_step_unit = transfer_step_unit
        self.message_call_step_unit = message_call_step_unit
        self.log_step_unit = log_step_unit

    def create(self, step_limit: int) -> 'IconScoreStepCounter':
        """Creates a step counter for the transaction

        :param step_limit: step limit of the transaction
        :return: step counter
        """
        return IconScoreStepCounter(
            self.storage_step_unit,
            self.transfer_step_unit,
            self.message_call_step_unit,
            self.log_step_unit,
            step_limit)


class OutOfStepException(IconServiceBaseException):
    """ An Exception which is thrown when steps are exhausted.
    """

    def __init__(self, step_limit: int, step_used: int,
                 requested_step: int) -> None:
        """Constructor

        :param storage_step_unit: a base step unit for storing to db
        :param transfer_step_unit: a base step unit for transferring icx
        :param message_call_step_unit: a base step unit for calling to another SCORE
        :param log_step_unit: a base step unit for logging.
        :param step_limit: step limit of the transaction
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
                 storage_step_unit: int,
                 transfer_step_unit: int,
                 message_call_step_unit: int,
                 log_step_unit: int,
                 step_limit: int) -> None:
        """Constructor

        :param storage_step_unit: a base step unit for storing to db
        :param transfer_step_unit: a base step unit for transferring icx
        :param message_call_step_unit: a base step unit for calling to another SCORE
        :param log_step_unit: a base step unit for logging.
        :param step_limit: step limit of the transaction
        """
        self.__storage_step_unit = storage_step_unit
        self.__transfer_step_unit = transfer_step_unit
        self.__message_call_step_unit = message_call_step_unit
        self.__log_step_unit = log_step_unit
        self.__step_limit: int = step_limit
        self.__step_used: int = 0

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

    def increase_storage_step(self, data_size: int) -> int:
        """ Increases storage step when write db
        """
        return self.__increase_step(data_size * self.__storage_step_unit)

    def increase_transfer_step(self, count: int) -> int:
        """ Increases transfer step when transferring icx
        """
        return self.__increase_step(count * self.__transfer_step_unit)

    def increase_message_call_step(self, count: int) -> int:
        """ Increases message call step when internal calling in a transaction.
        """
        return self.__increase_step(count * self.__message_call_step_unit)

    def increase_log_step(self, data_size: int) -> int:
        """ Increases log step when logging.
        """
        return self.__increase_step(data_size * self.__log_step_unit)

    def __increase_step(self, step_to_increase) -> int:
        """ Increases step
        """

        if step_to_increase + self.step_used > self.__step_limit:
            raise OutOfStepException(self.__step_limit, self.step_used,
                                     step_to_increase)
        self.__step_used += step_to_increase
        return self.__step_used
