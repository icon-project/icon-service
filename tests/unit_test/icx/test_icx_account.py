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


class TestMultipleUnstake:

    @pytest.mark.parametrize("revision", [
        revision.value for revision in Revision if revision.value >= Revision.MULTIPLE_UNSTAKE.value
    ])
    @pytest.mark.parametrize("unstakes_info, current_block_height, has_unstake", [
        ([], 20, False),
        ([[10, 20]], 5, True),
        ([[10, 20]], 25, False),
        ([[10, 20], [10, 30]], 15, True),
        ([[10, 20], [10, 30]], 25, False),
        ([[10, 20], [10, 30]], 35, False),
    ])
    def test_multiple_unstake_deposit_(
            self, context, mocker, revision, unstakes_info, current_block_height, has_unstake):
        mocker.patch.object(IconScoreContext, "revision", PropertyMock(return_value=revision))
        stake, balance = 100, 0
        coin_part = CoinPart(CoinPartType.GENERAL, CoinPartFlag.NONE, balance)
        stake_part = StakePart(stake=stake, unstake=0, unstake_block_height=0)
        account = Account(ADDRESS,
                          current_block_height,
                          revision,
                          coin_part=coin_part,
                          stake_part=stake_part)

        for info in unstakes_info:
            context.block._height = info[1] - UNSTAKE_LOCK_PERIOD
            stake = stake - info[0]
            # set_stake method refer account._current_block_height
            account._current_block_height = context.block.height
            account.set_stake(context, stake, UNSTAKE_LOCK_PERIOD)

        stake_part = account.stake_part
        remaining_unstakes = [unstake_info for unstake_info in unstakes_info if unstake_info[1] > current_block_height]
        expired_unstake = sum((unstake_info[0] for unstake_info in unstakes_info
                               if unstake_info[1] < current_block_height))
        balance = expired_unstake

        account = Account(ADDRESS, current_block_height, revision, coin_part=coin_part,
                          stake_part=stake_part)
        if revision >= Revision.FIX_BALANCE_BUG.value:
            has_unstake = False

        assert stake == account.stake
        assert balance == account.balance
        assert remaining_unstakes == account.unstakes_info
        assert (CoinPartFlag.HAS_UNSTAKE in account.coin_part.flags) == has_unstake
