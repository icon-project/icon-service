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

import hashlib
from collections import OrderedDict
from typing import TYPE_CHECKING, Any, Optional, List

from iconcommons.logger import Logger

from .data.prep import PRep
from .data.prep_container import PRepContainer
from .term import Term
from ..base.ComponentBase import EngineBase
from ..base.address import Address, ZERO_SCORE_ADDRESS
from ..base.exception import InvalidParamsException, InvalidRequestException
from ..base.type_converter import TypeConverter, ParamType
from ..base.type_converter_templates import ConstantKeys
from ..icon_constant import IISS_MIN_IREP, IISS_MAX_IREP, IISS_MAX_DELEGATIONS
from ..icon_constant import PrepResultState, PREP_MAIN_PREPS, PREP_MAIN_AND_SUB_PREPS
from ..iconscore.icon_score_context import IconScoreContext
from ..iconscore.icon_score_event_log import EventLogEmitter
from ..icx.icx_account import Account
from ..icx.storage import Intent
from ..iiss import IISSEngineListener
from ..iiss.reward_calc import RewardCalcDataCreator

if TYPE_CHECKING:
    from . import PRepStorage
    from ..iiss.reward_calc.msg_data import PRepRegisterTx, PRepUnregisterTx, TxData
    from ..icx import IcxStorage
    from ..precommit_data_manager import PrecommitData


