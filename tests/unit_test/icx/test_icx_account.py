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
from iconservice.base.exception import OutOfBalanceException
from iconservice.icon_constant import Revision, IconScoreContextType
from iconservice.iconscore.context.context import ContextContainer
from iconservice.iconscore.icon_score_context import IconScoreContext
from iconservice.icx.coin_part import CoinPart, CoinPartFlag, CoinPartType
from iconservice.icx.icx_account import Account
from iconservice.icx.stake_part import StakePart

ADDRESS = Address.from_string(f"hx{'1234'*10}")


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
        revision.value for revision in Revision if revision.value == Revision.FIX_BALANCE_BUG.value
    ])
    @pytest.mark.parametrize("balance, withdrawal_amount", [(0, 10)])
    @pytest.mark.parametrize("unstake_info, current_block_height", [
        ([], 20),
        ([[10, 20]], 5),
        ([[10, 20]], 15),
        ([[10, 20], [10, 40]], 5),
        ([[10, 20], [10, 40]], 15),
        ([[10, 20], [10, 40]], 25),
    ])
    def test_multiple_unstake_deposit_(
            self, context, mocker, revision, balance, withdrawal_amount, unstake_info, current_block_height):
        mocker.patch.object(IconScoreContext, "revision", PropertyMock(return_value=revision))
        coin_part = CoinPart(CoinPartType.GENERAL, CoinPartFlag.NONE, balance)
        stake = 100
        unstake_lock_period = 20
        account = Account(ADDRESS,
                          current_block_height,
                          revision,
                          coin_part=coin_part,
                          stake_part=StakePart(stake=stake, unstake=0, unstake_block_height=0))

        for info in unstake_info:
            context.block._height = info[1] - unstake_lock_period
            stake = stake - info[0]
            account.set_stake(context, stake, unstake_lock_period)

        if revision >= Revision.FIX_BALANCE_BUG.value:
            account.normalize(revision)
            account.withdraw(withdrawal_amount)
        else:
            with pytest.raises(OutOfBalanceException) as e:
                account.withdraw(withdrawal_amount)
