# -*- coding: utf-8 -*-

from __future__ import annotations

__all__ = "UnstakePatcher"

import importlib.resources
import json
from enum import IntEnum
from typing import TYPE_CHECKING, List, Dict, Any

from iconcommons.logger import Logger

from ..base.address import Address
from ..icx.coin_part import CoinPartFlag

if TYPE_CHECKING:
    from ..iconscore.icon_score_context import IconScoreContext
    from ..icx.coin_part import CoinPart
    from ..icx.stake_part import StakePart

TAG = "GHOST"
SUCCESS = 0
FAILURE = 1


class Unstake(object):
    def __init__(self, amount: int, block_height: int):
        self._amount = amount
        self._block_height = block_height

    def __str__(self) -> str:
        return f"{self.to_list()}"

    @property
    def amount(self) -> int:
        return self._amount

    @property
    def block_height(self) -> int:
        return self._block_height

    def to_list(self) -> List[int]:
        return [self._amount, self._block_height]

    @classmethod
    def from_list(cls, data: List[int]) -> Unstake:
        return cls(amount=data[0], block_height=data[1])


class Target(object):
    def __init__(self, address: Address, unstakes: List[Unstake]):
        self._address = address
        self._unstakes: List[Unstake] = unstakes

    def __len__(self) -> int:
        return len(self._unstakes)

    def __str__(self):
        return (
            f"address={self._address} "
            f"total_unstake={self.total_unstake} "
            f"unstakes={self._unstakes}"
        )

    @property
    def address(self) -> Address:
        return self._address

    @property
    def total_unstake(self) -> int:
        return sum(unstake.amount for unstake in self._unstakes)

    @property
    def unstakes(self) -> List[Unstake]:
        return self._unstakes

    def add_unstake(self, amount: int, block_height: int):
        self._unstakes.append(Unstake(amount, block_height))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "address": str(self._address),
            "total_unstake": self.total_unstake,
            "unstakes": self._unstakes,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Target:
        unstakes: List[Unstake] = [Unstake.from_list(i) for i in data["unstakes"]]

        return cls(address=Address.from_string(data["address"]), unstakes=unstakes)


class Result(IntEnum):
    FALSE = 0
    REMOVABLE_V0 = 1
    REMOVABLE_V1 = 2


