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

from typing import TYPE_CHECKING, List

from iconservice.base.address import Address
from iconservice.icon_constant import *
from tests.integrate_test.iiss.test_iiss_base import TestIISSBase

if TYPE_CHECKING:
    from iconservice.iconscore.icon_score_result import TransactionResult


CALC_PERIOD = 22


class TestCPS(TestIISSBase):
    def _make_init_config(self) -> dict:
        config: dict = super()._make_init_config()
        config[ConfigKey.PREP_REGISTRATION_FEE] = 0
        config[ConfigKey.IISS_CALCULATE_PERIOD] = CALC_PERIOD
        config[ConfigKey.TERM_PERIOD] = CALC_PERIOD
        return config

    def setUp(self):
        super().setUp()
        self.init_decentralized()
        self.init_inv()

        self.distribute_icx(
            accounts=self._accounts[:100],
            init_balance=1_000_000 * ICX_IN_LOOP
        )

    def test_deploy(self):
        cps_owner: 'Address' = self._accounts[0]

        tx_results: List['TransactionResult'] = self.deploy_score(
            score_root="sample_scores",
            score_name="cps/CPFTreasury",
            from_=cps_owner,
            deploy_params={}
        )
        cpf_treasury: 'Address' = tx_results[0].score_address

        tx_results: List['TransactionResult'] = self.deploy_score(
            score_root="sample_scores",
            score_name="cps/CPSTreasury",
            from_=cps_owner,
            deploy_params={}
        )
        cps_treasury: 'Address' = tx_results[0].score_address
