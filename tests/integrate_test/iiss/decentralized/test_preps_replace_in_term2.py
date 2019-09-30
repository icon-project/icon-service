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

from iconservice.icon_constant import ICX_IN_LOOP, ConfigKey, Revision
from tests.integrate_test.iiss.test_iiss_base import TestIISSBase

if TYPE_CHECKING:
    pass


class TestPreps(TestIISSBase):
    calc_period: int = 15
    term_period: int = 45
    penalty_grace_period: int = 15
    low_productivity_penalty_threshold: int = 0
    block_validation_penalty_threshold: int = 2
    prep_main_preps: int = 5
    prep_main_and_sub_preps: int = 8
    decentralize_trigger: int = 0
    prep_registration_fee: int = 0

    def _make_init_config(self) -> dict:
        config: dict = {
            ConfigKey.SERVICE: {
                ConfigKey.SERVICE_FEE: True
            },
            ConfigKey.IISS_CALCULATE_PERIOD: self.calc_period,
            ConfigKey.TERM_PERIOD: self.term_period,
            ConfigKey.PENALTY_GRACE_PERIOD: self.penalty_grace_period,
            ConfigKey.LOW_PRODUCTIVITY_PENALTY_THRESHOLD: self.low_productivity_penalty_threshold,
            ConfigKey.BLOCK_VALIDATION_PENALTY_THRESHOLD: self.block_validation_penalty_threshold,
            ConfigKey.PREP_MAIN_PREPS: self.prep_main_preps,
            ConfigKey.PREP_MAIN_AND_SUB_PREPS: self.prep_main_and_sub_preps,
            ConfigKey.DECENTRALIZE_TRIGGER: self.decentralize_trigger,
            ConfigKey.PREP_REGISTRATION_FEE: self.prep_registration_fee
        }
        return config

    def _decentralized(self):
        self.update_governance()
        self.set_revision(Revision.IISS.value)

        self.distribute_icx(accounts=self._accounts[:self.prep_main_and_sub_preps],
                            init_balance=1 * ICX_IN_LOOP)

        tx_list = []
        for i in range(self.prep_main_and_sub_preps):
            tx = self.create_register_prep_tx(from_=self._accounts[i])
            tx_list.append(tx)
        self.process_confirm_block_tx(tx_list)

        self.set_revision(Revision.DECENTRALIZATION.value)

        self.make_blocks_to_end_calculation()

        response: dict = self.get_main_prep_list()
        expected_preps: list = []
        expected_total_delegated: int = 0
        for account in self._accounts[:self.prep_main_preps]:
            expected_preps.append({
                'address': account.address,
                'delegated': 0
            })
        expected_response: dict = {
            "preps": expected_preps,
            "totalDelegated": expected_total_delegated
        }
        self.assertEqual(expected_response, response)

    def test_preps_replace_in_term(self):
        self._decentralized()

        self.make_blocks(self._block_height + 1,
                         prev_block_generator=self._accounts[0].address,
                         prev_block_votes=
                         [[account.address, True] for i, account in enumerate(self._accounts[1:self.prep_main_preps])]
                         )

        response: dict = self.get_main_prep_list()
        expected_preps: list = []
        expected_total_delegated: int = 0
        for account in self._accounts[:self.prep_main_preps]:
            expected_preps.append({
                'address': account.address,
                'delegated': 0
            })
        expected_response: dict = {
            "preps": expected_preps,
            "totalDelegated": expected_total_delegated
        }
        self.assertEqual(expected_response, response)

        self.make_blocks(self._block_height + 2,
                         prev_block_generator=self._accounts[0].address,
                         prev_block_votes=
                         [[account.address, False] for i, account in enumerate(self._accounts[1:2])]
                         +
                         [[account.address, True] for i, account in enumerate(self._accounts[2:self.prep_main_preps])]
                         )
        response: dict = self.get_main_prep_list()
        expected_preps: list = []
        expected_total_delegated: int = 0
        expected_preps.append({
            'address': self._accounts[0].address,
            'delegated': 0
        })
        expected_preps.append({
            'address': self._accounts[self.prep_main_preps].address,
            'delegated': 0
        })
        for account in self._accounts[2:self.prep_main_preps]:
            expected_preps.append({
                'address': account.address,
                'delegated': 0
            })

        expected_response: dict = {
            "preps": expected_preps,
            "totalDelegated": expected_total_delegated
        }
        self.assertEqual(expected_response, response)

        self.make_blocks_to_end_calculation(prev_block_generator=self._accounts[0].address,
                                            prev_block_votes=
                                            [[account.address, True] for i, account in enumerate(self._accounts[2:self.prep_main_preps + 1])])

        response: dict = self.get_main_prep_list()
        expected_preps: list = []
        expected_total_delegated: int = 0
        for account in self._accounts[:self.prep_main_preps]:
            expected_preps.append({
                'address': account.address,
                'delegated': 0
            })
        expected_response: dict = {
            "preps": expected_preps,
            "totalDelegated": expected_total_delegated
        }
        self.assertEqual(expected_response, response)

        self.make_blocks(self._block_height + 2,
                         prev_block_generator=self._accounts[0].address,
                         prev_block_votes=
                         [[account.address, False] for i, account in enumerate(self._accounts[1:2])]
                         +
                         [[account.address, True] for i, account in enumerate(self._accounts[2:self.prep_main_preps])]
                         )

        response: dict = self.get_main_prep_list()
        expected_preps: list = []
        expected_total_delegated: int = 0
        expected_preps.append({
            'address': self._accounts[0].address,
            'delegated': 0
        })
        expected_preps.append({
            'address': self._accounts[self.prep_main_preps].address,
            'delegated': 0
        })
        for account in self._accounts[2:self.prep_main_preps]:
            expected_preps.append({
                'address': account.address,
                'delegated': 0
            })

        expected_response: dict = {
            "preps": expected_preps,
            "totalDelegated": expected_total_delegated
        }
        self.assertEqual(expected_response, response)