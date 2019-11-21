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
from enum import Enum
from typing import TYPE_CHECKING, List, Dict
from unittest.mock import Mock

from iconservice.icon_constant import ConfigKey, PRepGrade
from iconservice.icon_constant import PREP_MAIN_PREPS, PREP_MAIN_AND_SUB_PREPS
from iconservice.iconscore.icon_score_context import IconScoreContext
from iconservice.utils import icx_to_loop
from tests.integrate_test.iiss.test_iiss_base import TestIISSBase
from tests.integrate_test.test_integrate_base import EOAAccount

if TYPE_CHECKING:
    from iconservice.base.address import Address
    from iconservice.base.block import Block


def _check_elected_prep_grades(preps: List[Dict[str, int]],
                               main_prep_count: int,
                               elected_prep_count: int):
    for i, prep in enumerate(preps):
        if i < main_prep_count:
            assert prep["grade"] == PRepGrade.MAIN.value
        elif i < elected_prep_count:
            assert prep["grade"] == PRepGrade.SUB.value
        else:
            assert prep["grade"] == PRepGrade.CANDIDATE.value


def _get_main_preps(preps: List[Dict[str, 'Address']], main_prep_count: int) -> List['Address']:
    main_preps: List['Address'] = []

    for i, prep in enumerate(preps):
        if i >= main_prep_count:
            break

        main_preps.append(prep["address"])

    return main_preps


class ProposalType(Enum):
    TEXT = 0
    REVISION = 1
    MALICIOUS_SCORE = 2
    PREP_DISQUALIFICATION = 3
    STEP_PRICE = 4


class TestRollback(TestIISSBase):
    MAIN_PREP_COUNT = PREP_MAIN_PREPS
    ELECTED_PREP_COUNT = PREP_MAIN_AND_SUB_PREPS
    CALCULATE_PERIOD = MAIN_PREP_COUNT
    TERM_PERIOD = MAIN_PREP_COUNT
    BLOCK_VALIDATION_PENALTY_THRESHOLD = 10
    LOW_PRODUCTIVITY_PENALTY_THRESHOLD = 80
    PENALTY_GRACE_PERIOD = CALCULATE_PERIOD * 2 + BLOCK_VALIDATION_PENALTY_THRESHOLD

    def _make_init_config(self) -> dict:
        return {
            ConfigKey.SERVICE: {
                ConfigKey.SERVICE_FEE: True
            },
            ConfigKey.IISS_META_DATA: {
                ConfigKey.UN_STAKE_LOCK_MIN: 10,
                ConfigKey.UN_STAKE_LOCK_MAX: 20
            },
            ConfigKey.IISS_CALCULATE_PERIOD: self.CALCULATE_PERIOD,
            ConfigKey.TERM_PERIOD: self.TERM_PERIOD,
            ConfigKey.BLOCK_VALIDATION_PENALTY_THRESHOLD: self.BLOCK_VALIDATION_PENALTY_THRESHOLD,
            ConfigKey.LOW_PRODUCTIVITY_PENALTY_THRESHOLD: self.LOW_PRODUCTIVITY_PENALTY_THRESHOLD,
            ConfigKey.PREP_MAIN_PREPS: self.MAIN_PREP_COUNT,
            ConfigKey.PREP_MAIN_AND_SUB_PREPS: self.ELECTED_PREP_COUNT,
            ConfigKey.PENALTY_GRACE_PERIOD: self.PENALTY_GRACE_PERIOD
        }

    def setUp(self):
        super().setUp()
        self.init_decentralized()

        # get main prep
        response: dict = self.get_main_prep_list()
        expected_preps: list = []
        for account in self._accounts[:PREP_MAIN_PREPS]:
            expected_preps.append({
                'address': account.address,
                'delegated': 0
            })
        expected_response: dict = {
            "preps": expected_preps,
            "totalDelegated": 0
        }
        self.assertEqual(expected_response, response)

    def test_rollback_icx_transfer(self):
        """
        scenario 1
            when it starts new preps on new term, normal case, while 100 block.
        expected :
            all new preps have maintained until 100 block because it already passed GRACE_PERIOD
        """
        IconScoreContext.engine.iiss.rollback_reward_calculator = Mock()

        # Inspect the current term
        response = self.get_prep_term()
        assert response["sequence"] == 2

        prev_block: 'Block' = self.icon_service_engine._get_last_block()

        # Transfer 3000 icx to new 10 accounts
        init_balance = icx_to_loop(3000)
        accounts: List['EOAAccount'] = self.create_eoa_accounts(10)
        self.distribute_icx(accounts=accounts, init_balance=init_balance)

        for account in accounts:
            balance: int = self.get_balance(account.address)
            assert balance == init_balance

        # Rollback the state to the previous block height
        self.icon_service_engine.rollback(prev_block.height, prev_block.hash)
        IconScoreContext.engine.iiss.rollback_reward_calculator.assert_called_with(
            prev_block.height, prev_block.hash)

        # Check if the balances of accounts are reverted
        for account in accounts:
            balance: int = self.get_balance(account.address)
            assert balance == 0

        # Check the last block
        self._check_if_last_block_is_reverted(prev_block)

    def test_rollback_score_deploy(self):
        pass

    def _check_if_last_block_is_reverted(self, prev_block: 'Block'):
        """After rollback, last_block should be the same as prev_block

        :param prev_block:
        :return:
        """
        last_block: 'Block' = self.icon_service_engine._get_last_block()
        assert last_block == prev_block
