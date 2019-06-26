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
from ..base.exception import InvalidParamsException
from ..base.type_converter import TypeConverter, ParamType
from ..base.type_converter_templates import ConstantKeys
from ..icon_constant import PrepResultState, IISS_MIN_IREP, IISS_MAX_IREP, PREP_MAIN_PREPS, PREP_MAIN_AND_SUB_PREPS
from ..iconscore.icon_score_event_log import EventLogEmitter
from ..icx.storage import Intent
from ..iiss.reward_calc import RewardCalcDataCreator

if TYPE_CHECKING:
    from . import PRepStorage
    from ..iiss.reward_calc.msg_data import PRepRegisterTx, PRepUnregisterTx, TxData
    from ..iiss import IISSStorage
    from ..iconscore.icon_score_context import IconScoreContext
    from ..icx.icx_account import Account
    from ..icx import IcxStorage
    from ..precommit_data_manager import PrecommitData


class Engine(EngineBase):
    """PRepEngine class

    Manages preps and handles P-Rep related JSON-RPC API requests
    """

    def __init__(self) -> None:
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

    def open(self, context: 'IconScoreContext', term_period: int, irep: int) -> None:
        self.preps = PRepContainer()
        self.preps.load(context)
        self.term.load(context, term_period, irep)

    def invoke(self, context: 'IconScoreContext', data: dict) -> None:
        method: str = data['method']
        params: dict = data['params']

        handler: callable = self._invoke_handlers[method]
        handler(context, params)

    def query(self, context: 'IconScoreContext', data: dict) -> Any:
        method: str = data['method']
        params: dict = data['params']

        handler: callable = self._query_handler[method]
        ret = handler(context, params)
        return ret

    def commit(self, context: 'IconScoreContext', precommit_data: 'PrecommitData'):
        """If the current P-Rep term is over, update term with new information
        which has P-Rep list(address, delegated amount), start height, end height, irep

        :param context:
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
        self._put_total_prep_delegated_in_state_db(context, prep.delegated)

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

    @staticmethod
    def _put_total_prep_delegated_in_state_db(context: 'IconScoreContext', offset: int):
        """Put total prep delegated to StateDatabase

        :param context:
        :param offset:
        :return:
        """
        if offset == 0:
            # No need to update total prep delegated
            return

        storage: 'IISSStorage' = context.storage.iiss

        total_delegated: int = storage.get_total_prep_delegated(context)
        storage.put_total_prep_delegated(context, total_delegated + offset)

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
        """Returns the details of a P-Rep including info of registration, delegation and statistics

        :param context:
        :param params:
        :return:
        """
        ret_params: dict = TypeConverter.convert(params, ParamType.IISS_GET_PREP)
        address: 'Address' = ret_params[ConstantKeys.ADDRESS]

        prep: 'PRep' = self.preps.get(address)
        if prep is None:
            raise InvalidParamsException(f"P-Rep not found: {str(address)}")

        return prep.to_dict()

    def handle_set_prep(self, context: 'IconScoreContext', params: dict):
        """Update a P-Rep registration information

        :param context:
        :param params:
        :return:
        """
        prep_storage = context.storage.prep
        address: 'Address' = context.tx.origin

        prep: 'PRep' = context.preps.get(address)
        if prep is None:
            raise InvalidParamsException(f"P-Rep not found: str{address}")
        prev_irep: int = prep.irep
        ret_params: dict = TypeConverter.convert(params, ParamType.IISS_SET_PREP)
        prep.set(context.block.height, **ret_params)
        self._validate_irep(context, prep.irep, prev_irep)

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

    @classmethod
    def _validate_irep(cls, context: 'IconScoreContext', irep: int, prev_irep: int = None):
        """Validate irep

        :param context:
        :param irep:
        :param prev_irep:
        :return:
        """
        if not (IISS_MIN_IREP <= irep <= IISS_MAX_IREP):
            raise InvalidParamsException(f"Invalid irep: {irep}")

        if prev_irep is None:
            return

        min_irep: int = prev_irep * 8 // 10  # 80% of previous irep
        max_irep: int = prev_irep * 12 // 10  # 120% of previous irep

        if min_irep <= irep <= max_irep:
            context.engine.issue.validate_total_supply_limit(context, irep)
            return

        raise InvalidParamsException(f"Irep out of range: {irep}, {prev_irep}")

    def handle_unregister_prep(self, context: 'IconScoreContext', params: dict):
        """Unregister a P-Rep

        :param context:
        :param params:
        :return:
        """
        prep_storage: 'PRepStorage' = context.storage.prep
        address: 'Address' = context.tx.origin

        prep: 'PRep' = context.preps.get(address)
        if prep is None:
            raise InvalidParamsException(f"P-Rep not found: str{address}")

        # Update preps in context
        context.preps.remove(address)

        # Update stateDB
        prep_storage.delete_prep(context, address)
        self._put_total_prep_delegated_in_state_db(context, -prep.delegated)

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

    def handle_get_main_prep_list(self, context: 'IconScoreContext', params: dict) -> dict:
        """Returns 22 P-Rep list in the present term

        :param context:
        :param params:
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

    def handle_get_sub_prep_list(self, context: 'IconScoreContext', params: dict) -> dict:
        """Returns 22 P-Rep list in the present term

        :param context:
        :param params:
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

    def handle_get_prep_list(self, context: 'IconScoreContext', params: dict) -> dict:
        """Returns P-Rep list with start and end rankings

        :param context:
        :param params:
        :return:
        """
        ret_params: dict = TypeConverter.convert(params, ParamType.IISS_GET_PREP_LIST)

        preps: 'PRepContainer' = self.preps
        total_delegated: int = 0
        prep_list: list = []

        start_index: int = ret_params.get(ConstantKeys.START_RANKING, 1)
        if start_index <= 0:
            raise InvalidParamsException("Invalid params: startRanking")

        end_index: int = ret_params.get(ConstantKeys.END_RANKING, len(preps))
        if end_index <= 0:
            raise InvalidParamsException("Invalid params: endRanking")

        if start_index > end_index:
            raise InvalidParamsException("Invalid params: reverse")

        for i in range(start_index - 1, end_index):
            prep: 'PRep' = preps.get_by_index(i)

            item = {
                "address": prep.address,
                "delegated": prep.delegated
            }
            prep_list.append(item)
            total_delegated += prep.delegated

        return {
            "startRanking": start_index,
            "totalDelegated": total_delegated,
            "preps": prep_list
        }
