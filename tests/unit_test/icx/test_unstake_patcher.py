# -*- coding: utf-8 -*-

import copy
import json
import os
import random
from typing import Dict, Any

import pytest

from iconservice.icx.stake_part import StakePart
from iconservice.icx.unstake_patcher import UnstakePatcher


def get_ghost_icx_list_path() -> str:
    return os.path.join(
        os.path.dirname(__file__),
        "../../../iconservice/res/invisible_ghost_icx_list.json"
    )


@pytest.fixture
def unstake_patcher() -> UnstakePatcher:
    # iconservice/res/invisible_ghost_icx_list.json
    path: str = get_ghost_icx_list_path()
    return UnstakePatcher.from_path(path)


class TestUnstakePatcher:
    def test_init(self, unstake_patcher):
        path = get_ghost_icx_list_path()
        with open(path, "rt") as f:
            data: Dict[str, Any] = json.load(f)

        for i, target in enumerate(unstake_patcher._targets):
            target_in_dict = data["targets"][i]
            assert str(target.address) == target_in_dict["address"]

            for j, unstake in enumerate(target.unstakes):
                assert unstake.amount == target_in_dict["unstakes"][j][0]
                assert unstake.block_height == target_in_dict["unstakes"][j][1]

    @pytest.mark.parametrize(
        "index,unstake,unstake_block_height,result",
        [
            (1, 43381396400000000000000, 22764980, True),
            (2, 2684320100000000000000, 22469640, True),
            (4, 0, 0, False),
        ]
    )
    def test_is_removable_v0(
            self, unstake_patcher, index, unstake, unstake_block_height, result):
        stake_part = StakePart(0, unstake, unstake_block_height)
        stake_part.set_complete(True)
        target = unstake_patcher._targets[index]

        assert unstake_patcher._is_removable_v0(stake_part, target) == result

    @pytest.mark.parametrize(
        "unstakes_info,index,result",
        [
            (
                [[89324800000000000000, 23030082], [9803672200000000000000, 23075236]],
                0, True
            ),
            (   # Unstake amount mismatch #1
                [[79324800000000000000, 23030082], [9803672200000000000000, 23075236]],
                0, False
            ),
            (   # unstake_block_height mismatch #1
                [[89324800000000000000, 23040000], [9803672200000000000000, 23075236]],
                0, False
            ),
            (   # Unstake amount mismatch #2
                [[89324800000000000000, 23030082], [1803672200000000000000, 23075236]],
                0, False
            ),
            (   # unstake_block_height mismatch #1
                [[89324800000000000000, 23030082], [9803672200000000000000, 24000000]],
                0, False
            ),

            (
                [[2420996900000000000000, 23059461]], 3, True
            ),
            (
                [[1420996900000000000000, 23059461]], 3, False
            ),
            (
                [[2420996900000000000000, 33059461]], 3, False
            ),
            (
                [[3000000000000000000000, 40000000]], 3, False
            ),
        ]
    )
    def test_is_removable_v1(self, unstake_patcher, index, unstakes_info, result):
        stake_part = StakePart(0, 0, 0, unstakes_info)
        stake_part.set_complete(True)
        target = unstake_patcher._targets[index]

        assert unstake_patcher._is_removable_v1(stake_part, target) == result

    @pytest.mark.parametrize(
        "index,unstake,unstake_block_height",
        [
            (1, 43381396400000000000000, 22764980),
            (2, 2684320100000000000000, 22469640),
        ]
    )
    def test_remove_ghost_icx_v0(
            self, unstake_patcher, index, unstake, unstake_block_height):
        stake = random.randint(0, 1000)
        stake_part = StakePart(stake, unstake, unstake_block_height)
        stake_part.set_complete(True)
        target = unstake_patcher._targets[index]

        assert stake_part.stake == stake
        assert stake_part.unstake == unstake
        assert stake_part.unstake_block_height == unstake_block_height
        assert not stake_part.is_dirty()

        stake_part = unstake_patcher._remove_ghost_icx_v0(stake_part, target)
        assert stake_part.is_dirty()
        assert len(stake_part.unstakes_info) == 0
        assert stake_part.stake == stake
        assert stake_part.unstake == 0
        assert stake_part.unstake_block_height == 0

    @pytest.mark.parametrize(
        "index,unstakes_info",
        [
            (
                0,
                [
                    [89324800000000000000, 23030082],
                    [9803672200000000000000, 23075236],
                    [1000000000000000000000, 24000000],
                ]
            ),
            (
                3, [[2420996900000000000000, 23059461]]
            ),
        ]
    )
    def test_remove_ghost_icx_v1(self, unstake_patcher, unstakes_info, index):
        stake = random.randint(0, 1000)
        stake_part = StakePart(stake, 0, 0, copy.deepcopy(unstakes_info))
        stake_part.set_complete(True)
        target = unstake_patcher._targets[index]

        stake_part = unstake_patcher._remove_ghost_icx_v1(stake_part, target)
        assert stake_part.is_dirty()
        assert stake_part.stake == stake
        assert stake_part.unstake == 0
        assert stake_part.unstake_block_height == 0

        size = len(stake_part.unstakes_info)
        target_size = len(target.unstakes)
        assert size == len(unstakes_info) - target_size

        for i in range(size):
            index = target_size + i
            assert stake_part.unstakes_info[i] == unstakes_info[index]
            assert stake_part.total_unstake == unstakes_info[index][0]
            assert stake_part.total_stake == unstakes_info[index][0] + stake