class Engine(EngineBase, IISSEngineListener):
    """PRepEngine class

    Roles:
    * Manages term and preps
    * Handles P-Rep related JSON-RPC API requests
    """
    def __init__(self):
        super().__init__()
        Logger.debug("PRepEngine.__init__() start")

        self._invoke_handlers: dict = {
            "registerPRep": self.handle_register_prep,
            "setPRep": self.handle_set_prep,
            "unregisterPRep": self.handle_unregister_prep
        }

        self._query_handler: dict = {
            "getPRep": self.handle_get_prep,
            "getMainPRepList": self.handle_get_main_prep_list,
            "getSubPRepList": self.handle_get_sub_prep_list,
            "getPRepList": self.handle_get_prep_list
        }

        self.preps: Optional['PRepContainer'] = None
        self.term = Term()

        Logger.debug("PRepEngine.__init__() end")

    def open(self, context: 'IconScoreContext', term_period: int, irep: int):
        self.preps = PRepContainer()
        self.preps.load(context)
        self.term.load(context, term_period, irep)

        context.engine.iiss.add_listener(self)

    def close(self):
        IconScoreContext.engine.iiss.remove_listener(self)

    def invoke(self, context: 'IconScoreContext', data: dict):
        method: str = data['method']
        params: dict = data['params']

        handler: callable = self._invoke_handlers[method]
        handler(context, params)

    def query(self, context: 'IconScoreContext', data: dict) -> Any:
        method: str = data['method']
        params: dict = data.get('params', {})

        handler: callable = self._query_handler[method]
        ret = handler(context, params)
        return ret

    def commit(self, _context: 'IconScoreContext', precommit_data: 'PrecommitData'):
        """If the current P-Rep term is over, update term with new information
        which has P-Rep list(address, delegated amount), start height, end height, irep

        :param _context:
        :param precommit_data:
        :return:
        """
        self.preps = precommit_data.preps

    def rollback(self):
        pass

    def handle_register_prep(
            self, context: 'IconScoreContext', params: dict):
        """Register a P-Rep

        Roles
        * Update preps in context
        * Update stateDB
        * Update rcDB

        :param context: 
        :param params:
        :return: 
        """
        icx_storage: 'IcxStorage' = context.storage.icx
        prep_storage: 'PRepStorage' = context.storage.prep

        address: 'Address' = context.tx.origin
        if context.preps.contains(address, inactive_preps_included=True):
            raise InvalidParamsException(f"{str(address)} has been already registered")

        ret_params: dict = TypeConverter.convert(params, ParamType.IISS_REG_PREP)
        account: 'Account' = icx_storage.get_account(context, address, Intent.DELEGATED)

        # Create a PRep object and assign delegated amount from account to prep
        # prep.irep is set to IISS_MIN_IREP by default
        prep = PRep.from_dict(address, ret_params, context.block.height, context.tx.index)
        prep.delegated = account.delegated_amount

        # Update preps in context
        context.preps.add(prep)

        # Update stateDB
        prep_storage.put_prep(context, prep)

        # Update rcDB
        self._put_reg_prep_in_rc_db(context, address)

        # EventLog
        EventLogEmitter.emit_event_log(
            context,
            score_address=ZERO_SCORE_ADDRESS,
            event_signature="PRepRegistered(Address)",
            arguments=[address],
            indexed_args_count=0
        )

    @staticmethod
    def _put_reg_prep_in_rc_db(context: 'IconScoreContext', address: 'Address'):
        """Put a newly registered P-Rep in RewardCalcDatabase

        :param context:
        :param address: The address of P-Rep
        :return:
        """

        rc_tx_batch: list = context.rc_tx_batch
        block_height: int = context.block.height

        tx: 'PRepRegisterTx' = RewardCalcDataCreator.create_tx_prep_reg()
        iiss_tx_data: 'TxData' = RewardCalcDataCreator.create_tx(address, block_height, tx)
        context.storage.rc.put(rc_tx_batch, iiss_tx_data)

    def check_end_block_height_of_term(self, context: 'IconScoreContext') -> bool:
        """Is the last block of the current term

        :param context:
        :return:
        """
        return self.term.end_block_height == context.block.height

    def make_prep_tx_result(self) -> Optional[dict]:
        prep_as_dict = self.get_main_preps_in_term()
        if prep_as_dict:
            prep_as_dict['irep'] = self.term.irep
            prep_as_dict['state'] = PrepResultState.NORMAL.value
            return prep_as_dict
        return None

    def get_main_preps_in_term(self) -> Optional[dict]:
        main_preps = self.term.main_preps
        prep_as_dict = None
        if len(main_preps) > 0:
            prep_as_dict = OrderedDict()
            preps_as_list = []
            prep_addresses_for_roothash = b''
            for prep in main_preps:
                prep_info_as_dict = OrderedDict()
                prep_info_as_dict[ConstantKeys.PREP_ID] = prep.address
                prep_info_as_dict[ConstantKeys.PUBLIC_KEY] = prep.public_key
                prep_info_as_dict[ConstantKeys.P2P_END_POINT] = prep.p2p_end_point
                preps_as_list.append(prep_info_as_dict)
                prep_addresses_for_roothash += prep.address.to_bytes_including_prefix()
            prep_as_dict["preps"] = preps_as_list
            prep_as_dict["rootHash"] = hashlib.sha3_256(prep_addresses_for_roothash).digest()
        return prep_as_dict

    def save_term(self, context: 'IconScoreContext', weighted_average_of_irep: int):
        self.term.save(context,
                       context.block.height,
                       context.preps.get_preps(start_index=0, size=PREP_MAIN_AND_SUB_PREPS),
                       weighted_average_of_irep,
                       context.total_supply)

    @staticmethod
    def calculate_weighted_average_of_irep(context: 'IconScoreContext') -> int:
        preps: 'PRepContainer' = context.preps
        assert len(preps) >= PREP_MAIN_PREPS

        total_delegated = 0  # total delegated of prep
        total_weighted_irep = 0

        for i in range(PREP_MAIN_PREPS):
            prep: 'PRep' = preps.get_by_index(i)
            total_weighted_irep += prep.irep * prep.delegated
            total_delegated += prep.delegated

        return total_weighted_irep // total_delegated if total_delegated > 0 else 0

    def handle_get_prep(self, context: 'IconScoreContext', params: dict) -> dict:
        """Returns the details of a P-Rep including information on registration, delegation and statistics

        :param _context:
        :param params:
        :return:
        """
        ret_params: dict = TypeConverter.convert(params, ParamType.IISS_GET_PREP)
        address: 'Address' = ret_params[ConstantKeys.ADDRESS]

        prep: 'PRep' = self.preps.get_by_address(address)
        if prep is None:
            raise InvalidParamsException(f"P-Rep not found: {str(address)}")

        account: 'Account' = context.storage.icx.get_account(context, address, Intent.STAKE)

        response: dict = prep.to_dict()
        response['delegation']['stake'] = account.stake
        return response

    def handle_set_prep(self, context: 'IconScoreContext', params: dict):
        """Update a P-Rep registration information

        :param context:
        :param params:
        :return:
        """
        prep_storage = context.storage.prep
        address: 'Address' = context.tx.origin

        prep: 'PRep' = context.preps.get_by_address(address, mutable=True)
        if prep is None:
            raise InvalidParamsException(f"P-Rep not found: {str(address)}")

        kwargs: dict = TypeConverter.convert(params, ParamType.IISS_SET_PREP)

        # Update incentive rep
        if "irep" in kwargs:
            irep: int = kwargs["irep"]
            del kwargs["irep"]
            self._set_irep_to_prep(context, irep, prep)

        if "p2pEndPoint" in kwargs:
            p2p_end_point: str = kwargs["p2pEndPoint"]
            del kwargs["p2pEndPoint"]
            kwargs["p2p_end_point"] = p2p_end_point

        # Update registration info
        prep.set(**kwargs)

        # Update a new P-Rep registration info to stateDB
        prep_storage.put_prep(context, prep)

        # EventLog
        EventLogEmitter.emit_event_log(
            context,
            score_address=ZERO_SCORE_ADDRESS,
            event_signature="PRepSet(Address)",
            arguments=[address],
            indexed_args_count=0
        )

    def _set_irep_to_prep(self, context: 'IconScoreContext', irep: int, prep: 'PRep'):
        prev_prep: 'PRep' = prep
        self._validate_irep(context, irep, prev_prep)

        prep.set_irep(irep, context.block.height)

    @classmethod
    def _validate_irep(cls, context: 'IconScoreContext', irep: int, prev_prep: 'PRep'):
        """Validate irep

        :param context:
        :param irep:
        :param prev_prep:
        :return:
        """
        if not (IISS_MIN_IREP <= irep <= IISS_MAX_IREP):
            raise InvalidParamsException(f"Invalid irep: {irep}")

        term: 'Term' = context.engine.prep.term
        prev_irep = prev_prep.irep
        prev_irep_updated_block_height = prev_prep.irep_block_height

        if term.sequence == -1:
            raise InvalidRequestException("irep can be set after decentralized")

        if prev_irep_updated_block_height >= term.start_block_height:
            raise InvalidRequestException("irep can only be changed once during the term.")
        min_irep: int = prev_irep * 8 // 10  # 80% of previous irep
        max_irep: int = prev_irep * 12 // 10  # 120% of previous irep

        if min_irep <= irep <= max_irep:
            context.engine.issue.validate_total_supply_limit(context, irep)
            return

        raise InvalidParamsException(f"Irep out of range: {irep}, {prev_irep}")

    def handle_unregister_prep(self, context: 'IconScoreContext', _params: dict):
        """Unregister a P-Rep

        :param context:
        :param _params:
        :return:
        """
        prep_storage: 'PRepStorage' = context.storage.prep
        address: 'Address' = context.tx.origin

        # Remove a given P-Rep from context.preps
        context.preps.remove(address)

        # Update stateDB
        prep_storage.delete_prep(context, address)

        # Update rcDB
        self._put_unreg_prep_for_iiss_db(context, address)

        # EventLog
        EventLogEmitter.emit_event_log(
            context,
            score_address=ZERO_SCORE_ADDRESS,
            event_signature="PRepUnregistered(Address)",
            arguments=[address],
            indexed_args_count=0
        )

    @staticmethod
    def _put_unreg_prep_for_iiss_db(context: 'IconScoreContext', address: 'Address'):
        rc_tx_batch: list = context.rc_tx_batch
        block_height: int = context.block.height

        tx: 'PRepUnregisterTx' = RewardCalcDataCreator.create_tx_prep_unreg()
        iiss_tx_data: 'TxData' = RewardCalcDataCreator.create_tx(address, block_height, tx)
        context.storage.rc.put(rc_tx_batch, iiss_tx_data)

    def handle_get_main_prep_list(self, _context: 'IconScoreContext', _params: dict) -> dict:
        """Returns 22 P-Rep list in the current term

        :param _context:
        :param _params:
        :return:
        """
        preps: List['PRep'] = self.term.main_preps
        total_delegated: int = 0
        prep_list: list = []

        for prep in preps:
            item = {
                "address": prep.address,
                "delegated": prep.delegated
            }
            prep_list.append(item)
            total_delegated += prep.delegated

        return {
            "totalDelegated": total_delegated,
            "preps": prep_list
        }

    def handle_get_sub_prep_list(self, _context: 'IconScoreContext', _params: dict) -> dict:
        """Returns 22 P-Rep list in the present term

        :param _context:
        :param _params:
        :return:
        """
        preps: List['PRep'] = self.term.sub_preps
        total_delegated: int = 0
        prep_list: list = []

        for prep in preps:
            item = {
                "address": prep.address,
                "delegated": prep.delegated
            }
            prep_list.append(item)
            total_delegated += prep.delegated

        return {
            "totalDelegated": total_delegated,
            "preps": prep_list
        }

    def handle_get_prep_list(self, _context: 'IconScoreContext', params: dict) -> dict:
        """Returns P-Rep list with start and end rankings

        P-Rep means all P-Reps including main P-Reps and sub P-Reps

        :param _context:
        :param params:
        :return:
        """
        ret_params: dict = TypeConverter.convert(params, ParamType.IISS_GET_PREP_LIST)

        preps: 'PRepContainer' = self.preps
        total_delegated: int = 0
        prep_list: list = []

        prep_count: int = len(preps)

        start_ranking: int = ret_params.get(ConstantKeys.START_RANKING, 1)
        end_ranking: int = ret_params.get(ConstantKeys.END_RANKING, prep_count)

        if not 1 <= start_ranking <= end_ranking <= prep_count:
            raise InvalidParamsException(
                f"Invalid ranking: startRanking({start_ranking}), endRanking({end_ranking})")

        for i in range(start_ranking - 1, end_ranking):
            prep: 'PRep' = preps.get_by_index(i)
            prep_list.append({"address": prep.address, "delegated": prep.delegated})
            total_delegated += prep.delegated

        return {
            "startRanking": start_ranking,
            "totalDelegated": total_delegated,
            "preps": prep_list
        }

    # IISSEngineListener implementation ---------------------------
    def on_set_stake(self, context: 'IconScoreContext', account: 'Account'):
        """Called on IISSEngine.handle_set_stake()

        :param context:
        :param account:
        :return:
        """
        pass

    def on_set_delegation(
            self, context: 'IconScoreContext', delegated_accounts: List['Account']):
        """Called on IISSEngine.handle_set_delegation()

        :param context:
        :param delegated_accounts:
        return:
        """
        assert 0 <= len(delegated_accounts) <= IISS_MAX_DELEGATIONS * 2

        for account in delegated_accounts:
            assert isinstance(account, Account)
            address = account.address

            # If a delegated account is a P-Rep, then update its delegated amount
            if address in context.preps:
                context.preps.set_delegated_to_prep(address, account.delegated_amount)
