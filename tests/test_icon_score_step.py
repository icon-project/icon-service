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

"""IconScoreEngine testcase
"""

import unittest

from iconservice.iconscore.icon_score_step import \
    IconScoreStepCounterFactory, IconScoreStepCounter, OutOfStepException, \
    StepType


class TestIconScoreStepCounter(unittest.TestCase):
    def setUp(self):
        self.__step_counter_factory = IconScoreStepCounterFactory()
        self.__step_counter_factory.set_step_unit(StepType.TRANSACTION, 6000)
        self.__step_counter_factory.set_step_unit(StepType.STORAGE_SET, 200)
        self.__step_counter_factory.set_step_unit(StepType.STORAGE_REPLACE, 50)
        self.__step_counter_factory.set_step_unit(StepType.STORAGE_DELETE, -100)
        self.__step_counter_factory.set_step_unit(StepType.TRANSFER, 10000)
        self.__step_counter_factory.set_step_unit(StepType.CALL, 1000)
        self.__step_counter_factory.set_step_unit(StepType.EVENTLOG, 20)

    def tearDown(self):
        self.__step_counter_factory = None

    def test_increase_storage_set_step(self):
        step_counter: IconScoreStepCounter \
            = self.__step_counter_factory.create(10000)
        step_counter.increase_step(StepType.STORAGE_SET, 2)
        self.assertEqual(step_counter.step_used, 6400)

    def test_increase_storage_replace_step(self):
        step_counter: IconScoreStepCounter \
            = self.__step_counter_factory.create(10000)
        step_counter.increase_step(StepType.STORAGE_REPLACE, 2)
        self.assertEqual(step_counter.step_used, 6100)

    def test_increase_storage_delete_step(self):
        step_counter: IconScoreStepCounter \
            = self.__step_counter_factory.create(10000)
        step_counter.increase_step(StepType.STORAGE_DELETE, 2)
        self.assertEqual(step_counter.step_used, 5800)
        step_counter.increase_step(StepType.STORAGE_DELETE, 100)
        self.assertEqual(step_counter.step_used, 0)

    def test_increase_transfer_step(self):
        step_counter: IconScoreStepCounter \
            = self.__step_counter_factory.create(20000)
        step_counter.increase_step(StepType.TRANSFER, 1)
        self.assertEqual(step_counter.step_used, 16000)

    def test_increase_call_step(self):
        step_counter: IconScoreStepCounter \
            = self.__step_counter_factory.create(10000)
        step_counter.increase_step(StepType.CALL, 2)
        self.assertEqual(step_counter.step_used, 8000)

    def test_increase_eventlog_step(self):
        step_counter: IconScoreStepCounter \
            = self.__step_counter_factory.create(10000)
        step_counter.increase_step(StepType.EVENTLOG, 2)
        self.assertEqual(step_counter.step_used, 6040)

    def test_out_of_step_exception(self):
        step_counter: IconScoreStepCounter \
            = self.__step_counter_factory.create(10000)
        step_counter.increase_step(StepType.EVENTLOG, 1)
        self.assertEqual(step_counter.step_used, 6020)
        self.assertRaises(OutOfStepException,
                          step_counter.increase_step, StepType.TRANSFER, 1)
        self.assertEqual(step_counter.step_used, 6020)
