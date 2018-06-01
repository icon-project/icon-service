#!/usr/bin/env python
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

from iconservice.logger import Logger
from iconservice.logger.logger import LogLevel


TAG = 'logger'


class TestLogger(unittest.TestCase):
    def setUp(self):
        Logger.import_dict('./tbears.json')

    def test_debug(self):
        Logger.set_log_level(LogLevel.DEBUG)
        Logger.debug('debug log')
        Logger.debug('debug log', TAG)
