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

from typing import TYPE_CHECKING, Optional, Callable

from .data.prep import PRep, PenaltyReason

if TYPE_CHECKING:
    from ..base.address import Address
    from ..iconscore.icon_score_context import IconScoreContext


class PenaltyImposer(object):
    """Check for the block validation statistics of P-Rep and impose a proper penalty on it

    """

    def __init__(self,
                 penalty_grace_period: int,
                 low_productivity_penalty_threshold: int,
                 block_validation_penalty_threshold: int):
        # Low productivity penalty is not imposed during penalty_grace_period
        self._penalty_grace_period: int = penalty_grace_period

        # Unit: percent without fraction
        self._low_productivity_penalty_threshold: int = low_productivity_penalty_threshold

        # Unit: The number of blocks
        self._block_validation_penalty_threshold: int = block_validation_penalty_threshold

    def run(self,
            context: 'IconScoreContext',
            prep: 'PRep',
            on_penalty_imposed: Callable[['IconScoreContext', 'Address', 'PenaltyReason'], None]) -> 'PenaltyReason':
        reason: 'PenaltyReason' = PenaltyReason.NONE

        if self._check_low_productivity_penalty(prep):
            reason = PenaltyReason.LOW_PRODUCTIVITY
        if self._check_block_validation_penalty(prep):
            reason = PenaltyReason.BLOCK_VALIDATION

        if on_penalty_imposed and reason != PenaltyReason.NONE:
            on_penalty_imposed(context, prep.address, reason)

        return reason

    def _check_low_productivity_penalty(self, prep: 'PRep') -> bool:
        return prep.total_blocks > self._penalty_grace_period and \
               prep.block_validation_proportion < self._low_productivity_penalty_threshold

    def _check_block_validation_penalty(self, prep: 'PRep') -> bool:
        return prep.unvalidated_sequence_blocks >= self._block_validation_penalty_threshold
