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
from typing import TYPE_CHECKING

from iconservice.base.address import GOVERNANCE_SCORE_ADDRESS
from iconservice.icon_constant import ConfigKey
from tests.integrate_test.iiss.test_iiss_base import TestIISSBase

if TYPE_CHECKING:
    pass


class TestIconNetworkValue(TestIISSBase):
    def _make_init_config(self) -> dict:
        config: dict = super()._make_init_config()
        config[ConfigKey.PREP_REGISTRATION_FEE] = 0
        return config

    def setUp(self):
        super().setUp()
        self.init_decentralized()

    def test_inv_step_price(self):
        self.make_blocks_to_end_calculation()

        step_price_old: int = self.query_score(from_=None,
                                               to_=GOVERNANCE_SCORE_ADDRESS,
                                               func_name="getStepPrice")

        self.update_governance(version="1_0_1", expected_status=True)

        self.score_call(from_=self._admin,
                        to_=GOVERNANCE_SCORE_ADDRESS,
                        func_name="set_step_price",
                        params={"value": hex(step_price_old * 2)},
                        expected_status=True)

        step_price: int = self.query_score(from_=None,
                                           to_=GOVERNANCE_SCORE_ADDRESS,
                                           func_name="getStepPrice")

        self.assertEqual(step_price_old * 2, step_price)
        self.make_blocks_to_end_calculation()
