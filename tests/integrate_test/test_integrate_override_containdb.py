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

"""IconScoreEngine testcase
"""

import unittest

from iconservice.base.address import ZERO_SCORE_ADDRESS
from tests import raise_exception_start_tag, raise_exception_end_tag
from tests.integrate_test.test_integrate_base import TestIntegrateBase


class TestIntegrateOverrideContainDB(TestIntegrateBase):

    def test_success(self):
        deploy_list = [
            'override/success',
        ]

        tx_list = [self._make_deploy_tx('test_deploy_scores', deploy_name,
                                        self._addr_array[0], ZERO_SCORE_ADDRESS)
                   for deploy_name in deploy_list]

        prev_block, tx_results = self._make_and_req_block(tx_list)

        self._write_precommit_state(prev_block)

        for tx_result in tx_results:
            self.assertEqual(tx_result.status, int(True))

    def test_override(self):
        deploy_list = [
            'override/owner',
            'override/owner_sub',
            'override/owner_sub2',
            'override/inner_func',
            'override/inner_func_static',
            'override/inner_setattr'
        ]

        tx_list = [self._make_deploy_tx('test_deploy_scores', deploy_name,
                                        self._addr_array[0], ZERO_SCORE_ADDRESS)
                   for deploy_name in deploy_list]

        raise_exception_start_tag("test_override")
        prev_block, tx_results = self._make_and_req_block(tx_list)
        raise_exception_end_tag("test_override")

        self._write_precommit_state(prev_block)

        for tx_result in tx_results:
            self.assertEqual(tx_result.status, int(False))


if __name__ == '__main__':
    unittest.main()
