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

from typing import TYPE_CHECKING, Any, Optional

from iconcommons.logger import Logger
from .data.prep import PRep
from .data.prep_container import PRepContainer
from .term import Term
from ..base.ComponentBase import EngineBase
from ..base.address import Address
from ..base.type_converter import TypeConverter, ParamType
from ..base.type_converter_templates import ConstantKeys
from ..icon_constant import PREP_COUNT
from ..iconscore.icon_score_result import TransactionResult
from ..icx.storage import Intent
from ..iiss.reward_calc import RewardCalcDataCreator
from ..base.exception import InvalidParamsException

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
            # "getSubPRepList": self.handle_get_sub_prep_list,
            "getPRepList": self.handle_get_prep_list
        }

        self.preps: Optional['PRepContainer'] = None
        self.term = Term()

        Logger.debug("PRepEngine.__init__() end")

    def open(self, context: 'IconScoreContext', term_period: int, governance_variable: dict) -> None:
        self.preps = PRepContainer()
        self.preps.load(context)
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

    def commit(self, context: 'IconScoreContext', precommit_data: 'PrecommitData'):
        """If the current P-Rep term is over, update term with new information
        which has P-Rep list(address, delegated amount), start height, end height, incentive_rep

        :param context:
        :param precommit_data:
        :return:
        """
        self.preps = precommit_data.preps

    def rollback(self):
        pass

    def handle_register_prep(
            self, context: 'IconScoreContext', params: dict, tx_result: 'TransactionResult'):
        """Register a P-Rep

        Roles
        * Update preps in context
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
        if address in context.preps:
            raise InvalidParamsException(f"{str(address)} has been already registered")

        ret_params: dict = TypeConverter.convert(params, ParamType.IISS_REG_PREP)
        account: 'Account' = icx_storage.get_account(context, address, Intent.DELEGATED)

        # Create a PRep object and assign delegated amount from account to prep
        prep = PRep.from_dict(address, ret_params, context.block.height, context.tx.index)
        prep.delegated = account.delegated_amount

        # Update preps in context
        context.preps.add(prep)

        # Update stateDB
        prep_storage.put_prep(context, prep)
        self._apply_prep_delegated_offset_for_iiss_variable(context, prep.delegated)

        # Update rcDB
        self._put_reg_prep_for_rc_data(context, address)

    @staticmethod
    def _put_reg_prep_for_rc_data(context: 'IconScoreContext', address: 'Address'):
        rc_tx_batch: list = context.rc_tx_batch
        block_height: int = context.block.height

        tx: 'PRepRegisterTx' = RewardCalcDataCreator.create_tx_prep_reg()
        iiss_tx_data: 'TxData' = RewardCalcDataCreator.create_tx(address, block_height, tx)
        context.storage.rc.put(rc_tx_batch, iiss_tx_data)

    @staticmethod
    def _put_unreg_prep_for_iiss_db(context: 'IconScoreContext', address: 'Address'):
        rc_tx_batch: list = context.rc_tx_batch
        block_height: int = context.block.height

        tx: 'PRepUnregisterTx' = RewardCalcDataCreator.create_tx_prep_unreg()
        iiss_tx_data: 'TxData' = RewardCalcDataCreator.create_tx(address, block_height, tx)
        context.storage.rc.put(rc_tx_batch, iiss_tx_data)

    @staticmethod
    def _apply_prep_delegated_offset_for_iiss_variable(
            context: 'IconScoreContext', offset: int):
        total_delegated_amount: int = context.storage.iiss.get_total_prep_delegated(context)
        context.storage.iiss.put_total_prep_delegated(context, total_delegated_amount + offset)

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

    @staticmethod
    def handle_set_prep(
            context: 'IconScoreContext', params: dict, tx_result: 'TransactionResult'):
        """Update a P-Rep registration information

        :param context:
        :param params:
        :param tx_result:
        :return:
        """
        prep_storage = context.storage.prep
        address: 'Address' = context.tx.origin

        prep: 'PRep' = context.preps.get(address)
        if prep is None:
            raise InvalidParamsException(f"P-Rep not found: str{address}")

        ret_params: dict = TypeConverter.convert(params, ParamType.IISS_SET_PREP)
        prep.set(ret_params)

        # Update a new P-Rep registration info to stateDB
        prep_storage.put_prep(context, prep)

    def handle_unregister_prep(
            self, context: 'IconScoreContext', params: dict, tx_result: 'TransactionResult'):
        """Unregister a P-Rep

        :param context:
        :param params:
        :param tx_result:
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

    def handle_get_main_prep_list(self, context: 'IconScoreContext', params: dict) -> dict:
        """Returns 22 P-Rep list in the present term

        :param context:
        :param params:
        :return:
        """
        preps: 'PRepContainer' = self.preps
        total_delegated: int = 0
        prep_list = []

        for prep in preps:
            item = {
                "address": prep.address,
                "delegated": prep.delegated
            }
            prep_list.append(item)
            total_delegated += prep.delegated

            if len(prep_list) == PREP_COUNT:
                break

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
        prep_list = []

        start_index: int = ret_params.get(ConstantKeys.START_RANKING, 1) - 1
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
