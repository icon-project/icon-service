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

from ..reward_calc.data_creator import DataCreator
from ...base.exception import InvalidParamsException
from ...base.type_converter import TypeConverter
from ...base.type_converter_templates import ParamType, ConstantKeys
from ...icon_constant import IISS_MAX_DELEGATIONS
from ...icx.icx_storage import Intent

if TYPE_CHECKING:
    from ...iconscore.icon_score_result import TransactionResult
    from ...iconscore.icon_score_context import IconScoreContext
    from ...icx.icx_storage import IcxStorage
    from ...icx.icx_account import Account
    from ...base.address import Address
    from ..reward_calc.data_storage import DataStorage as RewardCalcDataStorage
    from ..ipc.reward_calc_proxy import RewardCalcProxy
    from ..reward_calc.msg_data import DelegationInfo, DelegationTx, TxData
    from ..variable.variable import Variable


class DelegationHandler:
    icx_storage: 'IcxStorage' = None
    reward_calc_proxy: 'RewardCalcProxy' = None
    rc_storage: 'RewardCalcDataStorage' = None
    variable: 'Variable' = None

    @classmethod
    def handle_set_delegation(cls, context: 'IconScoreContext', params: dict, tx_result: 'TransactionResult'):

        address: 'Address' = context.tx.origin
        ret_params: dict = TypeConverter.convert(params, ParamType.IISS_SET_DELEGATION)
        data: list = ret_params[ConstantKeys.DELEGATIONS]

        cls._put_delegation_for_state_db(context, address, data)
        cls._put_delegation_for_iiss_db(context.rc_tx_batch, address, context.block.height, data)

    @classmethod
    def _put_delegation_for_state_db(cls, context: 'IconScoreContext', delegating_address: 'Address',
                                     delegations: list):

        if not isinstance(delegations, list):
            raise InvalidParamsException('Failed to delegation: delegations is not list type')

        if len(delegations) > IISS_MAX_DELEGATIONS:
            raise InvalidParamsException(f'Failed to delegation: Overflow Max Input List')

        delegating: 'Account' = cls.icx_storage.get_account(context, delegating_address, Intent.DELEGATING)
        candidates: dict = cls._make_candidates(delegating.delegations, delegations)
        cls._set_delegations(delegating, candidates)
        dirty_accounts: list = cls._delegated_candidates(context, delegating, candidates)
        dirty_accounts.append(delegating)

        for dirty_account in dirty_accounts:
            cls.icx_storage.put_account(context, dirty_account)
            if context.prep_candidate_engine.is_candidate(context, dirty_account.address):
                context.prep_candidate_engine.update_prep_candidate_info_for_sort(context,
                                                                                  dirty_account.address,
                                                                                  dirty_account.delegated_amount)
        # TODO tx_result make if needs

    @classmethod
    def _make_candidates(cls, old_delegations: list, new_delegations: list) -> dict:
        candidates: dict = {}

        if old_delegations:
            for address, old in old_delegations:
                candidates[address] = (old, 0)

        for delegation in new_delegations:
            address, new = delegation.values()
            if address in candidates:
                old, _ = candidates[address]
                candidates[address] = (old, new)
            else:
                candidates[address] = (0, new)
        return candidates

    @classmethod
    def _set_delegations(cls, delegating: 'Account', candidates: dict):
        new_delegations: list = [(address, new) for address, (before, new) in candidates.items() if new > 0]
        delegating.set_delegations(new_delegations)

        if delegating.delegations_amount > delegating.stake:
                raise InvalidParamsException(
                    f"Failed to delegation: delegation_amount{delegating.delegations_amount} > stake{delegating.stake}")

    @classmethod
    def _delegated_candidates(cls, context: 'IconScoreContext', delegating: 'Account', candidates: dict) -> list:
        dirty_accounts: list = []
        for address, (before, new) in candidates.items():
            if address == delegating.address:
                candidate: 'Account' = delegating
            else:
                candidate: 'Account' = cls.icx_storage.get_account(context, address, Intent.DELEGATED)
                dirty_accounts.append(candidate)

            offset: int = new - before
            candidate.update_delegated_amount(offset)

            if context.prep_candidate_engine.is_candidate(context, address):
                total: int = cls.variable.issue.get_total_candidate_delegated(context)
                cls.variable.issue.put_total_candidate_delegated(context, total + offset)
        return dirty_accounts

    @classmethod
    def _put_delegation_for_iiss_db(cls, batch: list, address: 'Address', block_height: int, delegations: list):

        delegation_list: list = []

        for delegation in delegations:
            delegation_address, delegation_value = delegation.values()
            info: 'DelegationInfo' = DataCreator.create_delegation_info(delegation_address, delegation_value)
            delegation_list.append(info)

        delegation_tx: 'DelegationTx' = DataCreator.create_tx_delegation(delegation_list)
        iiss_tx_data: 'TxData' = DataCreator.create_tx(address, block_height, delegation_tx)
        cls.rc_storage.put(batch, iiss_tx_data)

    @classmethod
    def handle_get_delegation(cls, context: 'IconScoreContext', params: dict) -> dict:

        ret_params: dict = TypeConverter.convert(params, ParamType.IISS_GET_STAKE)
        address: 'Address' = ret_params[ConstantKeys.ADDRESS]
        return cls._get_delegation(context, address)

    @classmethod
    def _get_delegation(cls, context: 'IconScoreContext', address: 'Address') -> dict:

        account: 'Account' = cls.icx_storage.get_account(context, address, Intent.DELEGATED)
        delegation_list: list = []
        for address, value in account.delegations:
            delegation_list.append({"address": address, "value": value})

        data = {
            "delegations": delegation_list,
            "totalDelegated": account.delegations_amount
        }

        return data
