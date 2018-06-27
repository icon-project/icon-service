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
from inspect import isfunction, getmembers
from typing import Optional, List, Dict

from iconservice.iconscore.icon_score_api_generator import ScoreApiGenerator
from iconservice.iconscore.icon_score_base import external, IconScoreException


class TestScoreApiGenerator(unittest.TestCase):
    def setUp(self):
        self._members = getmembers(TestScore, predicate=isfunction)

    def test_internal_function(self):
        function_name = 'internal_function'
        functions = [value for key, value in self._members
                     if key == function_name]
        apis = ScoreApiGenerator.generate(functions)
        self.assertEqual(0, len(apis))

    def test_function_empty_param_empty_return(self):
        function_name = 'empty_param_empty_return'
        functions = [value for key, value in self._members
                     if key == function_name]
        api = ScoreApiGenerator.generate(functions)[0]
        self.assertEqual('function', api['type'])
        self.assertEqual(function_name, api['name'])
        self.assertEqual(0, len(api['inputs']))
        self.assertEqual(0, len(api['outputs']))

    def test_function_empty_param_str_return(self):
        function_name = 'empty_param_str_return'
        functions = [value for key, value in self._members
                     if key == function_name]
        api = ScoreApiGenerator.generate(functions)[0]
        self.assertEqual('function', api['type'])
        self.assertEqual(function_name, api['name'])
        self.assertEqual(0, len(api['inputs']))
        self.assertEqual(1, len(api['outputs']))
        self.assertEqual('str', api['outputs'][0]['type'])

    def test_function_inherited_str_param_empty_return(self):
        function_name = 'inherited_str_param_empty_return'
        functions = [value for key, value in self._members
                     if key == function_name]
        api = ScoreApiGenerator.generate(functions)[0]
        self.assertEqual('function', api['type'])
        self.assertEqual(function_name, api['name'])
        self.assertEqual(0, len(api['outputs']))
        self.assertEqual(1, len(api['inputs']))
        self.assertEqual('str', api['inputs'][0]['type'])

    def test_function_str_param_optional_return(self):
        function_name = 'str_param_optional_return'
        functions = [value for key, value in self._members
                     if key == function_name]
        api = ScoreApiGenerator.generate(functions)[0]
        self.assertEqual('function', api['type'])
        self.assertEqual(function_name, api['name'])
        self.assertEqual(1, len(api['inputs']))
        self.assertEqual('str', api['inputs'][0]['type'])
        self.assertEqual(1, len(api['outputs']))
        self.assertEqual('str', api['outputs'][0]['type'])

    def test_function_str_param_list_return(self):
        function_name = 'str_param_list_return'
        functions = [value for key, value in self._members
                     if key == function_name]
        api = ScoreApiGenerator.generate(functions)[0]
        self.assertEqual('function', api['type'])
        self.assertEqual(function_name, api['name'])
        self.assertEqual(1, len(api['inputs']))
        self.assertEqual('str', api['inputs'][0]['type'])
        self.assertEqual(1, len(api['outputs']))
        self.assertEqual('list', api['outputs'][0]['type'])

    def test_function_str_param_dict_return(self):
        function_name = 'str_param_dict_return'
        functions = [value for key, value in self._members
                     if key == function_name]
        api = ScoreApiGenerator.generate(functions)[0]
        self.assertEqual('function', api['type'])
        self.assertEqual(function_name, api['name'])
        self.assertEqual(1, len(api['inputs']))
        self.assertEqual('str', api['inputs'][0]['type'])
        self.assertEqual(1, len(api['outputs']))
        self.assertEqual('dict', api['outputs'][0]['type'])

    def test_function_list_param_empty_return(self):
        function_name = 'list_param_empty_return'
        functions = [value for key, value in self._members
                     if key == function_name]
        self.assertRaises(IconScoreException, ScoreApiGenerator.generate,
                          functions)

    def test_function_unsupported_param_empty_return(self):
        function_name = 'unsupported_param_empty_return'
        functions = [value for key, value in self._members
                     if key == function_name]
        self.assertRaises(IconScoreException, ScoreApiGenerator.generate,
                          functions)

    def test_function_str_param_unsupported_return(self):
        function_name = 'str_param_unsupported_return'
        functions = [value for key, value in self._members
                     if key == function_name]
        self.assertRaises(IconScoreException, ScoreApiGenerator.generate,
                          functions)

    def test_function_empty_param_unsupported_optional_return(self):
        function_name = 'empty_param_unsupported_optional_return'
        functions = [value for key, value in self._members
                     if key == function_name]
        self.assertRaises(IconScoreException, ScoreApiGenerator.generate,
                          functions)

    def test_return_bool(self):
        function_name = 'empty_param_bool_return'
        functions = [value for key, value in self._members
                     if key == function_name]
        api = ScoreApiGenerator.generate(functions)[0]
        self.assertEqual('bool', api['outputs'][0]['type'])

    def tearDown(self):
        self._members = None


class String(str):
    pass


class Decimal:
    pass


class TestScore:

    def internal_function(self):
        pass

    @external
    def empty_param_empty_return(self):
        pass

    @external
    def empty_param_str_return(self) -> str:
        pass

    @external
    def str_param_empty_return(self, name: str):
        pass

    @external
    def inherited_str_param_empty_return(self, name: String):
        pass

    @external
    def str_param_optional_return(self, name: String) -> Optional[String]:
        pass

    @external
    def str_param_list_return(self, name: String) -> List[str]:
        pass

    @external
    def str_param_dict_return(self, name: String) -> Dict[str, int]:
        pass

    @external
    def list_param_empty_return(self, name: list):
        pass

    @external
    def unsupported_param_empty_return(self, name: Decimal):
        pass

    @external
    def str_param_unsupported_return(self, name: str) -> Decimal:
        pass

    @external
    def empty_param_unsupported_optional_return(self) -> Optional[Decimal]:
        pass

    @external
    def empty_param_bool_return(self) -> bool:
        pass
