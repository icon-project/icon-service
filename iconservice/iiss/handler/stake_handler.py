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

from ...base.exception import InvalidParamsException
from ...base.type_converter_templates import ParamType, ConstantKeys
from ...base.type_converter import TypeConverter
from ...icx.icx_storage import Intent

if TYPE_CHECKING:
    from ...iconscore.icon_score_result import TransactionResult
    from ...iconscore.icon_score_context import IconScoreContext
    from ...icx.icx_storage import IcxStorage
    from ...icx.icx_account import Account
    from ...base.address import Address
    from ..ipc.reward_calc_proxy import RewardCalcProxy
    from ..rc_data_storage import RcDataStorage
    from ..iiss_variable.iiss_variable import IissVariable


class StakeHandler:
    icx_storage: 'IcxStorage' = None
    reward_calc_proxy: 'RewardCalcProxy' = None
    rc_storage: 'RcDataStorage' = None
    variable: 'IissVariable' = None

    @classmethod
    def handle_set_stake(cls, context: 'IconScoreContext', params: dict, tx_result: 'TransactionResult'):

        address: 'Address' = context.tx.origin
        ret_params: dict = TypeConverter.convert(params, ParamType.IISS_SET_STAKE)
        value: int = ret_params[ConstantKeys.VALUE]

        cls._put_stake_for_state_db(context, address, value)

    @classmethod
    def _put_stake_for_state_db(cls, context: 'IconScoreContext', address: 'Address', value: int):

        if not isinstance(value, int) or value < 0:
            raise InvalidParamsException('Failed to stake: value is not int type or value < 0')

        account: 'Account' = cls.icx_storage.get_account(context, address, Intent.STAKE)
        unstake_lock_period = 10
        account.set_stake(value, unstake_lock_period)
        cls.icx_storage.put_account(context, account)

        # TODO tx_result make if needs

    @classmethod
    def handle_get_stake(cls, context: 'IconScoreContext', params: dict) -> dict:

        ret_params: dict = TypeConverter.convert(params, ParamType.IISS_GET_STAKE)
        address: 'Address' = ret_params[ConstantKeys.ADDRESS]
        return cls._get_stake(context, address)

    @classmethod
    def _get_stake(cls, context: 'IconScoreContext', address: 'Address') -> dict:

        account: 'Account' = cls.icx_storage.get_account(context, address, Intent.STAKE)

        stake: int = account.stake
        unstake: int = account.unstake
        unstake_block_beight: int = account.unstake_block_height

        data = {
            "stake": stake,
            "unstake": unstake,
            "unstakedBlockHeight": unstake_block_beight
        }
        return data
