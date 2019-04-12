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

from ...iconscore.icon_score_event_log import EventLogEmitter
from ...base.address import ZERO_SCORE_ADDRESS
from ...base.exception import InvalidParamsException
from ...base.type_converter_templates import ParamType, ConstantKeys
from ...base.type_converter import TypeConverter

if TYPE_CHECKING:
    from ...iconscore.icon_score_result import TransactionResult
    from ...iconscore.icon_score_context import IconScoreContext
    from ...icx.icx_storage import IcxStorage
    from ...icx.icx_account import Account
    from ...base.address import Address
    from ..reward_calc_proxy import RewardCalcProxy
    from ..rc_data_storage import RcDataStorage
    from ..iiss_variable.iiss_variable import IissVariable


class IScoreHandler:
    icx_storage: 'IcxStorage' = None
    reward_calc_proxy: 'RewardCalcProxy' = None
    rc_storage: 'RcDataStorage' = None
    variable: 'IissVariable' = None

    @classmethod
    def handle_claim_iscore(cls, context: 'IconScoreContext', params: dict, tx_result: 'TransactionResult'):

        address: 'Address' = context.tx.origin
        # ret_params: dict = TypeConverter.convert(params, ParamType.IISS_CLAIM_I_SCORE)
        cls._put_claim_iscore_for_state_db(context, address)

    @classmethod
    def _put_claim_iscore_for_state_db(cls, context: 'IconScoreContext', address: 'Address'):

        iscore: int = 1000 * 10 ** 18
        block_height: int = 100

        ret_data: list = [address, iscore, block_height]
        # TODO invoke to RC
        # ret_data: list = cls.reward_calc_proxy.claim(address, context.block.height, context.block.hash)

        ret_address: 'Address' = ret_data[0]

        if address != ret_address:
            raise InvalidParamsException(f"Mismatch claim IScore input: {address}, ret: {ret_address}")

        ret_iscore: int = ret_data[1]
        ret_icx: int = ret_iscore // 10 ** 3
        ret_block_height: int = ret_data[2]

        from_account: 'Account' = cls.icx_storage.get_account(context, address)
        from_account.deposit(ret_icx)

        cls._create_tx_result(context, ret_iscore, ret_icx)

    @classmethod
    def _create_tx_result(cls, context: 'IconScoreContext', iscore: int, icx: int):
        # make tx result
        event_signature: str = 'claimIScore(int,int)'
        arguments = [iscore, icx]
        index = 2
        EventLogEmitter.emit_event_log(context, ZERO_SCORE_ADDRESS, event_signature, arguments, index)

    @classmethod
    def handle_query_iscore(cls, context: 'IconScoreContext', params: dict) -> dict:
        ret_params: dict = TypeConverter.convert(params, ParamType.IISS_QUERY_I_SCORE)
        address: 'Address' = ret_params[ConstantKeys.ADDRESS]
        return cls._get_i_score_from_rc(address)

    @classmethod
    def _get_i_score_from_rc(cls, address: 'Address') -> dict:

        address: 'Address' = None
        iscore: int = 1000 * 10 ** 18
        icx: int = iscore // 10 ** 3
        block_height: int = 100

        ret_data: list = [address, iscore, icx, block_height]
        # TODO query from RC
        # ret_data: list = cls.reward_calc_proxy.query(address)

        ret_address: 'Address' = ret_data[0]

        if address != ret_address:
            raise InvalidParamsException(f"Mismatch claim IScore input: {address}, ret: {ret_address}")

        ret_iscore: int = ret_data[1]
        ret_icx: int = iscore // 10 ** 3
        ret_block_height: int = ret_data[2]

        data = {
            "iscore": ret_iscore,
            "icx": ret_icx,
            "blockHeight": ret_block_height
        }

        return data

