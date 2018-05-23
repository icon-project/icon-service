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
from unittest.mock import Mock

from icon.iconservice.iconscore.icon_score_step import \
    IconScoreStepCounterFactory, IconScoreStepCounter, OutOfStepException


class TestIconScoreStepCounter(unittest.TestCase):
    def setUp(self):
        self.__step_counter_factory \
            = IconScoreStepCounterFactory(10, 10, 10, 10)

    def tearDown(self):
        self.__step_counter_factory = None

    def test_increase_storage_step(self):
        step_counter: IconScoreStepCounter \
            = self.__step_counter_factory.create(100)
        step_counter.increase_storage_step(2)
        self.assertEqual(step_counter.step_used, 20)

    def test_increase_transfer_step(self):
        step_counter: IconScoreStepCounter \
            = self.__step_counter_factory.create(100)
        step_counter.increase_transfer_step(1)
        self.assertEqual(step_counter.step_used, 10)

    def test_increase_message_call_step(self):
        step_counter: IconScoreStepCounter \
            = self.__step_counter_factory.create(100)
        step_counter.increase_message_call_step(1)
        self.assertEqual(step_counter.step_used, 10)

    def test_increase_log_step(self):
        step_counter: IconScoreStepCounter \
            = self.__step_counter_factory.create(100)
        step_counter.increase_log_step(2)
        self.assertEqual(step_counter.step_used, 20)

    def test_out_of_step_exception(self):
        step_counter: IconScoreStepCounter \
            = self.__step_counter_factory.create(15)
        step_counter.increase_log_step(1)
        self.assertEqual(step_counter.step_used, 10)
        self.assertRaises(OutOfStepException, step_counter.increase_log_step, 1)
        self.assertEqual(step_counter.step_used, 10)
