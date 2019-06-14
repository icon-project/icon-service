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

from iconservice.prep.data.candidate import Candidate
from ...base.exception import InvalidParamsException
from ...base.type_converter import TypeConverter
from ...base.type_converter_templates import ParamType, ConstantKeys
from ...icx.storage import Intent

if TYPE_CHECKING:
    from ...iconscore.icon_score_result import TransactionResult
    from ...iconscore.icon_score_context import IconScoreContext
    from ...icx.storage import IcxStorage
    from ...icx.icx_account import Account
    from ...base.address import Address


class CandidateHandler:
    icx_storage: 'IcxStorage' = None

    @classmethod
    def _is_candidate(cls, context: 'IconScoreContext', address: 'Address') -> bool:
        return context.prep_engine.is_candidate(context, address)

    @classmethod
    def handle_reg_prep_candidate(
            cls, context: 'IconScoreContext', params: dict, tx_result: 'TransactionResult'):
        address: 'Address' = context.tx.origin
        if cls._is_candidate(context, address):
            raise InvalidParamsException(f"{str(address)} has been already registered")

        ret_params: dict = TypeConverter.convert(params, ParamType.IISS_REG_PREP_CANDIDATE)

        candidate = Candidate.from_dict(address, ret_params, context.block.height, context.tx.index)
        context.prep_engine.candidates.add(candidate)

        cls._put_prep_candidate_for_state_db(context, candidate)
        cls._put_reg_prep_candidate_for_iiss_db(context, address)

    @classmethod
    def _put_prep_candidate_for_state_db(cls, context: 'IconScoreContext', candidate: 'Candidate'):
        context.prep_storage.put_candidate(context, candidate)

        account: 'Account' = cls.icx_storage.get_account(context, candidate.address, Intent.DELEGATED)

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
    def _apply_candidate_delegated_offset_for_iiss_variable(
            cls, context: 'IconScoreContext', offset: int):
        context.iiss_engine.apply_candidate_delegated_offset_for_iiss_variable(context, offset)

    @classmethod
    def handle_get_prep_candidate(cls, context: 'IconScoreContext', params: dict) -> dict:

        ret_params: dict = TypeConverter.convert(params, ParamType.IISS_GET_PREP_CANDIDATE)
        address: 'Address' = ret_params[ConstantKeys.ADDRESS]
        return cls._get_prep_candidate(context, address)

    @classmethod
    def _get_prep_candidate(cls, context: 'IconScoreContext', address: 'Address') -> dict:

        if not cls._is_candidate(context, address):
            raise InvalidParamsException(f"P-Rep candidate not found: {str(address)}")

        candidate: 'Candidate' = context.prep_storage.get_candidate(context, address)
        return candidate.to_dict()

    @classmethod
    def handle_set_prep_candidate(
            cls, context: 'IconScoreContext', params: dict, tx_result: 'TransactionResult'):
        address: 'Address' = context.tx.origin
        prep_engine = context.prep_engine
        prep_storage = context.prep_storage

        candidate: 'Candidate' = prep_engine.candidates.get(address)
        if candidate is None:
            raise InvalidParamsException(f"P-Rep candidate not found: str{address}")

        ret_params: dict = TypeConverter.convert(params, ParamType.IISS_SET_PREP_CANDIDATE)
        candidate.set(ret_params)

        prep_storage.put_candidate(context, candidate)

    @classmethod
    def handle_unreg_prep_candidate(
            cls, context: 'IconScoreContext', params: dict, tx_result: 'TransactionResult'):
        """Unregister a P-Rep candidate

        :param context:
        :param params:
        :param tx_result:
        :return:
        """
        address: 'Address' = context.tx.origin
        prep_engine = context.prep_engine

        candidate: 'Candidate' = prep_engine.candidates.get(address)
        if candidate is None:
            raise InvalidParamsException(f"P-Rep candidate not found: str{address}")

        cls._del_prep_candidate_for_state_db(context, candidate)
        cls._put_unreg_prep_candidate_for_iiss_db(context, address)

    @classmethod
    def _del_prep_candidate_for_state_db(
            cls, context: 'IconScoreContext', candidate: 'Candidate'):
        context.prep_storage.delete_candidate(context, candidate.address)
        cls._apply_candidate_delegated_offset_for_iiss_variable(context, -candidate.delegated)

    @classmethod
    def _put_unreg_prep_candidate_for_iiss_db(
            cls, context: 'IconScoreContext', address: 'Address'):
        context.iiss_engine.put_unreg_prep_candidate_for_iiss_db(
            context.rc_tx_batch, address, context.block.height)

    @classmethod
    def handle_get_prep_candidate_delegation_info(
            cls, context: 'IconScoreContext', params: dict) -> dict:
        ret_params: dict = TypeConverter.convert(params, ParamType.IISS_GET_PREP_CANDIDATE_DELEGATION_INFO)
        address: 'Address' = ret_params[ConstantKeys.ADDRESS]

        return cls._get_prep_candidate_delegation_info(context, address)

    @classmethod
    def _get_prep_candidate_delegation_info(
            cls, context: 'IconScoreContext', address: 'Address') -> dict:
        candidates: 'CandidateContainer' = context.prep_engine.candidates.get(address)
        candidate = candidates.get(address)
        ranking: int = candidates.get_ranking(address)

        if candidate is None:
            raise InvalidParamsException(f"P-Rep candidate not found: {str(address)}")

        return {
            "ranking": ranking,
            "delegated": candidate.delegated
        }

