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

"""
IconScoreEngine Test Cases
Added checking if getPRepTerm API returns not only main and sub P-Reps but inactive ones.

"""
from enum import Enum
from typing import TYPE_CHECKING, List, Dict

from iconservice.icon_constant import ConfigKey, PRepGrade, PenaltyReason, PRepStatus
from iconservice.icon_constant import PREP_MAIN_PREPS, PREP_MAIN_AND_SUB_PREPS
from iconservice.iconscore.icon_score_result import TransactionResult
from iconservice.utils import icx_to_loop
from tests.integrate_test.iiss.test_iiss_base import TestIISSBase
from tests.integrate_test.test_integrate_base import EOAAccount

if TYPE_CHECKING:
    from iconservice.base.address import Address


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


class TestPreps(TestIISSBase):
    MAIN_PREP_COUNT = PREP_MAIN_PREPS
    ELECTED_PREP_COUNT = PREP_MAIN_AND_SUB_PREPS
    CALCULATE_PERIOD = MAIN_PREP_COUNT
    TERM_PERIOD = MAIN_PREP_COUNT
    BLOCK_VALIDATION_PENALTY_THRESHOLD = 10
    LOW_PRODUCTIVITY_PENALTY_THRESHOLD = 80
    PENALTY_GRACE_PERIOD = CALCULATE_PERIOD * 2 + BLOCK_VALIDATION_PENALTY_THRESHOLD

    def _check_preps_on_get_prep_term(self, added_inactive_preps: List[Dict[str, str]]):
        """
        Return bool value
        checking if not only main P-Reps and sub ones but input added inactive preps are preps of 'getPRepTerm' API

        :param added_inactive_preps: expected added inactive prep list
        :return: bool
        """
        preps = self.get_prep_term()["preps"]
        main_preps = self.get_main_prep_list()["preps"]
        sub_preps = self.get_sub_prep_list()["preps"]
        tmp_preps = main_preps + sub_preps
        expected_preps = []
        for prep in tmp_preps:
            expected_preps.append(self.get_prep(prep["address"]))

        preps_on_block_validation_penalty = \
            sorted(added_inactive_preps,
                   key=lambda x: (-x["delegated"], x["blockHeight"], x["txIndex"]))
        expected_preps.extend(preps_on_block_validation_penalty)
        assert expected_preps == preps

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
        self.init_decentralized(network_proposal=True)

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

    def test_replace_prep(self):
        """
        scenario 1
            when it starts new preps on new term, normal case, while 100 block.
        expected :
            all new preps have maintained until 100 block because it already passed GRACE_PERIOD
        """
        main_prep_count = PREP_MAIN_PREPS
        elected_prep_count = PREP_MAIN_AND_SUB_PREPS
        total_prep_count = elected_prep_count * 2
        calculate_period = self.CALCULATE_PERIOD

        # Inspect the current term
        response = self.get_prep_term()
        assert response["sequence"] == 2

        self.distribute_icx(accounts=self._accounts[:PREP_MAIN_PREPS],
                            init_balance=icx_to_loop(1))

        # Distribute 3000 icx to new 100 accounts
        accounts: List['EOAAccount'] = self.create_eoa_accounts(total_prep_count)
        self.distribute_icx(accounts=accounts, init_balance=icx_to_loop(3000))

        transactions = []
        for i, account in enumerate(accounts):
            # Register a P-Rep
            tx = self.create_register_prep_tx(from_=account)
            transactions.append(tx)

            # Stake 100 icx
            tx = self.create_set_stake_tx(from_=account, value=icx_to_loop(100))
            transactions.append(tx)

            # Delegate 1 icx to itself
            tx = self.create_set_delegation_tx(
                from_=account,
                origin_delegations=[
                    (account, icx_to_loop(1))
                ]
            )
            transactions.append(tx)
        self.process_confirm_block_tx(transactions)

        self.make_blocks_to_end_calculation()
        self.make_empty_blocks(1)

        # TERM-3: Nothing
        term_3: dict = self.get_prep_term()
        assert term_3["sequence"] == 3
        preps = term_3["preps"]

        _check_elected_prep_grades(preps, main_prep_count, elected_prep_count)
        main_preps_3: List['Address'] = _get_main_preps(preps, main_prep_count)

        assert term_3["totalDelegated"] == icx_to_loop(1) * total_prep_count

        # Check if block validation statistics works well
        self.make_empty_blocks(
            count=calculate_period,
            prev_block_generator=main_preps_3[0],
            prev_block_validators=[address for address in main_preps_3[1:]]
        )

        # All main P-Reps succeeded to validate all blocks in a term
        for i, address in enumerate(main_preps_3):
            assert address == accounts[i].address

            response = self.get_prep(address)
            assert response["totalBlocks"] == calculate_period
            assert response["validatedBlocks"] == calculate_period
            assert response["unvalidatedSequenceBlocks"] == 0

        # TERM-4: Block validation penalty -----------------------------------------
        account_on_block_validation_penalty: 'EOAAccount' = accounts[1]

        term_4: dict = self.get_prep_term()
        assert term_4["sequence"] == 4
        preps = term_4["preps"]

        _check_elected_prep_grades(preps, main_prep_count, elected_prep_count)
        main_preps_4: List['Address'] = _get_main_preps(preps, main_prep_count)
        assert main_preps_3 == main_preps_4

        self.make_empty_blocks(
            count=self.BLOCK_VALIDATION_PENALTY_THRESHOLD + 1,
            prev_block_generator=main_preps_4[0],
            prev_block_validators=[
                address for address in main_preps_4[1:]
                if address != account_on_block_validation_penalty.address
            ]
        )

        term_4: dict = self.get_prep_term()
        assert term_4["sequence"] == 4
        preps = term_4["preps"]

        # A main P-Rep got penalized for consecutive 660 block validation failure
        _check_elected_prep_grades(preps, main_prep_count, elected_prep_count - 1)
        main_preps_4: List['Address'] = _get_main_preps(preps, main_prep_count)

        # The first sub P-Rep replaced the the second main P-Rep
        assert main_preps_4[1] == accounts[main_prep_count].address
        assert main_preps_4[1] != account_on_block_validation_penalty
        prep_on_penalty: dict = self.get_prep(account_on_block_validation_penalty.address)

        assert prep_on_penalty["status"] == PRepStatus.ACTIVE.value
        assert prep_on_penalty["penalty"] == PenaltyReason.BLOCK_VALIDATION.value
        assert prep_on_penalty["unvalidatedSequenceBlocks"] == self.BLOCK_VALIDATION_PENALTY_THRESHOLD + 1
        assert prep_on_penalty["totalBlocks"] == \
            prep_on_penalty["validatedBlocks"] + \
            prep_on_penalty["unvalidatedSequenceBlocks"]

        # checks if adding the prep receiving a block validation penalty on preps of getPRepTerm API
        self._check_preps_on_get_prep_term([prep_on_penalty])

        count = term_4["endBlockHeight"] - term_4["blockHeight"] + 1
        self.make_empty_blocks(
            count=count,
            prev_block_generator=main_preps_4[0],
            prev_block_validators=main_preps_4[1:]
        )

        # Term-5: Unregister P-Rep
        # accounts[1] prep returns to the main P-Rep group
        term_5 = self.get_prep_term()
        assert term_5["sequence"] == 5
        preps = term_5["preps"]

        _check_elected_prep_grades(preps, main_prep_count, elected_prep_count)
        main_preps_5: List['Address'] = _get_main_preps(preps, main_prep_count)
        assert main_preps_5[1] == account_on_block_validation_penalty.address

        prep = self.get_prep(account_on_block_validation_penalty.address)
        assert prep["penalty"] == PenaltyReason.NONE.value
        assert prep["unvalidatedSequenceBlocks"] == 0
        assert prep["grade"] == PRepGrade.MAIN.value
        assert prep["totalBlocks"] == prep_on_penalty["totalBlocks"]
        assert prep["validatedBlocks"] == prep_on_penalty["validatedBlocks"]

        index = 2
        unregistered_account = accounts[index]
        assert main_preps_5[index] == accounts[index].address

        self.unregister_prep(unregistered_account,
                             expected_status=True,
                             prev_block_generator=main_preps_5[0],
                             prev_block_validators=main_preps_5)

        # Changed main P-Rep list are applied to the next block
        self.make_empty_blocks(1,
                               prev_block_generator=main_preps_5[0],
                               prev_block_validators=[
                                   address for address in main_preps_5 if address != unregistered_account
                               ])

        unregistered_prep: dict = self.get_prep(unregistered_account.address)
        assert unregistered_prep["status"] == PRepStatus.UNREGISTERED.value
        assert unregistered_prep["grade"] == PRepGrade.CANDIDATE.value
        assert unregistered_prep["penalty"] == PenaltyReason.NONE.value

        term_5 = self.get_prep_term()
        preps = term_5["preps"]

        # checks if adding the unregistered prep on preps of getPRepTerm API (1)
        self._check_preps_on_get_prep_term([])

        _check_elected_prep_grades(preps, main_prep_count, elected_prep_count - 1)
        main_preps_5: List['Address'] = _get_main_preps(preps, main_prep_count)

        assert preps[index]["address"] != unregistered_account.address
        assert preps[index]["address"] == accounts[main_prep_count].address

        count = term_5["endBlockHeight"] - term_5["blockHeight"] + 1
        self.make_empty_blocks(count,
                               prev_block_generator=main_preps_5[0],
                               prev_block_validators=[prep for prep in main_preps_5])

        # TERM-6: Low productivity penalty
        account_on_low_productivity_penalty: 'EOAAccount' = account_on_block_validation_penalty

        term_6 = self.get_prep_term()
        assert term_6["sequence"] == 6
        preps = term_6["preps"]

        # checks if adding the unregistered prep on preps of getPRepTerm API (2)
        self._check_preps_on_get_prep_term([])

        _check_elected_prep_grades(preps, main_prep_count, elected_prep_count)
        main_preps_6: List['Address'] = _get_main_preps(preps, main_prep_count)

        self.make_empty_blocks(
            count=2,
            prev_block_generator=main_preps_6[0],
            prev_block_validators=[
                address for address in main_preps_6
                if address != account_on_low_productivity_penalty.address
            ]
        )

        prep_on_penalty = self.get_prep(account_on_low_productivity_penalty)
        assert prep_on_penalty["status"] == PRepStatus.DISQUALIFIED.value
        assert prep_on_penalty["penalty"] == PenaltyReason.LOW_PRODUCTIVITY.value
        assert prep_on_penalty["unvalidatedSequenceBlocks"] == 2
        assert prep_on_penalty["grade"] == PRepGrade.CANDIDATE.value
        assert prep_on_penalty["validatedBlocks"] * 100 // prep_on_penalty["totalBlocks"] < \
            self.LOW_PRODUCTIVITY_PENALTY_THRESHOLD

        term_6 = self.get_prep_term()
        preps = term_6["preps"]

        # checks if adding the prep receiving a low productivity penalty on preps of getPRepTerm API
        self._check_preps_on_get_prep_term([])

        _check_elected_prep_grades(preps, main_prep_count, elected_prep_count - 1)
        main_preps_6: List['Address'] = _get_main_preps(preps, main_prep_count)
        assert main_preps_6[1] != account_on_low_productivity_penalty.address
        assert main_preps_6[1] == accounts[main_prep_count + 1].address

        count = term_6["endBlockHeight"] - term_6["blockHeight"] + 1
        self.make_empty_blocks(count,
                               prev_block_generator=main_preps_6[0],
                               prev_block_validators=[prep for prep in main_preps_6])

        # TERM-7: Disqualify P-Rep
        account_on_disqualification = accounts[main_prep_count + 1]

        term_7 = self.get_prep_term()
        assert term_7["sequence"] == 7
        preps = term_7["preps"]

        _check_elected_prep_grades(preps, main_prep_count, elected_prep_count)
        main_preps_7: List['Address'] = _get_main_preps(preps, main_prep_count)

        assert main_preps_7[-1] == account_on_disqualification.address
        tx_result: 'TransactionResult' = self.register_proposal(
            main_preps_7[0],
            title="P-Rep Disqualification",
            description="the P-Rep is malicious",
            type_=ProposalType.PREP_DISQUALIFICATION.value,
            value=account_on_disqualification.address)
        assert tx_result.status == TransactionResult.SUCCESS
        assert len(main_preps_7) == main_prep_count

        tx_hash: bytes = tx_result.tx_hash
        transactions = []
        for i, prep in enumerate(main_preps_7[1:]):
            vote: bool = prep != account_on_disqualification
            tx = self.create_vote_proposal_tx(from_=prep, id_=tx_hash, vote=vote)
            transactions.append(tx)

        tx_results: List['TransactionResult'] = self.process_confirm_block(
            transactions,
            prev_block_generator=main_preps_7[0],
            prev_block_validators=main_preps_7[1:]
        )
        assert tx_results[-1].status == TransactionResult.FAILURE

        prep_on_disqualification_penalty = self.get_prep(account_on_disqualification)
        assert prep_on_disqualification_penalty["status"] == PRepStatus.DISQUALIFIED.value
        assert prep_on_disqualification_penalty["grade"] == PRepGrade.CANDIDATE.value
        assert prep_on_disqualification_penalty["penalty"] == PenaltyReason.PREP_DISQUALIFICATION.value

        term_7_1 = self.get_prep_term()
        assert term_7_1["sequence"] == 7
        preps = term_7_1["preps"]

        # checks if adding the prep receiving a disqualification penalty on preps of getPRepTerm API
        self._check_preps_on_get_prep_term([])

        _check_elected_prep_grades(preps, main_prep_count, elected_prep_count - 1)
        main_preps_7: List['Address'] = _get_main_preps(preps, main_prep_count)
        assert main_preps_7[-1] != account_on_disqualification.address
        # The first sub P-Rep replaces the main P-Rep which is disqualified by network proposal
        assert main_preps_7[-1] == term_7["preps"][main_prep_count]["address"]
