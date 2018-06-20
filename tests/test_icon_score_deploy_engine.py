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

from iconservice.deploy.icon_score_deploy_engine import IconScoreDeployEngine


class MockScore(object):
    def __init__(self, test_case: unittest.TestCase):
        self._test_case = test_case

    def on_install(self, test1: int = 1, test2: str = 'a'):
        self._test_case.assertEqual(test1, 100)
        self._test_case.assertEqual(test2, 'hello')


class TestScoreDeployEngine(unittest.TestCase):
    def setUp(self):
        icx_storage = None
        icon_score_mapper = None
        flags = IconScoreDeployEngine.Flag.ENABLE_DEPLOY_AUDIT
        self.engine = IconScoreDeployEngine(
            icon_score_root_path='./score',
            flags=flags,
            icx_storage=icx_storage,
            icon_score_mapper=icon_score_mapper)

    def tearDown(self):
        pass

    def test_is_data_type_supported(self):
        data_types = [
            'install', 'update', 'audit', 'call', 'message', '', None
        ]
        results = [True, True, True, False, False, False]

        for data_type, results in zip(data_types, results):
            self.assertEqual(
                results, self.engine.is_data_type_supported(data_type))

    def test_call_on_init_of_score(self):
        params = {
            'test1': '100',
            'test2': 'hello'
        }
        score = MockScore(self)
        self.engine._call_on_init_of_score(None, score.on_install, params)
