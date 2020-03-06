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

import random
import unittest

from iconservice.iconscore.icon_score_step import StepTracer, StepType


class TestStepTracer(unittest.TestCase):
    def setUp(self) -> None:
        self.step_tracker = StepTracer()

    def test_trace(self):
        step_tracer = self.step_tracker
        assert str(step_tracer) == ""

        cumulative_step: int = 0

        for step_type in StepType:
            step: int = random.randint(0, 100_000)
            cumulative_step += step
            step_tracer.add(step_type, step, cumulative_step)

        assert step_tracer.cumulative_step == cumulative_step
        assert len(step_tracer) == len(StepType)
