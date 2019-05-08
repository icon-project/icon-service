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

from typing import TYPE_CHECKING

from ...base.address import ZERO_SCORE_ADDRESS
from ...base.type_converter import TypeConverter
from ...base.type_converter_templates import ParamType, ConstantKeys
from ...iconscore.icon_score_event_log import EventLogEmitter

if TYPE_CHECKING:
    from ...iconscore.icon_score_result import TransactionResult
    from ...iconscore.icon_score_context import IconScoreContext
    from ...icx.icx_storage import IcxStorage
    from ...icx.icx_account import Account
    from ...base.address import Address
    from ..ipc.reward_calc_proxy import RewardCalcProxy
    from ..reward_calc_data_storage import RewardCalcDataStorage
    from ..variable.variable import Variable


def _iscore_to_icx(iscore: int) -> int:
    return iscore // 10 ** 3


class IScoreHandler:
    icx_storage: 'IcxStorage' = None
    reward_calc_proxy: 'RewardCalcProxy' = None
    rc_storage: 'RewardCalcDataStorage' = None
    variable: 'Variable' = None

    @classmethod
    def handle_claim_iscore(cls, context: 'IconScoreContext', params: dict, tx_result: 'TransactionResult'):
        address: 'Address' = context.tx.origin

        # TODO: error handling
        iscore, block_height = cls.reward_calc_proxy.claim_iscore(
            address, context.block.height, context.block.hash)

        icx: int = _iscore_to_icx(iscore)

        from_account: 'Account' = cls.icx_storage.get_account(context, address)
        from_account.deposit(icx)
        cls.icx_storage.put_account(context, from_account)
        cls._create_tx_result(context, iscore, icx)

    @classmethod
    def _create_tx_result(cls, context: 'IconScoreContext', iscore: int, icx: int):
        # make tx result
        event_signature: str = 'IScoreClaimed(int,int)'
        arguments = [iscore, icx]
        index = 0
        EventLogEmitter.emit_event_log(context, ZERO_SCORE_ADDRESS, event_signature, arguments, index)

    @classmethod
    def handle_query_iscore(cls, context: 'IconScoreContext', params: dict) -> dict:
        ret_params: dict = TypeConverter.convert(params, ParamType.IISS_QUERY_ISCORE)
        address: 'Address' = ret_params[ConstantKeys.ADDRESS]

        # TODO: error handling
        iscore, block_height = cls.reward_calc_proxy.query_iscore(address)

        data = {
            "iscore": iscore,
            "icx": _iscore_to_icx(iscore),
            "blockHeight": block_height
        }

        return data
