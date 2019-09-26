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

from iconservice.icon_constant import Revision, \
    PREP_MAIN_PREPS, ICX_IN_LOOP, ConfigKey, IISS_MIN_IREP, IISS_INITIAL_IREP, PREP_MAIN_AND_SUB_PREPS
from tests.integrate_test.iiss.test_iiss_base import TestIISSBase
from tests.integrate_test.test_integrate_base import TOTAL_SUPPLY


class TestIISSDecentralized2(TestIISSBase):
    CALCULATE_PERIOD = 10
    TERM_PERIOD = 8

    def _make_init_config(self) -> dict:
        return {
            ConfigKey.SERVICE: {
                ConfigKey.SERVICE_FEE: True
            },
            ConfigKey.IISS_CALCULATE_PERIOD: self.CALCULATE_PERIOD,
            ConfigKey.TERM_PERIOD: self.TERM_PERIOD,
            ConfigKey.IISS_META_DATA: {
                ConfigKey.UN_STAKE_LOCK_MIN: 10,
                ConfigKey.UN_STAKE_LOCK_MAX: 20
            },
            ConfigKey.PREP_REGISTRATION_FEE: 0
        }

    def _decentralized(self):
        total_supply = TOTAL_SUPPLY * ICX_IN_LOOP
        # Minimum_delegate_amount is 0.02 * total_supply
        # In this test delegate 0.03*total_supply because `Issue transaction` exists since REV_IISS
        minimum_delegate_amount_for_decentralization: int = total_supply * 2 // 1000 + 1
        init_balance: int = minimum_delegate_amount_for_decentralization * 2

        # distribute icx PREP_MAIN_PREPS ~ PREP_MAIN_PREPS + PREP_MAIN_PREPS - 1
        self.distribute_icx(accounts=self._accounts[PREP_MAIN_PREPS:PREP_MAIN_AND_SUB_PREPS],
                            init_balance=init_balance)

        # stake PREP_MAIN_PREPS ~ PREP_MAIN_PREPS + PREP_MAIN_PREPS - 1
        stake_amount: int = minimum_delegate_amount_for_decentralization
        tx_list: list = []
        for i in range(PREP_MAIN_PREPS):
            tx: dict = self.create_set_stake_tx(from_=self._accounts[PREP_MAIN_PREPS + i],
                                                value=stake_amount)
            tx_list.append(tx)
        self.process_confirm_block_tx(tx_list)

        # distribute icx for register PREP_MAIN_PREPS ~ PREP_MAIN_PREPS + PREP_MAIN_PREPS - 1
        self.distribute_icx(accounts=self._accounts[:PREP_MAIN_PREPS],
                            init_balance=3000 * ICX_IN_LOOP)

        # register PRep
        tx_list: list = []
        for account in self._accounts[:PREP_MAIN_PREPS]:
            tx: dict = self.create_register_prep_tx(from_=account)
            tx_list.append(tx)
        self.process_confirm_block_tx(tx_list)

        # delegate to PRep
        tx_list: list = []
        for i in range(PREP_MAIN_PREPS):
            tx: dict = self.create_set_delegation_tx(from_=self._accounts[PREP_MAIN_PREPS + i],
                                                     origin_delegations=[
                                                         (
                                                             self._accounts[i],
                                                             minimum_delegate_amount_for_decentralization
                                                         )
                                                     ])
            tx_list.append(tx)
        self.process_confirm_block_tx(tx_list)

        # get main prep
        response: dict = self.get_main_prep_list()
        expected_response: dict = {
            "preps": [],
            "totalDelegated": 0
        }
        self.assertEqual(expected_response, response)

        # set Revision REV_IISS (decentralization)
        self.set_revision(Revision.DECENTRALIZATION.value)

    def test_get_IISS_info(self):
        self.update_governance()

        # set Revision REV_IISS
        self.set_revision(Revision.IISS.value)

        block_height: int = self._block_height
        calc_period: int = self._config[ConfigKey.IISS_CALCULATE_PERIOD]

        # get iiss info
        response: dict = self.get_iiss_info()
        expected_response = {
            'blockHeight': block_height,
            'nextCalculation': block_height + calc_period + 1,
            'nextPRepTerm': 0,
            'variable': {
                "irep": 0,
                "rrep": 1200
            },
            'rcResult': {
            }
        }
        self.assertEqual(expected_response, response)

        block_height: int = self.make_blocks_to_end_calculation()
        self.make_blocks(self._block_height + 1)

        response: dict = self.get_iiss_info()
        expected_response = {
            'blockHeight': block_height + 1,
            'nextCalculation': block_height + calc_period + 1,
            'nextPRepTerm': 0,
            'variable': {
                "irep": 0,
                "rrep": 1200
            },
            'rcResult': {
                "iscore": 0,
                "estimatedICX": 0,
                "startBlockHeight": block_height - calc_period + 1,
                "endBlockHeight": block_height
            }
        }
        self.assertEqual(expected_response, response)

        self._decentralized()

        block_height: int = self.make_blocks_to_end_calculation()
        self.make_blocks(self._block_height + 1)

        prev_calc_period: int = calc_period

        response: dict = self.get_iiss_info()
        expected_response = {
            'blockHeight': block_height + 1,
            'nextCalculation': block_height + calc_period - 1,
            'nextPRepTerm': block_height + calc_period - 1,
            'variable': {
                'irep': 50000000000000000000000,
                'rrep': 1078
            },
            'rcResult': {
                "iscore": 0,
                "estimatedICX": 0,
                "startBlockHeight": block_height - prev_calc_period + 1,
                "endBlockHeight": block_height
            }
        }
        self.assertEqual(expected_response, response)
