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
import shutil
from unittest.mock import PropertyMock

import pytest

from iconservice import Address
from iconservice.base.block import Block
from iconservice.database.db import ContextDatabase
from iconservice.icon_constant import Revision, IconScoreContextType
from iconservice.iconscore.context.context import ContextContainer
from iconservice.iconscore.icon_score_context import IconScoreContext
from iconservice.icx.coin_part import CoinPart, CoinPartFlag, CoinPartType
from iconservice.icx.icx_account import Account
from iconservice.icx.stake_part import StakePart
from iconservice.icx.storage import Storage, Intent
from iconservice.utils import ContextStorage

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


@pytest.fixture(scope="function")
def storage(context):
    db_name = 'icx.db'
    db = ContextDatabase.from_path(db_name)
    storage = Storage(db)
    context.storage = ContextStorage(icx=storage)
    storage.open(context)
    yield storage
    storage.close(context)
    shutil.rmtree(db_name)


class TestIcxStorage:

    @pytest.mark.parametrize("unstakes_info, current_block_height, flag, expected_balance", [
        ([], 20, CoinPartFlag.NONE, 100),
        ([[10, 20]], 5, CoinPartFlag.HAS_UNSTAKE, 100),
        ([[10, 20]], 25, CoinPartFlag.NONE, 110),
        ([[10, 20], [10, 30]], 15, CoinPartFlag.HAS_UNSTAKE, 100),
        ([[10, 20], [10, 30]], 25, CoinPartFlag.NONE, 110),
        ([[10, 20], [10, 30]], 35, CoinPartFlag.NONE, 120),
    ])
    def test_get_account(
            self, storage, context, mocker, unstakes_info, current_block_height, flag, expected_balance):
        revision = Revision.FIX_BALANCE_BUG.value
        mocker.patch.object(IconScoreContext, "revision", PropertyMock(return_value=revision))
        stake, balance = 100, 100
        coin_part = CoinPart(CoinPartType.GENERAL, CoinPartFlag.NONE, balance)
        coin_part.set_dirty(True)
        stake_part = StakePart(stake=stake, unstake=0, unstake_block_height=0, unstakes_info=unstakes_info)
        stake_part.set_dirty(True)
        account = Account(
            ADDRESS, current_block_height, revision, coin_part=coin_part, stake_part=stake_part)
        account.coin_part._flags = flag
        context.block._height = current_block_height
        storage.put_account(context, account)

        remaining_unstakes = [unstake_info for unstake_info in unstakes_info if unstake_info[1] > current_block_height]

        account = storage.get_account(context, ADDRESS)
        assert account.balance == expected_balance
        assert account.unstakes_info == remaining_unstakes
