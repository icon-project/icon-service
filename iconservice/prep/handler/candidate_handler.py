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

from ..candidate import Candidate
from ..candidate_utils import CandidateUtils
from ...base.exception import InvalidParamsException
from ...base.type_converter import TypeConverter
from ...base.type_converter_templates import ParamType, ConstantKeys
from ...icx.icx_storage import Intent

if TYPE_CHECKING:
    from ...iconscore.icon_score_result import TransactionResult
    from ...iconscore.icon_score_context import IconScoreContext
    from ...icx.icx_storage import IcxStorage
    from ...icx.icx_account import Account
    from ...base.address import Address
    from ..candidate_storage import CandidateStorage
    from ..candidate_container import CandidateSortedInfos
    from ..variable.variable import Variable


class CandidateHandler:
    icx_storage: 'IcxStorage' = None
    prep_storage: 'CandidateStorage' = None
    prep_variable: 'Variable' = None
    prep_candidates: 'CandidateSortedInfos' = None

    @classmethod
    def handle_reg_prep_candidate(cls, context: 'IconScoreContext', params: dict, tx_result: 'TransactionResult'):

        address: 'Address' = context.tx.origin
        ret_params: dict = TypeConverter.convert(params, ParamType.IISS_REG_PREP_CANDIDATE)

        cls._put_prep_candidate_for_state_db(context, address, ret_params)
        cls._put_reg_prep_candidate_for_iiss_db(context, address)

    @classmethod
    def _put_prep_candidate_for_state_db(cls, context: 'IconScoreContext', address: 'Address', params: dict):

        if cls.prep_storage.is_candidate(context, address):
            raise InvalidParamsException(f'Failed to register candidate: already register')

        prep_candidate: Candidate = \
            Candidate.from_dict(params, context.block.height, context.tx.index, address)
        cls.prep_storage.put_candidate(context, prep_candidate)

        account: 'Account' = cls.icx_storage.get_account(context, address, Intent.DELEGATED)
        CandidateUtils.register_prep_candidate_info_for_sort(context,
                                                             address,
                                                             prep_candidate.name,
                                                             account.delegated_amount)

        cls._apply_candidate_delegated_offset_for_iiss_variable(context, account.delegated_amount)
        # TODO tx_result make if needs

    @classmethod
    def _put_reg_prep_candidate_for_iiss_db(cls,
                                            context: 'IconScoreContext',
                                            address: 'Address'):

        context.iiss_engine.put_reg_prep_candidate_for_rc_data(context.rc_tx_batch,
                                                               address,
                                                               context.block.height)

    @classmethod
    def _apply_candidate_delegated_offset_for_iiss_variable(cls,
                                                            context: 'IconScoreContext',
                                                            offset: int):
        context.iiss_engine.apply_candidate_delegated_offset_for_iiss_variable(context, offset)

    @classmethod
    def handle_set_prep_candidate(cls, context: 'IconScoreContext', params: dict, tx_result: 'TransactionResult'):

        address: 'Address' = context.tx.origin
        ret_params: dict = TypeConverter.convert(params, ParamType.IISS_SET_PREP_CANDIDATE)

        cls._update_prep_candidate_for_state_db(context, address, ret_params)

    @classmethod
    def _update_prep_candidate_for_state_db(cls, context: 'IconScoreContext', address: 'Address', params: dict):

        if not cls.prep_storage.is_candidate(context, address):
            raise InvalidParamsException(f'Failed to set candidate: no register')

        prep_candidate: 'Candidate' = cls.prep_storage.get_candidate(context, address)
        prep_candidate.update_dict(params)
        cls.prep_storage.put_candidate(context, prep_candidate)
        # TODO tx_result make if needs

    @classmethod
    def handle_unreg_prep_candidate(cls, context: 'IconScoreContext', params: dict, tx_result: 'TransactionResult'):

        address: 'Address' = context.tx.origin
        # ret_params: dict = TypeConverter.convert(params, ParamType.IISS_UNREG_PREP_CANDIDATE)
        cls._del_prep_candidate_for_state_db(context, address)
        cls._put_unreg_prep_candidate_for_iiss_db(context, address)

    @classmethod
    def _del_prep_candidate_for_state_db(cls, context: 'IconScoreContext', address: 'Address'):
        if not cls.prep_storage.is_candidate(context, address):
            raise InvalidParamsException(f'Failed to un register candidate: no register')

        cls.prep_storage.delete_candidate(context, address)
        CandidateUtils.unregister_prep_candidate_info_for_sort(context, address)

        account: 'Account' = cls.icx_storage.get_account(context, address, Intent.DELEGATED)
        cls._apply_candidate_delegated_offset_for_iiss_variable(context, -account.delegated_amount)
        # TODO tx_result make if needs

    @classmethod
    def _put_unreg_prep_candidate_for_iiss_db(cls,
                                              context: 'IconScoreContext',
                                              address: 'Address'):

        context.iiss_engine.put_unreg_prep_candidate_for_iiss_db(context.rc_tx_batch,
                                                                 address,
                                                                 context.block.height)

    @classmethod
    def handle_get_prep_candidate(cls, context: 'IconScoreContext', params: dict) -> dict:

        ret_params: dict = TypeConverter.convert(params, ParamType.IISS_GET_PREP_CANDIDATE)
        address: 'Address' = ret_params[ConstantKeys.ADDRESS]
        return cls._get_prep_candidate(context, address)

    @classmethod
    def _get_prep_candidate(cls, context: 'IconScoreContext', address: 'Address') -> dict:

        if not cls.prep_storage.is_candidate(context, address):
            raise InvalidParamsException(f'Failed to get candidate: no register')

        prep_candidate: 'Candidate' = cls.prep_storage.get_candidate(context, address)

        data = {
            ConstantKeys.NAME: prep_candidate.name,
            ConstantKeys.EMAIL: prep_candidate.email,
            ConstantKeys.WEBSITE: prep_candidate.website,
            ConstantKeys.JSON: prep_candidate.json,
            ConstantKeys.TARGET: prep_candidate.target,
            ConstantKeys.GOVERNANCE_VARIABLE: {
                ConstantKeys.INCENTIVE_REP: prep_candidate.gv.incentiveRep
            }
        }
        return data

    @classmethod
    def handle_get_prep_candidate_delegation_info(cls, context: 'IconScoreContext', params: dict) -> dict:

        ret_params: dict = TypeConverter.convert(params, ParamType.IISS_GET_PREP_CANDIDATE_DELEGATION_INFO)
        address: 'Address' = ret_params[ConstantKeys.ADDRESS]
        return cls._get_prep_candidate_delegation_info(context, address)

    @classmethod
    def _get_prep_candidate_delegation_info(cls, context: 'IconScoreContext', address: 'Address') -> dict:

        index, candidate = cls.prep_candidates.get(address)

        if candidate is None:
            raise InvalidParamsException(f"this EOA is not Candidate: {address}")

        data = {
            "ranking": index + 1,
            "totalDelegated": candidate.total_delegated,
        }
        return data

    @classmethod
    def handle_get_prep_list(cls, context: 'IconScoreContext', params: dict) -> dict:

        ret_params: dict = TypeConverter.convert(params, ParamType.IISS_GET_PREP_LIST)
        return cls._get_prep_list(context)

    @classmethod
    def _get_prep_list(cls, context: 'IconScoreContext') -> dict:

        preps: list = cls.prep_variable.get_preps(context)
        data: dict = {}
        total_delegated: int = 0

        prep_infos = []
        for prep in preps:
            info = {
                "address": prep.address,
                "delegated": prep.total_delegated
            }
            total_delegated += prep.total_delegated
            prep_infos.append(info)

        data["totalDelegated"] = total_delegated
        data["prepList"] = prep_infos

        return data

    @classmethod
    def handle_get_prep_candidate_list(cls, context: 'IconScoreContext', params: dict) -> dict:

        ret_params: dict = TypeConverter.convert(params, ParamType.IISS_GET_PREP_CANDIDATE_LIST)
        return cls._get_prep_candidate_list(context, ret_params)

    @classmethod
    def _get_prep_candidate_list(cls, context: 'IconScoreContext', params: dict) -> dict:

        prep_list: list = cls.prep_candidates.to_list()
        data: dict = {}
        total_delegated: int = 0

        prep_infos = []
        for candidate in prep_list:
            info = {
                "address": candidate.address,
                "delegated": candidate.total_delegated
            }
            total_delegated += candidate.total_delegated
            prep_infos.append(info)

        data["totalDelegated"] = total_delegated
        data["prepList"] = prep_infos

        return data
