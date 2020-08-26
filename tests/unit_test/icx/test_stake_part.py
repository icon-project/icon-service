# -*- coding: utf-8 -*-

import pytest

from iconservice.icon_constant import Revision
from iconservice.icx.stake_part import StakePart


class TestStakePart:
    @pytest.mark.parametrize(
        "block_height,params,expected",
        [
            (
                999,
                {"stake": 0, "unstake": 100, "unstake_block_height": 1000},
                {"stake": 0, "unstake": 100, "unstake_block_height": 1000, "expired_unstake": 0},
            ),
            (
                999,
                {"stake": 50, "unstake": 100, "unstake_block_height": 1000},
                {"stake": 50, "unstake": 100, "unstake_block_height": 1000, "expired_unstake": 0},
            ),
            (
                1000,
                {"stake": 0, "unstake": 100, "unstake_block_height": 1000},
                {"stake": 0, "unstake": 100, "unstake_block_height": 1000, "expired_unstake": 0},
            ),
            (
                1000,
                {"stake": 50, "unstake": 100, "unstake_block_height": 1000},
                {"stake": 50, "unstake": 100, "unstake_block_height": 1000, "expired_unstake": 0},
            ),
            (
                1001,
                {"stake": 0, "unstake": 100, "unstake_block_height": 1000},
                {"stake": 0, "unstake": 0, "unstake_block_height": 0, "expired_unstake": 100},
            ),
            (
                1001,
                {"stake": 50, "unstake": 100, "unstake_block_height": 1000},
                {"stake": 50, "unstake": 0, "unstake_block_height": 0, "expired_unstake": 100},
            ),
        ]
    )
    def test_stake_part_on_rev_8(self, block_height, params, expected):
        revision = 8
        stake_part = StakePart(**params)
        expired_unstake: int = stake_part.normalize(block_height=block_height, revision=revision)

        assert expired_unstake == expected["expired_unstake"]
        assert stake_part.stake == expected["stake"]
        assert stake_part.total_stake == expected["stake"] + expected["unstake"]
        assert stake_part.unstake == expected["unstake"]
        assert stake_part.total_unstake == expected["unstake"]
        assert stake_part.unstake_block_height == expected["unstake_block_height"]

    @pytest.mark.parametrize(
        "stake,unstakes_info,amount,expected_unstakes_info",
        [
            (0, [[100, 1000]], 10, [[90, 1000]]),
            (0, [[100, 1000], [200, 1500]], 50, [[100, 1000], [150, 1500]]),
            (0, [[100, 1000], [200, 1500]], 200, [[100, 1000]]),
            (0, [[100, 1000], [200, 1500]], 299, [[1, 1000]]),
            (0, [[100, 1000], [200, 1500], [50, 2000]], 20, [[100, 1000], [200, 1500], [30, 2000]]),
            (0, [[100, 1000], [200, 1500], [50, 2000]], 50, [[100, 1000], [200, 1500]]),
            (0, [[100, 1000], [200, 1500], [50, 2000]], 100, [[100, 1000], [150, 1500]]),
            (0, [[100, 1000], [200, 1500], [50, 2000]], 250, [[100, 1000]]),
            (0, [[100, 1000], [200, 1500], [50, 2000]], 270, [[80, 1000]]),
        ]
    )
    def test_withdraw_unstake(self, stake, unstakes_info, amount, expected_unstakes_info):
        expected_total_unstake = sum(unstake for unstake, _ in expected_unstakes_info)

        stake_part = StakePart(stake=stake, unstakes_info=unstakes_info)
        stake_part.normalize(block_height=500, revision=Revision.FIX_UNSTAKE_BUG.value)
        stake_part.withdraw_unstake(amount)

        assert stake_part.stake == stake
        assert stake_part.unstakes_info == expected_unstakes_info
        assert stake_part.total_unstake == expected_total_unstake
