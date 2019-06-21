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
from typing import TYPE_CHECKING, Any, Optional

from iconcommons.logger import Logger

from .data.prep import PRep
from .data.prep_container import PRepContainer
from .term import Term
from ..base.ComponentBase import EngineBase
from ..base.address import Address, ZERO_SCORE_ADDRESS
from ..base.exception import InvalidParamsException
from ..base.type_converter import TypeConverter, ParamType
from ..base.type_converter_templates import ConstantKeys
from ..iconscore.icon_score_event_log import EventLogEmitter
from ..icx.storage import Intent
from ..iiss.reward_calc import RewardCalcDataCreator
from ..precommit_data_manager import PrecommitData
from ..icon_constant import PrepResultState, IISS_MIN_IREP

if TYPE_CHECKING:
    from . import PRepStorage
    from ..iiss.reward_calc.msg_data import PRepRegisterTx, PRepUnregisterTx, TxData
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
        if address in context.preps:
            raise InvalidParamsException(f"{str(address)} has been already registered")

        ret_params: dict = TypeConverter.convert(params, ParamType.IISS_REG_PREP)
        account: 'Account' = icx_storage.get_account(context, address, Intent.DELEGATED)

        # Create a PRep object and assign delegated amount from account to prep
        prep = PRep.from_dict(address, ret_params, context.block.height, context.tx.index)
        prep.delegated = account.delegated_amount
        self._validate_limit_irep(context, prep)

        # Update preps in context
        context.preps.add(prep)

        # Update stateDB
        prep_storage.put_prep(context, prep)
        self._apply_prep_delegated_offset_for_iiss_variable(context, prep.delegated)

        # Update rcDB
        self._put_reg_prep_for_rc_data(context, address)

        self._create_tx_result(context, 'PRepRegistered(Address)', address)

    @classmethod
    def _create_tx_result(cls, context: 'IconScoreContext', event_signature: str, address: 'Address'):
        # make tx result
        arguments = [address]
        index = 0
        EventLogEmitter.emit_event_log(context, ZERO_SCORE_ADDRESS, event_signature, arguments, index)

    @staticmethod
    def _put_reg_prep_for_rc_data(context: 'IconScoreContext', address: 'Address'):
        rc_tx_batch: list = context.rc_tx_batch
        block_height: int = context.block.height

        tx: 'PRepRegisterTx' = RewardCalcDataCreator.create_tx_prep_reg()
        iiss_tx_data: 'TxData' = RewardCalcDataCreator.create_tx(address, block_height, tx)
        context.storage.rc.put(rc_tx_batch, iiss_tx_data)

    @staticmethod
    def _apply_prep_delegated_offset_for_iiss_variable(
            context: 'IconScoreContext', offset: int):
        total_delegated_amount: int = context.storage.iiss.get_total_prep_delegated(context)
        context.storage.iiss.put_total_prep_delegated(context, total_delegated_amount + offset)

    def check_term_end_block_height(self, context: 'IconScoreContext') -> bool:
        return self.term.end_block_height in (context.block.height, -1)

    def make_prep_tx_result(self) -> Optional[dict]:
        main_preps = self.term.main_preps
        prep_as_dict = None
        if len(main_preps) > 0:
            prep_as_dict = OrderedDict()
            preps_as_list = []
            preps_as_list_for_roothash = []
            for prep in self.term.main_preps:
                prep_info_as_dict = OrderedDict()
                prep_info_as_dict[ConstantKeys.PREP_ID] = prep.address
                prep_info_as_dict[ConstantKeys.PUBLIC_KEY] = prep.public_key
                prep_info_as_dict[ConstantKeys.P2P_END_POINT] = prep.p2p_end_point
                preps_as_list.append(prep_info_as_dict)
                preps_as_list_for_roothash.extend(
                    [prep.address.to_bytes(), prep.public_key, prep.p2p_end_point.encode()])
            prep_as_dict["preps"] = preps_as_list
            prep_as_dict["state"] = PrepResultState.NORMAL.value
            prep_as_dict["rootHash"] = hashlib.sha3_256(b'|'.join(preps_as_list_for_roothash)).digest()
        return prep_as_dict

    def save_term(self, context: 'IconScoreContext'):
        self.term.save(context,
                       context.block.height,
                       context.preps.get_preps(),
                       self.term.irep,
                       context.total_supply)

    def handle_get_prep(self, context: 'IconScoreContext', params: dict) -> dict:
        """Returns registration information of a P-Rep

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
        prep.set(ret_params, context.block.height)
        self._validate_limit_irep(context, prep, prev_irep)

        # Update a new P-Rep registration info to stateDB
        prep_storage.put_prep(context, prep)

        self._create_tx_result(context, 'PRepSet(Address)', address)

    @classmethod
    def _validate_limit_irep(cls, context: 'IconScoreContext', prep: 'PRep', prev_irep: int = None):
        prep_irep: int = prep.irep
        if prep_irep < IISS_MIN_IREP:
            raise InvalidParamsException(f"Invalid irep {prep_irep}")

        if prev_irep is None:
            return

        if prev_irep * 0.8 > prep_irep or prep_irep > prev_irep * 1.2:
            raise InvalidParamsException(f'Out of boundary: {prep_irep}, {prev_irep}')

        context.engine.issue.validate_limit_total_supply(context, prep_irep)

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
        self._apply_prep_delegated_offset_for_iiss_variable(context, -prep.delegated)

        # Update rcDB
        self._put_unreg_prep_for_iiss_db(context, address)

        self._create_tx_result(context, 'PRepUnregistered(Address)', address)

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
        preps: 'PRepContainer' = self.term.main_preps
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
        preps: 'PRepContainer' = self.term.sub_preps
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

        start_index: int = ret_params.get(ConstantKeys.START_RANKING, 1) - 1
        if start_index < 0:
            start_index = 0

        end_index: int = ret_params.get(ConstantKeys.END_RANKING, len(preps))

        for i in range(start_index, end_index):
            prep: 'PRep' = preps[i]

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
