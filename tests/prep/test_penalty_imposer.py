# -*- coding: utf-8 -*-
# Copyright 2019 ICON Foundation
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

import os
import unittest
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

from iconservice.base.address import Address, AddressPrefix
from iconservice.iconscore.icon_score_context import IconScoreContext
from iconservice.prep.data.prep import PRep, PenaltyReason, PRepStatus, PRepGrade
from iconservice.prep.penalty_imposer import PenaltyImposer

if TYPE_CHECKING:
    pass

NAME = "banana"
EMAIL = "banana@example.com"
COUNTRY = "KOR"
CITY = "Seoul"
WEBSITE = "https://banana.example.com"
DETAILS = "https://banana.example.com/details"
P2P_END_POINT = "banana.example.com:7100"
IREP = 50000
LAST_GENERATE_BLOCK_HEIGHT = 50
STAKE = 100
DELEGATED = 100
BLOCK_HEIGHT = 777
TX_INDEX = 0
TOTAL_BLOCKS = 0
VALIDATED_BLOCKS = 0
IREP_BLOCK_HEIGHT = BLOCK_HEIGHT
PENALTY = PenaltyReason.NONE
UNVALIDATED_SEQUENCE_BLOCKS = 0


def create_prep(total_blocks: int = 0,
                validated_blocks: int = 0,
                unvalidated_sequence_blocks: int = 0):
    address = Address(AddressPrefix.EOA, os.urandom(20))
    prep = PRep(
        address,
        status=PRepStatus.ACTIVE,
        penalty=PenaltyReason.NONE,
        grade=PRepGrade.CANDIDATE,
        name=NAME,
        country=COUNTRY,
        city=CITY,
        email=EMAIL,
        website=WEBSITE,
        details=DETAILS,
        p2p_endpoint=P2P_END_POINT,
        irep=IREP,
        irep_block_height=IREP_BLOCK_HEIGHT,
        last_generate_block_height=LAST_GENERATE_BLOCK_HEIGHT,
        stake=STAKE,
        delegated=DELEGATED,
        block_height=BLOCK_HEIGHT,
        tx_index=TX_INDEX,
        total_blocks=total_blocks,
        validated_blocks=validated_blocks,
        unvalidated_sequence_blocks=unvalidated_sequence_blocks
    )

    return prep


class TestPenaltyImposer(unittest.TestCase):

    def setUp(self) -> None:
        self.context = IconScoreContext()

    def test_no_penalty(self):
        penalty_grace_period = 1000
        block_validation_penalty_threshold = 660
        low_productivity_penalty_threshold = 85

        on_penalty_imposed = MagicMock()

        total_blocks = penalty_grace_period - 1
        validated_blocks = 899
        unvalidated_sequence_blocks = total_blocks - validated_blocks

        prep = create_prep(
            total_blocks=total_blocks,
            validated_blocks=validated_blocks,
            unvalidated_sequence_blocks=unvalidated_sequence_blocks
        )

        penalty_imposer = PenaltyImposer(
            penalty_grace_period=penalty_grace_period,
            low_productivity_penalty_threshold=low_productivity_penalty_threshold,
            block_validation_penalty_threshold=block_validation_penalty_threshold
        )

        penalty_imposer.run(context=self.context,
                            prep=prep,
                            on_penalty_imposed=on_penalty_imposed)
        on_penalty_imposed.assert_not_called()

        prep.update_block_statistics(is_validator=True)
        assert prep.total_blocks == total_blocks + 1 == penalty_grace_period
        assert prep.validated_blocks == validated_blocks + 1
        assert prep.unvalidated_sequence_blocks == 0

        penalty_imposer.run(
            context=self.context, prep=prep, on_penalty_imposed=on_penalty_imposed)
        on_penalty_imposed.assert_not_called()

    def test_block_validation_penalty(self):
        penalty_grace_period = 43120 * 2
        block_validation_penalty_threshold = 660
        low_productivity_penalty_threshold = 85

        total_blocks = penalty_grace_period - 100
        unvalidated_sequence_blocks = block_validation_penalty_threshold
        validated_blocks = total_blocks - unvalidated_sequence_blocks

        prep = create_prep(total_blocks, validated_blocks, unvalidated_sequence_blocks)

        on_penalty_imposed = MagicMock()
        penalty_imposer = PenaltyImposer(
            penalty_grace_period=penalty_grace_period,
            low_productivity_penalty_threshold=low_productivity_penalty_threshold,
            block_validation_penalty_threshold=block_validation_penalty_threshold
        )

        # Block validation penalty works regardless of penalty_grace_period
        penalty_imposer.run(
            context=self.context, prep=prep, on_penalty_imposed=on_penalty_imposed)
        on_penalty_imposed.assert_called_with(
            self.context, prep.address, PenaltyReason.BLOCK_VALIDATION)

    def test_low_productivity_penalty(self):
        penalty_grace_period = 43120 * 2
        block_validation_penalty_threshold = 660
        low_productivity_penalty_threshold = 85

        total_blocks = penalty_grace_period
        unvalidated_sequence_blocks = 0
        validated_blocks = penalty_grace_period * low_productivity_penalty_threshold // 100

        prep = create_prep(total_blocks, validated_blocks, unvalidated_sequence_blocks)

        on_penalty_imposed = MagicMock()
        penalty_imposer = PenaltyImposer(
            penalty_grace_period=penalty_grace_period,
            low_productivity_penalty_threshold=low_productivity_penalty_threshold,
            block_validation_penalty_threshold=block_validation_penalty_threshold
        )

        # Low productivity penalty does not work during penalty_grace_period
        penalty_imposer.run(
            context=self.context, prep=prep, on_penalty_imposed=on_penalty_imposed)
        on_penalty_imposed.assert_not_called()

        prep.update_block_statistics(is_validator=False)
        assert prep.total_blocks >= penalty_grace_period
        assert prep.validated_blocks == validated_blocks
        assert prep.unvalidated_sequence_blocks == 1
        assert prep.block_validation_proportion < 85

        penalty_imposer.run(
            context=self.context, prep=prep, on_penalty_imposed=on_penalty_imposed)
        on_penalty_imposed.assert_called_with(
            self.context, prep.address, PenaltyReason.LOW_PRODUCTIVITY)
