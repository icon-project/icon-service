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

import pytest

from iconservice.base.address import Address
from iconservice.base.address import ZERO_SCORE_ADDRESS
from iconservice.icon_constant import ConfigKey, PRepGrade
from iconservice.icon_constant import PREP_MAIN_PREPS, PREP_MAIN_AND_SUB_PREPS
from iconservice.base.exception import ScoreNotFoundException
from iconservice.iconscore.icon_score_context import IconScoreContext
from iconservice.utils import icx_to_loop
from tests.integrate_test.iiss.test_iiss_base import TestIISSBase
from tests.integrate_test.test_integrate_base import EOAAccount

if TYPE_CHECKING:
    from iconservice.base.block import Block
    from iconservice.iconscore.icon_score_result import TransactionResult


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
        # Prevent icon_service_engine from sending RollbackRequest to rc
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
        self._rollback(prev_block)

        # Check if the balances of accounts are reverted
        for account in accounts:
            balance: int = self.get_balance(account.address)
            assert balance == 0

        # Check the last block
        self._check_if_last_block_is_reverted(prev_block)

    def test_rollback_score_deploy(self):
        # Prevent icon_service_engine from sending RollbackRequest to rc
        IconScoreContext.engine.iiss.rollback_reward_calculator = Mock()

        init_balance = icx_to_loop(100)
        deploy_step_limit = 2 * 10 ** 9
        sender_account: 'EOAAccount' = self.create_eoa_account()
        sender_address: 'Address' = sender_account.address

        # Transfer 10 ICX to sender_account
        self.distribute_icx([sender_account], init_balance=init_balance)

        # Save the balance of sender address
        balance: int = self.get_balance(sender_address)
        assert init_balance == balance

        # Save the previous block
        prev_block: 'Block' = self.icon_service_engine._get_last_block()

        # Deploy a SCORE
        tx: dict = self.create_deploy_score_tx(score_root="sample_deploy_scores",
                                               score_name="install/sample_score",
                                               from_=sender_address,
                                               to_=ZERO_SCORE_ADDRESS,
                                               step_limit=deploy_step_limit)
        tx_results: List['TransactionResult'] = self.process_confirm_block(tx_list=[tx])

        # Skip tx_result[0]. It is the result of a base transaction
        tx_result: 'TransactionResult' = tx_results[1]
        score_address: 'Address' = tx_result.score_address
        assert isinstance(score_address, Address)
        assert score_address.is_contract

        # Check if the score works well with a query request
        response = self.query_score(from_=sender_address, to_=score_address, func_name="hello")
        assert response == "Hello"

        # Check the balance is reduced
        balance: int = self.get_balance(sender_address)
        assert init_balance == balance + tx_result.step_price * tx_result.step_used

        # Rollback: Go back to the block where a score has not been deployed yet
        self._rollback(prev_block)

        # Check if the score deployment is revoked successfully
        with pytest.raises(ScoreNotFoundException):
            self.query_score(from_=sender_address, to_=score_address, func_name="hello")

        # Check if the balance of sender address is revoked
        balance: int = self.get_balance(sender_address)
        assert init_balance == balance

        # Deploy the same SCORE again
        tx: dict = self.create_deploy_score_tx(score_root="sample_deploy_scores",
                                               score_name="install/sample_score",
                                               from_=sender_address,
                                               to_=ZERO_SCORE_ADDRESS,
                                               step_limit=deploy_step_limit)
        tx_results: List['TransactionResult'] = self.process_confirm_block(tx_list=[tx])

        # Skip tx_result[0]. It is the result of a base transaction
        tx_result: 'TransactionResult' = tx_results[1]
        new_score_address = tx_result.score_address
        assert isinstance(score_address, Address)
        assert new_score_address.is_contract
        assert score_address != new_score_address

        # Check if the score works well with a query request
        response = self.query_score(from_=sender_address, to_=new_score_address, func_name="hello")
        assert response == "Hello"

    def test_rollback_score_state(self):
        # Prevent icon_service_engine from sending RollbackRequest to rc
        IconScoreContext.engine.iiss.rollback_reward_calculator = Mock()

        init_balance = icx_to_loop(100)
        deploy_step_limit = 2 * 10 ** 9
        sender_account: 'EOAAccount' = self.create_eoa_account()
        sender_address: 'Address' = sender_account.address
        score_value = 1234
        deploy_params = {"value": hex(score_value)}

        # Transfer 10 ICX to sender_account
        self.distribute_icx([sender_account], init_balance=init_balance)

        # Save the balance of sender address
        balance: int = self.get_balance(sender_address)
        assert init_balance == balance

        # Deploy a SCORE
        tx: dict = self.create_deploy_score_tx(score_root="sample_deploy_scores",
                                               score_name="install/sample_score",
                                               from_=sender_address,
                                               to_=ZERO_SCORE_ADDRESS,
                                               deploy_params=deploy_params,
                                               step_limit=deploy_step_limit)
        tx_results: List['TransactionResult'] = self.process_confirm_block(tx_list=[tx])

        # Skip tx_result[0]. It is the result of a base transaction
        tx_result: 'TransactionResult' = tx_results[1]
        score_address: 'Address' = tx_result.score_address
        assert isinstance(score_address, Address)
        assert score_address.is_contract

        # Check if the score works well with a query request
        response = self.query_score(from_=sender_address, to_=score_address, func_name="get_value")
        assert response == score_value

        # Check the balance is reduced
        balance: int = self.get_balance(sender_address)
        assert init_balance == balance + tx_result.step_price * tx_result.step_used

        # Save the previous block
        prev_block: 'Block' = self.icon_service_engine._get_last_block()

        # Send a transaction to change the score state
        old_balance = balance
        tx_results: List['TransactionResult'] = self.score_call(from_=sender_address,
                                                                to_=score_address,
                                                                func_name="increase_value",
                                                                step_limit=10 ** 8,
                                                                expected_status=True)

        tx_result: 'TransactionResult' = tx_results[1]
        assert tx_result.step_used > 0
        assert tx_result.step_price > 0
        assert tx_result.to == score_address

        balance: int = self.get_balance(sender_address)
        assert old_balance == balance + tx_result.step_used * tx_result.step_price

        # Check if the score works well with a query request
        response = self.query_score(from_=sender_address, to_=score_address, func_name="get_value")
        assert response == score_value + 1

        # Rollback: Go back to the block where a score has not been deployed yet
        self._rollback(prev_block)

        # Check if the score state is reverted
        response = self.query_score(from_=sender_address, to_=score_address, func_name="get_value")
        assert response == score_value

    def test_rollback_register_prep(self):
        # Prevent icon_service_engine from sending RollbackRequest to rc
        IconScoreContext.engine.iiss.rollback_reward_calculator = Mock()

        accounts: List['EOAAccount'] = self.create_eoa_accounts(1)
        self.distribute_icx(accounts=accounts, init_balance=icx_to_loop(3000))

        # Keep the previous states in order to compare with the rollback result
        prev_get_preps: dict = self.get_prep_list()
        prev_block: 'Block' = self.icon_service_engine._get_last_block()

        # Register a new P-Rep
        transactions = []
        for i, account in enumerate(accounts):
            # Register a P-Rep
            tx = self.create_register_prep_tx(from_=account)
            transactions.append(tx)
        self.process_confirm_block_tx(transactions)

        # Check whether a registerPRep tx is done
        current_get_preps: dict = self.get_prep_list()
        assert current_get_preps["blockHeight"] == prev_block.height + 1
        assert len(current_get_preps["preps"]) == len(prev_get_preps["preps"]) + 1

        # Rollback
        self._rollback(prev_block)

        current_get_preps: dict = self.get_prep_list()
        assert current_get_preps == prev_get_preps

        self._check_if_last_block_is_reverted(prev_block)

    def test_rollback_set_delegation(self):
        # Prevent icon_service_engine from sending RollbackRequest to rc
        IconScoreContext.engine.iiss.rollback_reward_calculator = Mock()

        accounts: List['EOAAccount'] = self.create_eoa_accounts(1)
        self.distribute_icx(accounts=accounts, init_balance=icx_to_loop(3000))
        user_account = accounts[0]

        # Keep the previous states in order to compare with the rollback result
        prev_get_preps: dict = self.get_prep_list()
        prev_block: 'Block' = self.icon_service_engine._get_last_block()

        # Move 22th P-Rep up to 1st with setDelegation
        delegating: int = icx_to_loop(1)
        transactions = []
        for i, account in enumerate(accounts):
            # Stake 100 icx
            tx = self.create_set_stake_tx(from_=user_account, value=icx_to_loop(100))
            transactions.append(tx)

            # Delegate 1 icx to itself
            tx = self.create_set_delegation_tx(
                from_=account,
                origin_delegations=[
                    (self._accounts[PREP_MAIN_PREPS - 1], delegating)
                ]
            )
            transactions.append(tx)
        self.process_confirm_block_tx(transactions)

        # Check whether a setDelegation tx is done
        current_get_preps: dict = self.get_prep_list()
        assert current_get_preps["blockHeight"] == prev_block.height + 1

        prev_prep_info: dict = prev_get_preps["preps"][PREP_MAIN_PREPS - 1]
        current_prep_info: dict = current_get_preps["preps"][0]
        for field in prev_prep_info:
            if field == "delegated":
                assert prev_prep_info[field] == current_prep_info[field] - delegating
            else:
                assert prev_prep_info[field] == current_prep_info[field]

        # Rollback
        self._rollback(prev_block)

        current_get_preps: dict = self.get_prep_list()
        assert current_get_preps == prev_get_preps

        self._check_if_last_block_is_reverted(prev_block)

    def _rollback(self, block: 'Block'):
        super().rollback(block.height, block.hash)
        self._check_if_rollback_reward_calculator_is_called(block)
        self._check_if_last_block_is_reverted(block)

    def _check_if_last_block_is_reverted(self, prev_block: 'Block'):
        """After rollback, last_block should be the same as prev_block

        :param prev_block:
        :return:
        """
        last_block: 'Block' = self.icon_service_engine._get_last_block()
        assert last_block == prev_block

    @staticmethod
    def _check_if_rollback_reward_calculator_is_called(block: 'Block'):
        IconScoreContext.engine.iiss.rollback_reward_calculator.assert_called_with(
            block.height, block.hash)