def put_reg_prep_candidate_for_rc_data(self,
                                       batch: list,
                                       address: 'Address',
                                       block_height: int):
    tx: 'PRepRegisterTx' = RewardCalcDataCreator.create_tx_prep_reg()
    iiss_tx_data: 'TxData' = RewardCalcDataCreator.create_tx(address, block_height, tx)
    self._rc_storage.storage.rc.put(batch, iiss_tx_data)

def put_unreg_prep_candidate_for_iiss_db(self,
                                         batch: list,
                                         address: 'Address',
                                         block_height: int):
    tx: 'PRepUnregisterTx' = RewardCalcDataCreator.create_tx_prep_unreg()
    iiss_tx_data: 'TxData' = RewardCalcDataCreator.create_tx(address, block_height, tx)
    self._rc_storage.put(batch, iiss_tx_data)

def apply_candidate_delegated_offset_for_iiss_variable(self,
                                                       context: 'IconScoreContext',
                                                       offset: int):
    total_delegated_amount: int = self._variable.issue.get_total_candidate_delegated(context)
    self._variable.issue.put_total_candidate_delegated(context,
                                                       total_delegated_amount + offset)


"""
    @classmethod
    def handle_get_prep_list(cls, context: 'IconScoreContext', params: dict) -> dict:
        preps: List['Candidate'] = context.prep_engine.candidates.get_preps()
        result: dict = {}
        total_delegated: int = 0

        preps_in_result = []
        for prep in preps:
            item = {
                "address": prep.address,
                "delegated": prep.delegated
            }
            preps_in_result.append(item)
            total_delegated += prep.delegated

        result["totalDelegated"] = total_delegated
        result["preps"] = preps_in_result

        return result

    @classmethod
    def handle_get_prep_candidate_list(cls, context: 'IconScoreContext', params: dict) -> dict:
        ret_params: dict = TypeConverter.convert(params, ParamType.IISS_GET_PREP_CANDIDATE_LIST)
        return cls._get_prep_candidate_list(context, ret_params)

    @classmethod
    def _get_prep_candidate_list(cls, context: 'IconScoreContext', params: dict) -> dict:
        candidates: 'CandidateContainer' = context.prep_engine.candidates
        total_delegated: int = 0
        candidate_list = []

        start_index: int = params.get(ConstantKeys.START_RANKING, 1) - 1
        end_index: int = params.get(ConstantKeys.END_RANKING, len(candidates))

        for i in range(start_index, end_index):
            candidate: 'Candidate' = candidates[i]

            item = {
                "address": candidate.address,
                "delegated": candidate.delegated
            }
            candidate_list.append(item)

            total_delegated += candidate.delegated

        return {
            "totalDelegated": total_delegated,
            "candidates": candidate_list
        }
"""
