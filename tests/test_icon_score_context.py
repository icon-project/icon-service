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


import unittest

from iconservice.iconscore.icon_score_context import IconScoreContext
from iconservice.iconscore.icon_score_context import IconScoreContextType
from iconservice.iconscore.icon_score_context import IconScoreContextFactory


class TestIconScoreContextFactory(unittest.TestCase):
    def setUp(self):
        self.factory = IconScoreContextFactory(max_size=2)

    def tearDown(self):
        self.factory = None

    def test_create_and_destroy(self):
        factory = self.factory
        self.assertEqual(0, len(factory._queue))

        for _ in range(3):
            context = factory.create(IconScoreContextType.QUERY)
            self.assertTrue(isinstance(context, IconScoreContext))
            self.assertEqual(0, len(factory._queue))
            self.assertTrue(context.readonly)
            factory.destroy(context)

        self.assertEqual(1, len(factory._queue))

        context = factory.create(IconScoreContextType.INVOKE)
        self.assertEqual(0, len(factory._queue))
        self.assertEqual(IconScoreContextType.INVOKE, context.type)
        self.factory.destroy(context)

        context = factory.create(IconScoreContextType.DIRECT)
        self.assertEqual(0, len(factory._queue))
        self.assertEqual(IconScoreContextType.DIRECT, context.type)
        self.factory.destroy(context)
