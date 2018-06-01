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
import os.path

from iconservice.logger import Logger


TAG = 'logger'


class TestLogger(unittest.TestCase):
    def setUp(self):
        filePath = os.path.join(os.path.dirname(__file__), 'logger.json')
        Logger(filePath)

    def test_debug(self):
        Logger.debug('debug log')
        Logger.debug('debug log', TAG)

    def test_info(self):
        Logger.info('info log')
        Logger.info('info log', TAG)

    def test_warning(self):
        Logger.warning('warning log')
        Logger.warning('warning log', TAG)

    def test_error(self):
        Logger.error('error log')
        Logger.error('error log', TAG)


if __name__ == '__main__':
    unittest.main()
