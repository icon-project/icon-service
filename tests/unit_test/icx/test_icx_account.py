# -*- coding: utf-8 -*-
#
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
import copy
from unittest.mock import PropertyMock

import pytest

from iconservice import Address
from iconservice.base.block import Block
from iconservice.icon_constant import Revision, IconScoreContextType
from iconservice.iconscore.context.context import ContextContainer
from iconservice.iconscore.icon_score_context import IconScoreContext
from iconservice.icx.coin_part import CoinPart, CoinPartFlag, CoinPartType
from iconservice.icx.icx_account import Account
from iconservice.icx.stake_part import StakePart

ADDRESS = Address.from_string(f"hx{'1234'*10}")
UNSTAKE_LOCK_PERIOD = 20
WITHDRAWAL_AMOUNT = 10


@pytest.fixture(scope="function")
def context():
    ctx = IconScoreContext(IconScoreContextType.DIRECT)
    block = Block(0, None, 0, None, 0)
    ctx.block = block
    ContextContainer._push_context(ctx)
    yield ctx
    ContextContainer._pop_context()


class TestAccount:

    @pytest.mark.parametrize("revision", [
        revision.value for revision in Revision if revision.value >= Revision.MULTIPLE_UNSTAKE.value
    ])
    @pytest.mark.parametrize("flag", [CoinPartFlag.NONE, CoinPartFlag.HAS_UNSTAKE])
    @pytest.mark.parametrize("unstakes_info, current_block_height, expected_balance", [
        (None, 20, 100),
        ([], 20, 100),
        ([[10, 20]], 5, 100),
        ([[10, 20]], 20, 100),
        ([[10, 20]], 25, 110),
        ([[10, 20], [10, 30]], 15, 100),
        ([[10, 20], [10, 30]], 20, 100),
        ([[10, 20], [10, 30]], 25, 110),
        ([[10, 20], [10, 30]], 30, 110),
        ([[10, 20], [10, 30]], 35, 120),
    ])
    def test_normalize(
            self, context, mocker, revision, unstakes_info, current_block_height, flag, expected_balance):
        unstakes_info = copy.deepcopy(unstakes_info)
        mocker.patch.object(IconScoreContext, "revision", PropertyMock(return_value=revision))
        stake, balance = 100, 100

        coin_part = CoinPart(CoinPartType.GENERAL, flag, balance)
        stake_part = StakePart(stake=stake, unstake=0, unstake_block_height=0, unstakes_info=unstakes_info)
        account = Account(
            ADDRESS, current_block_height, revision, coin_part=coin_part, stake_part=stake_part)

        if unstakes_info is None:
            remaining_unstakes = []
        else:
            remaining_unstakes = [
                unstake_info for unstake_info in unstakes_info if unstake_info[1] >= current_block_height
            ]

        account.normalize(revision)

        assert account.stake == stake
        assert account.balance == expected_balance
        assert account.unstakes_info == remaining_unstakes
