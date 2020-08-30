# -*- coding: utf-8 -*-

from __future__ import annotations

__all__ = "UnstakePatcher"

import json
from enum import IntEnum
from typing import TYPE_CHECKING, List, Dict, Any, Optional

from iconcommons.logger import Logger

from ..base.address import Address
from ..icx.coin_part import CoinPartFlag

if TYPE_CHECKING:
    from ..iconscore.icon_score_context import IconScoreContext
    from ..icx.coin_part import CoinPart
    from ..icx.stake_part import StakePart

TAG = "UNSTAKE"


class _Item(object):
    def __init__(self, address: Address, unstake: int, unstake_block_height: int):
        self._address = address
        self._unstake = unstake
        self._unstake_block_height = unstake_block_height

    @property
    def address(self) -> Address:
        return self._address

    @property
    def unstake(self) -> int:
        return self._unstake

    @property
    def unstake_block_height(self) -> int:
        return self._unstake_block_height

    @classmethod
    def from_dict(cls, item: Dict[str, Any]) -> _Item:
        return cls(
            address=Address.from_string(item["address"]),
            unstake=item["unstake"],
            unstake_block_height=item["unstake_block_height"]
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "address": str(self._address),
            "unstake": self._unstake,
            "unstake_block_height": self._unstake_block_height
        }


class _UnstakeType(IntEnum):
    TOTAL = 0
    SUCCESS = 1
    FAILURE = 2


class UnstakePatcher(object):

    def __init__(self):
        self._items: List[_Item] = []
        self._success_items: Optional[List[_Item]] = None
        self._failure_items: Optional[List[_Item]] = None
        self._unstakes: Optional[List[int]] = None  # 0: total, 1: success, 2: failure

    def load(self, path: str):
        f = open(path, "rt")
        items: List[Dict[str, Any]] = json.load(f)
        f.close()

        self._items = [_Item.from_dict(item) for item in items]

    def run(self, context: 'IconScoreContext'):
        Logger.debug(tag=TAG, msg=f"StakePatcher.run() start")

        self._burn(context)
        self._write_report()

        Logger.debug(tag=TAG, msg="StakePatcher.run() end")

    def _init_metrics(self):
        self._success_items = []
        self._failure_items = []
        self._unstakes = [0, 0, 0]

    def _burn(self, context: 'IconScoreContext'):
        self._init_metrics()
        storage = context.storage.icx

        for item in self._items:
            address = item.address
            coin_part = storage.get_coin_part(context, address)
            stake_part = storage.get_stake_part(context, address)

            if self._is_burnable(coin_part, stake_part, item):
                unstakes_info: List[List[int, int]] = stake_part.unstakes_info
                unstake, unstake_block_height = unstakes_info[0]

                stake_part.remove_unstake_info(0)
                assert stake_part.is_dirty()

                Logger.warning(
                    tag=TAG,
                    msg="Remove invisible ghost icx: "
                        f"address={address} "
                        f"unstake={unstake} "
                        f"unstake_block_height={unstake_block_height}"
                )

                storage.put_stake_part(context, address, stake_part)
                self._add_success_item(item)
            else:
                self._add_failure_item(item)

            self._unstakes[_UnstakeType.TOTAL] += item.unstake

    @classmethod
    def _is_burnable(cls, coin_part: CoinPart, stake_part: StakePart, item: _Item) -> bool:
        unstakes_info: List[List[int, int]] = stake_part.unstakes_info
        if len(unstakes_info) == 0:
            return False

        unstake, unstake_block_height = unstakes_info[0]

        return (
            CoinPartFlag.HAS_UNSTAKE not in coin_part.flags
            and item.unstake == unstake
            and item.unstake_block_height == unstake_block_height
        )

    def _add_success_item(self, item: _Item):
        self._success_items.append(item)
        self._unstakes[_UnstakeType.SUCCESS] += item.unstake

    def _add_failure_item(self, item: _Item):
        self._failure_items.append(item)
        self._unstakes[_UnstakeType.FAILURE] += item.unstake

    def _write_report(self):
        path = ""

        Logger.warning(
            tag=TAG,
            msg="Invisible ghost ICX patch result: "
                f"total_unstake={self._unstakes[_UnstakeType.TOTAL]} "
                f"success_unstake={self._unstakes[_UnstakeType.SUCCESS]} "
                f"failure_unstake={self._unstakes[_UnstakeType.FAILURE]} "
                f"total_items={len(self._items)} "
                f"success_items={len(self._success_items)} "
                f"failure_items={len(self._failure_items)}"
        )

        try:
            report = {
                # Unstake amount
                "total_unstake": self._unstakes[_UnstakeType.TOTAL],
                "success_unstake": self._unstakes[_UnstakeType.SUCCESS],
                "failure_unstake": self._unstakes[_UnstakeType.FAILURE],

                # Item count
                "total": len(self._items),
                "success": len(self._success_items),
                "failure": list(self._failure_items),

                # Item list
                "success_items": [item.to_dict() for item in self._success_items],
                "failure_items": [item.to_dict() for item in self._failure_items]
            }

            with open(path, "w") as f:
                text = json.dumps(report, indent=4)
                f.write(text)
        except BaseException as e:
            Logger.exception(tag=TAG, msg=str(e))
