# -*- coding: utf-8 -*-

from typing import TYPE_CHECKING, List

from iconcommons.logger import Logger

from ..icx.coin_part import CoinPartFlag

if TYPE_CHECKING:
    from ..base.address import Address
    from ..iconscore.icon_score_context import IconScoreContext

TAG = "UNSTAKE"


class _Patch(object):
    def __init__(self, address: 'Address', unstake: int, unstake_block_height: int):
        self._address = address
        self._unstake = unstake
        self._unstake_block_height = unstake_block_height

    @property
    def address(self) -> 'Address':
        return self._address

    @property
    def unstake(self) -> int:
        return self._unstake

    @property
    def unstake_block_height(self) -> int:
        return self._unstake_block_height


class UnstakePatcher(object):

    def __init__(self):
        self._patches: List[_Patch] = []

    def run(self, context: 'IconScoreContext'):
        Logger.debug(tag=TAG, msg=f"StakePatcher.run() start")

        storage = context.storage.icx
        unstake_to_remove = 0
        removed_unstake = 0
        success = 0

        for patch in self._patches:
            address = patch.address
            coin_part = storage.get_coin_part(context, address)
            stake_part = storage.get_stake_part(context, address)
            unstake_to_remove += patch.unstake

            unstakes_info: List[List[int, int]] = stake_part.unstakes_info
            if len(unstakes_info) == 0:
                continue

            # TODO: Need to remove multiple unstake info
            index = 0
            unstake, unstake_block_height = unstakes_info[index]

            if (CoinPartFlag.HAS_UNSTAKE not in coin_part.flags
                    and patch.unstake == unstake
                    and patch.unstake_block_height == unstake_block_height):
                stake_part.remove_unstake_info(index)
                assert stake_part.is_dirty()

                Logger.warning(
                    tag=TAG,
                    msg="Fix unstake_info: "
                        f"address={address} "
                        f"unstake={unstake} "
                        f"unstake_block_height={unstake_block_height}"
                )

                storage.put_stake_part(context, address, stake_part)
                removed_unstake += unstake
                success += 1

        Logger.warning(
            tag=TAG,
            msg="Unstake patch result: "
                f"unstake({removed_unstake}/{unstake_to_remove}) "
                f"success({success}/{len(self._patches)})"
        )
        Logger.debug(tag=TAG, msg="StakePatcher.run() end")
