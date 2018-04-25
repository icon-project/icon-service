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


import unittest

from iconservice.iconscore.icon_score_context import IconScoreContext
from iconservice.iconscore.icon_score_context import IconScoreContextFactory


class TestIconScoreContextFactory(unittest.TestCase):
    def setUp(self):
        self.factory = IconScoreContextFactory(max_size=2)

    def tearDown(self):
        self.factory = None

    def test_create_and_destroy(self):
        factory = self.factory
        contexts = []

        for _ in range(3):
            context = factory.create()
            self.assertTrue(isinstance(context, IconScoreContext))
            self.assertEqual(0, len(factory._queue))
            contexts.append(context)

        for context in contexts:
            self.factory.destroy(context)

        self.assertEqual(2, len(factory._queue))

        context = factory.create()
        self.assertEqual(1, len(factory._queue))

        context = factory.create()
        self.assertEqual(0, len(factory._queue))
