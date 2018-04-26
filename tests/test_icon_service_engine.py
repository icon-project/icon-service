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


import os
import shutil
import unittest

from iconservice.base.address import Address
from iconservice.icon_service_engine import IconServiceEngine


class TestIconServiceEngine(unittest.TestCase):
    def setUp(self):
        self._state_db_root_path = 'dbs'
        self._icon_score_root_path = 'scores'

        engine = IconServiceEngine()
        engine.open(icon_score_root_path=self._icon_score_root_path,
                    state_db_root_path=self._state_db_root_path)
        self._engine = engine
        self._from = Address.from_string(f'hx{"0" * 40}')
        self._to = Address.from_string(f'hx{"1" * 40}')
        self._icon_score_address = Address.from_string(f'cx{"2" * 40}')

    def tearDown(self):
        self._engine.close()
        shutil.rmtree(self._icon_score_root_path)
        shutil.rmtree(self._state_db_root_path)

    def test_icx_get_balance(self):
        method = 'icx_getBalance'
        params = {'address': self._from}

        balance = self._engine.call(method, params)
        self.assertTrue(isinstance(balance, int))
        self.assertEqual(0, balance)

    def test_icx_transfer(self):
        method = 'icx_sendTransaction'
        params = {
            'from': self._from,
            'to': self._to,
            'value': 2 * 10 ** 18,
            'fee': 10 ** 16,
            'tx_hash': '4bf74e6aeeb43bde5dc8d5b62537a33ac8eb7605ebbdb51b015c1881b45b3aed',
            'signature': 'VAia7YZ2Ji6igKWzjR2YsGa2m53nKPrfK7uXYW78QLE+ATehAVZPC40szvAiA6NEU5gCYB4c4qaQzqDh2ugcHgA='
        }

        ret = self._engine.call(method, params)
        self.assertIsNone(ret)

    '''
    def test_score_invoke(self):
        method = 'icx_sendTransaction'
        params = {
            'from': self._from,
            'to': self._icon_score_address,
            'value': 0,
            'fee': 10 ** 16,
            'tx_hash': '4bf74e6aeeb43bde5dc8d5b62537a33ac8eb7605ebbdb51b015c1881b45b3aed',
            'signature': 'VAia7YZ2Ji6igKWzjR2YsGa2m53nKPrfK7uXYW78QLE+ATehAVZPC40szvAiA6NEU5gCYB4c4qaQzqDh2ugcHgA=',
            'data': {
                'method': 'transfer',
                'params': {
                    'to': self._to,
                    'value': 777
                }
            }
        }

        ret = self._engine.call(method, params)
        self.assertTrue(ret)
    '''

    '''
    def test_score_query(self):
        method = 'icx_call'
        params = {
            'from': self._from,
            'to': self._icon_score_address,
            'value': 10 ** 18,
            'data': {
                'method': 'balance_of',
                'params': {
                    'address': self._from
                }
            }
        }

        balance = self._engine.call(method, params)
        self.assertTrue(isinstance(balance, int))
        self.assertEqual(0, balance)
    '''
