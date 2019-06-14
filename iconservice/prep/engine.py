# Copyright 2019 ICON Foundation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from typing import TYPE_CHECKING, Any

from iconcommons.logger import Logger
from .data.candidate import Candidate
from .data.candidate_container import CandidateContainer
from .term import Term
from ..base.ComponentBase import EngineBase
from ..base.address import Address
from ..base.type_converter import TypeConverter, ParamType
from ..base.type_converter_templates import ConstantKeys
from ..icon_constant import PREP_COUNT
from ..iconscore.icon_score_result import TransactionResult
from ..icx.storage import Intent
from ..iiss.reward_calc import RewardCalcDataCreator

if TYPE_CHECKING:
    from . import PRepStorage
    from ..iiss.reward_calc.msg_data import *
    from ..iconscore.icon_score_context import IconScoreContext
    from ..icx.icx_account import Account
    from ..icx import IcxStorage


class Engine(EngineBase):
    """PRepEngine class

    Manages P-Rep candidates and handles P-Rep related JSON-RPC API requests
    """

    def __init__(self) -> None:
        super().__init__()
        Logger.debug("PRepEngine.__init__() start")

        self._invoke_handlers: dict = {
            "registerPRepCandidate": self.handle_register_prep_candidate,
            "setPRepCandidate": self.handle_set_prep_candidate,
            "unregisterPRepCandidate": self.handle_unregister_prep_candidate
        }

        self._query_handler: dict = {
            "getPRepCandidate": self.handle_get_prep_candidate,
            "getPRepCandidateDelegationInfo": self.handle_get_prep_candidate_delegation_info,
            "getPRepList": self.handle_get_prep_list,
            "getPRepCandidateList": self.handle_get_prep_candidate_list
        }

        self.candidates: Optional['CandidateContainer'] = None
        self.term = Term()

        Logger.debug("PRepEngine.__init__() end")

    def open(self, context: 'IconScoreContext', term_period: int, governance_variable: dict) -> None:
        self.candidates = CandidateContainer()
        self.candidates.load(context)
        self.term.load(context, term_period, governance_variable)

    def invoke(self, context: 'IconScoreContext', data: dict, tx_result: 'TransactionResult') -> None:
        method: str = data['method']
        params: dict = data['params']

        handler: callable = self._invoke_handlers[method]
        handler(context, params, tx_result)

    def query(self, context: 'IconScoreContext', data: dict) -> Any:
        method: str = data['method']
        params: dict = data['params']

        handler: callable = self._query_handler[method]
        ret = handler(context, params)
        return ret

    def commit(self, context: 'IconScoreContext'):
        """If the current P-Rep term is over, update term with new information
        which has P-Rep list(address, delegated amount), start height, end height, incentive_rep

        :param context:
        :return:
        """
        pass

    def rollback(self):
        pass

    def handle_register_prep_candidate(
            self, context: 'IconScoreContext', params: dict, tx_result: 'TransactionResult'):
        """Register a P-Rep candidate

        Roles
        * Update candidates in context
        * Update stateDB
        * Update rcDB

        :param context: 
        :param params: 
        :param tx_result: 
        :return: 
        """
        icx_storage: 'IcxStorage' = context.storage.icx
        prep_storage: 'PRepStorage' = context.storage.prep

        address: 'Address' = context.tx.origin
        if address in context.candidates:
            raise InvalidParamsException(f"{str(address)} has been already registered")

        ret_params: dict = TypeConverter.convert(params, ParamType.IISS_REG_PREP_CANDIDATE)
        account: 'Account' = icx_storage.get_account(context, address, Intent.DELEGATED)

        # Create a candidate object and assign delegated amount from account to candidate
        candidate = Candidate.from_dict(address, ret_params, context.block.height, context.tx.index)
        candidate.delegated = account.delegated_amount

        # Update candidates in context
        context.candidates.add(candidate)

        # Update stateDB
        prep_storage.put_candidate(context, candidate)
        self._apply_candidate_delegated_offset_for_iiss_variable(context, candidate.delegated)

        # Update rcDB
        self._put_reg_prep_candidate_for_rc_data(context, address)

    @staticmethod
    def _put_reg_prep_candidate_for_rc_data(context: 'IconScoreContext', address: 'Address'):
        rc_tx_batch: list = context.rc_tx_batch
        block_height: int = context.block.height

        tx: 'PRepRegisterTx' = RewardCalcDataCreator.create_tx_prep_reg()
        iiss_tx_data: 'TxData' = RewardCalcDataCreator.create_tx(address, block_height, tx)
        context.storage.rc.put(rc_tx_batch, iiss_tx_data)

    @staticmethod
    def _put_unreg_prep_candidate_for_iiss_db(context: 'IconScoreContext', address: 'Address'):
        rc_tx_batch: list = context.rc_tx_batch
        block_height: int = context.block.height

        tx: 'PRepUnregisterTx' = RewardCalcDataCreator.create_tx_prep_unreg()
        iiss_tx_data: 'TxData' = RewardCalcDataCreator.create_tx(address, block_height, tx)
        context.storage.rc.put(rc_tx_batch, iiss_tx_data)

    @staticmethod
    def _apply_candidate_delegated_offset_for_iiss_variable(
            context: 'IconScoreContext', offset: int):
        total_delegated_amount: int = context.storage.iiss.get_total_candidate_delegated(context)
        context.storage.iiss.put_total_candidate_delegated(context, total_delegated_amount + offset)

    def handle_get_prep_candidate(self, context: 'IconScoreContext', params: dict) -> dict:
        """Returns registration information of a P-Rep candidate

        :param context:
        :param params:
        :return:
        """
        ret_params: dict = TypeConverter.convert(params, ParamType.IISS_GET_PREP_CANDIDATE)
        address: 'Address' = ret_params[ConstantKeys.ADDRESS]

        candidate: 'Candidate' = self.candidates.get(address)
        if candidate is None:
            raise InvalidParamsException(f"P-Rep candidate not found: {str(address)}")

        return candidate.to_dict()

    @staticmethod
    def handle_set_prep_candidate(
            context: 'IconScoreContext', params: dict, tx_result: 'TransactionResult'):
        """Update a P-Rep candidate registration information

        :param context:
        :param params:
        :param tx_result:
        :return:
        """
        prep_storage = context.storage.prep
        address: 'Address' = context.tx.origin

        candidate: 'Candidate' = context.candidates.get(address)
        if candidate is None:
            raise InvalidParamsException(f"P-Rep candidate not found: str{address}")

        ret_params: dict = TypeConverter.convert(params, ParamType.IISS_SET_PREP_CANDIDATE)
        candidate.set(ret_params)

        # Update a new P-Rep candidate registration info to stateDB
        prep_storage.put_candidate(context, candidate)

    def handle_unregister_prep_candidate(
            self, context: 'IconScoreContext', params: dict, tx_result: 'TransactionResult'):
        """Unregister a P-Rep candidate

        :param context:
        :param params:
        :param tx_result:
        :return:
        """
        prep_storage: 'PRepStorage' = context.storage.prep
        address: 'Address' = context.tx.origin

        candidate: 'Candidate' = context.candidates.get(address)
        if candidate is None:
            raise InvalidParamsException(f"P-Rep candidate not found: str{address}")

        # Update candidates in context
        context.candidates.remove(address)

        # Update stateDB
        prep_storage.delete_candidate(context, address)
        self._apply_candidate_delegated_offset_for_iiss_variable(context, -candidate.delegated)

        # Update rcDB
        self._put_unreg_prep_candidate_for_iiss_db(context, address)

    def handle_get_prep_candidate_delegation_info(
            self, context: 'IconScoreContext', params: dict) -> dict:
        """Returns delegation info of a P-Rep candidate

        :param context:
        :param params:
        :return:
        """
        ret_params: dict = TypeConverter.convert(
            params, ParamType.IISS_GET_PREP_CANDIDATE_DELEGATION_INFO)
        address: 'Address' = ret_params[ConstantKeys.ADDRESS]

        candidate = self.candidates.get(address)
        ranking: int = self.candidates.get_ranking(address)

        if candidate is None:
            raise InvalidParamsException(f"P-Rep candidate not found: {str(address)}")

        return {
            "ranking": ranking,
            "delegated": candidate.delegated
        }

    def handle_get_prep_list(self, context: 'IconScoreContext', params: dict) -> dict:
        """Returns 22 P-Rep list in the present term

        :param context:
        :param params:
        :return:
        """
        candidates: 'CandidateContainer' = self.candidates
        total_delegated: int = 0
        preps = []

        for prep in candidates:
            item = {
                "address": prep.address,
                "delegated": prep.delegated
            }
            preps.append(item)
            total_delegated += prep.delegated

            if len(preps) == PREP_COUNT:
                break

        return {
            "totalDelegated": total_delegated,
            "preps": preps
        }

    def handle_get_prep_candidate_list(self, context: 'IconScoreContext', params: dict) -> dict:
        """Returns P-Rep candidate list with start and end rankings

        :param context:
        :param params:
        :return:
        """
        ret_params: dict = TypeConverter.convert(params, ParamType.IISS_GET_PREP_CANDIDATE_LIST)

        candidates: 'CandidateContainer' = self.candidates
        total_delegated: int = 0
        candidate_list = []

        start_index: int = ret_params.get(ConstantKeys.START_RANKING, 1) - 1
        end_index: int = ret_params.get(ConstantKeys.END_RANKING, len(candidates))

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
