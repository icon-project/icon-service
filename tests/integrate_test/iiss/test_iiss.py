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

"""Test for icon_score_base.py and icon_score_base2.py"""

import unittest

from iconservice.icon_constant import REV_IISS, ConfigKey
from tests.integrate_test.iiss.test_iiss_base import TestIISSBase


class TestIISS(TestIISSBase):
    def test_get_IISS_info(self):
        self.update_governance()

        # set Revision REV_IISS
        tx: dict = self.create_set_revision_tx(REV_IISS)
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)

        term_period: int = self._config[ConfigKey.TERM_PERIOD]
        block_height: int = self._block_height

        # get iiss info
        response: dict = self.get_iiss_info()
        expected_response = {
            'nextCalculation': block_height + term_period,
            'nextPRepTerm': 0,
            'variable': {
                "irep": self._config[ConfigKey.INITIAL_IREP],
                "rrep": 1200
            }
        }
        self.assertEqual(expected_response, response)


if __name__ == '__main__':
    unittest.main()