class UnstakePatcher(object):

    def __init__(self, targets: List[Target]):
        self._targets = targets

        self._success_targets: List[Target] = []
        self._failure_targets: List[Target] = []
        self._unstakes: List[int] = [0, 0, 0]

    @classmethod
    def _load(cls, path: str) -> Dict[str, Any]:
        if isinstance(path, str):
            with open(path, "rt") as f:
                json_text = f.read()
        else:
            json_text = importlib.resources.read_text(
                "iconservice.res", "invisible_ghost_icx_list.json"
            )

        return json.loads(json_text)

    def run(self, context: 'IconScoreContext'):
        storage = context.storage.icx

        for target in self._targets:
            address = target.address
            coin_part = storage.get_coin_part(context, address)
            stake_part = storage.get_stake_part(context, address)

            result: Result = self._check_removable(coin_part, stake_part, target)
            if result == Result.FALSE:
                self._add_failure_item(target)
            else:
                if Result.REMOVABLE_V0:
                    stake_part = self._remove_ghost_icx_v0(stake_part, target)
                else:
                    stake_part = self._remove_ghost_icx_v1(stake_part, target)

                assert stake_part.is_dirty()
                storage.put_stake_part(context, stake_part)
                self._add_success_item(target)

    @classmethod
    def _check_removable(
        cls, coin_part: CoinPart, stake_part: StakePart, target: Target
    ) -> Result:

        if CoinPartFlag.HAS_UNSTAKE not in coin_part.flags:
            if stake_part.unstake_block_height > 0:
                if cls._is_removable_v0(stake_part, target):
                    return Result.REMOVABLE_V0
            else:
                if cls._is_removable_v1(stake_part, target):
                    return Result.REMOVABLE_V1

        return Result.FALSE

    @classmethod
    def _is_removable_v0(cls, stake_part: 'StakePart', target: Target) -> bool:
        """Inspect stake_part.unstake and stake_part.unstake_block_height

        :param target:
        :param stake_part:
        :return:
        """
        if len(target.unstakes) != 1:
            return False
        if len(stake_part.unstakes_info) != 0:
            Logger.error(
                tag=TAG,
                msg=f"Invalid stake_part.unstakes_info: {stake_part.unstakes_info}"
            )
            return False

        unstake: Unstake = target.unstakes[0]
        return (
            unstake.amount == stake_part.unstake
            and unstake.block_height == stake_part.unstake_block_height
        )

    @classmethod
    def _is_removable_v1(cls, stake_part: 'StakePart', target: Target) -> bool:
        """Inspect stake_part.unstakes_info

        :param stake_part:
        :param target:
        :return:
        """
        unstakes_info: List[List[int, int]] = stake_part.unstakes_info
        if (
                len(unstakes_info) == 0
                or stake_part.unstake > 0
                or stake_part.unstake_block_height > 0
        ):
            return False

        for info, unstake in zip(stake_part.unstakes_info, target.unstakes):
            if not (
                info[0] == unstake.amount
                and info[1] == unstake.block_height
            ):
                return False

        return True

    @classmethod
    def _remove_ghost_icx_v0(cls, stake_part, target: Target) -> 'StakePart':
        """Remove ghost icx from stake_part.unstake and stake_part.unstake_block_height

        :param stake_part:
        :param target:
        :return:
        """
        assert len(stake_part.unstakes_info) == 0
        assert len(target.unstakes) == 1

        unstake: Unstake = target.unstakes[0]
        assert stake_part.unstake == unstake.amount
        assert stake_part.unstake_block_height == unstake.block_height

        stake_part.cleanup_old_format_unstake()
        assert stake_part.unstake == 0
        assert stake_part.unstake_block_height == 0

        Logger.info(tag=TAG, msg=f"remove_ghost_icx_v0: {target}")

        return stake_part

    @classmethod
    def _remove_ghost_icx_v1(cls, stake_part, target) -> 'StakePart':
        """Remove ghost icx from stake_part.unstakes_info

        :param stake_part:
        :param target:
        :return:
        """
        assert stake_part.unstake == 0
        assert stake_part.unstake_block_height == 0

        for unstake in target.unstakes:
            amount, unstake_block_height = stake_part.unstakes_info.pop(0)

            assert amount == unstake.amount
            assert unstake_block_height == unstake.block_height

        Logger.info(tag=TAG, msg=f"remove_ghost_icx_v1: {target}")

        stake_part.set_dirty(True)
        return stake_part

    def _add_success_item(self, target: Target):
        self._success_targets.append(target)
        self._unstakes[SUCCESS] += target.total_unstake

    def _add_failure_item(self, target: Target):
        self._failure_targets.append(target)
        self._unstakes[FAILURE] += target.total_unstake

    def write_result(self, path: str):
        total_unstake = sum(self._unstakes)

        Logger.warning(
            tag=TAG,
            msg="Invisible ghost ICX patch result: "
            f"total_unstake={total_unstake} "
            f"success_unstake={self._unstakes[SUCCESS]} "
            f"failure_unstake={self._unstakes[FAILURE]} "
            f"total_items={len(self._targets)} "
            f"success_items={len(self._success_targets)} "
            f"failure_items={len(self._failure_targets)}",
        )

        try:
            report = {
                # Unstake amount
                "total_unstake": total_unstake,
                "success_unstake": self._unstakes[SUCCESS],
                "failure_unstake": self._unstakes[FAILURE],

                # Item count
                "total": len(self._targets),
                "success": len(self._success_targets),
                "failure": list(self._failure_targets),

                # Item list
                "success_targets": [target.to_dict() for target in self._success_targets],
                "failure_targets": [target.to_dict() for target in self._failure_targets],
            }

            with open(path, "w") as f:
                text = json.dumps(report, indent=4)
                f.write(text)
        except BaseException as e:
            Logger.exception(tag=TAG, msg=str(e))

    @classmethod
    def from_path(cls, path: str) -> UnstakePatcher:
        data: Dict[str, Any] = cls._load(path)
        targets: List[Target] = [Target.from_dict(i) for i in data["targets"]]

        return cls(targets)
