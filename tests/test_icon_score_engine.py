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

from iconservice.iconscore.icon_score_engine import IconScoreEngine
from iconservice.iconscore.icon_score_info_mapper import IconScoreInfoMapper


class TestIconScoreEngine(unittest.TestCase):
    """
    def setUp(self):
        self._engine = IconScoreEngine()
        self._from = f'hx{"0" * 40}'
        self._to = f'hx{"1" * 40}'
        self._icon_score_address = f'cx{"2" * 40}'

    def tearDown(self):
        self._engine = None

    def test_invoke(self):
        address = self._icon_score_address
        method = 'transfer'
        params = {
            'from': self._from,
            'to': self._to,
            'value': 10 ** 18
        }

        ret = self._engine.invoke(address, method, params)
        self.assertTrue(ret)

    def test_query(self):
        address = self._icon_score_address
        method = 'balance_of'
        params = {
            'address': self._from
        }

        balance = self._engine.query(address, method, params)
        self.assertTrue(isinstance(balance, int))
        self.assertEqual(0, balance)
    """
