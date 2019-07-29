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
from typing import TYPE_CHECKING, Any, Optional, List, Dict, Tuple

from iconcommons.logger import Logger

from .data.prep import PRep, PRepDictType
from .data.prep_container import PRepContainer
from .term import Term
from .validator import validate_prep_data, validate_irep
from ..base.ComponentBase import EngineBase
from ..base.address import Address, ZERO_SCORE_ADDRESS
from ..base.exception import InvalidParamsException, MethodNotFoundException
from ..base.type_converter import TypeConverter, ParamType
from ..base.type_converter_templates import ConstantKeys
from ..icon_constant import IISS_MAX_DELEGATIONS, REV_DECENTRALIZATION, IISS_MIN_IREP
from ..icon_constant import PRepGrade, PrepResultState, PRepStatus
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
            "setGovernanceVariables": self.handle_set_governance_variables,
            "unregisterPRep": self.handle_unregister_prep
        }

        self._query_handler: dict = {
            "getPRep": self.handle_get_prep,
            "getMainPReps": self.handle_get_main_prep_list,
            "getSubPReps": self.handle_get_sub_prep_list,
            "getPReps": self.handle_get_prep_list
        }

        self.preps = PRepContainer()
        self.term = Term()
        self._initial_irep: Optional[int] = None

        Logger.debug("PRepEngine.__init__() end")

    def open(self, context: 'IconScoreContext', term_period: int, irep: int):
        self._load_preps(context)
        self.term.load(context, term_period)
        self._initial_irep = irep

        context.engine.iiss.add_listener(self)

    def _load_preps(self, context: 'IconScoreContext'):
        """Load a prep from db

        :param prep:
        :return:
        """
        icx_storage: 'IcxStorage' = context.storage.icx

        for prep in context.storage.prep.get_prep_iterator():
            account: 'Account' = icx_storage.get_account(context, prep.address, Intent.ALL)

            prep.stake = account.stake
            prep.delegated = account.delegated_amount

            self.preps.add(prep)

        self.preps.freeze()

    def close(self):
        IconScoreContext.engine.iiss.remove_listener(self)

    def invoke(self, context: 'IconScoreContext', data: dict):
        method: str = data['method']
        params: dict = data.get('params', {})

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
        # Updated every block
        self.preps = precommit_data.preps

        # Updated every term
        if precommit_data.term is not None:
            self.term: 'Term' = precommit_data.term

    def rollback(self):
        pass

    def on_term_ended(self, context: 'IconScoreContext') -> Tuple[dict, 'Term']:
        """Called in IconServiceEngine.invoke() every time when a term is ended

        Update P-Rep grades according to PRep.delegated
        """
        self._update_prep_grades(main_prep_count=context.main_prep_count,
                                 main_and_sub_prep_count=context.main_and_sub_prep_count,
                                 old_preps=self.term.preps,
                                 new_preps=context.preps)
        main_preps_as_dict: dict = self.get_next_main_preps(context)
        next_term: 'Term' = self._create_next_term(context)
        next_term.save(context)

        return main_preps_as_dict, next_term

    @staticmethod
    def _update_prep_grades(main_prep_count: int, main_and_sub_prep_count: int,
                            old_preps: List['PRep'], new_preps: 'PRepContainer'):
        prep_grades: Dict['Address', Tuple['PRepGrade', 'PRepGrade']] = {}

        # Put the address and grade of a old P-Rep to prep_grades dict
        for prep in old_preps:
            # grades[0] is an old grade and grades[1] is a new grade
            prep_grades[prep.address] = (prep.grade, PRepGrade.CANDIDATE)

        # Remove the P-Reps which preserve the same grade in the next term from prep_grades dict
        for i in range(main_and_sub_prep_count):
            prep: 'PRep' = new_preps.get_by_index(i, mutable=False)
            if prep is None:
                Logger.warning(tag="PREP", msg=f"Not enough P-Reps: {new_preps.size(active_prep_only=True)}")
                break

            prep_address: 'Address' = prep.address
            grades: tuple = prep_grades.get(prep_address, (PRepGrade.CANDIDATE, PRepGrade.CANDIDATE))

            old_grade: 'PRepGrade' = grades[0]
            new_grade: 'PRepGrade' = PRepGrade.MAIN if i < main_prep_count else PRepGrade.SUB

            if old_grade == new_grade:
                del prep_grades[prep_address]
            else:
                prep_grades[prep_address] = (old_grade, new_grade)

        # Update the grades of P-Reps for the next term
        for address, grades in prep_grades.items():
            prep: 'PRep' = new_preps.get_by_address(address, mutable=True)
            assert prep is not None
            prep.grade = grades[1]

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
        if context.preps.contains(address, active_prep_only=False):
            raise InvalidParamsException(f"{address} has been already registered")

        # Check Prep registration fee
        value = context.msg.value
        if value != context.storage.prep.prep_registration_fee:
            raise InvalidParamsException(f"Invalid prep registration fee. "
                                         f"Registration Fee Must be {context.storage.prep.prep_registration_fee} "
                                         f"not {value}")

        ret_params: dict = TypeConverter.convert(params, ParamType.IISS_REG_PREP)
        validate_prep_data(address, ret_params)

        account: 'Account' = icx_storage.get_account(context, address, Intent.STAKE | Intent.DELEGATED)

        # Create a PRep object and assign delegated amount from account to prep
        # prep.irep is set to IISS_MIN_IREP by default
        prep = PRep.from_dict(address, ret_params, context.block.height, context.tx.index)
        prep.stake = account.stake
        prep.delegated = account.delegated_amount

        # Set an initial value to irep of a P-Rep on registerPRep
        if context.is_decentralized():
            prep.set_irep(self.term.irep, context.block.height)
        else:
            prep.set_irep(self._initial_irep, context.block.height)

        # Update preps in context
        context.preps.register(prep)

        # Update stateDB
        prep_storage.put_prep(context, prep)

        # Update rcDB
        self._put_reg_prep_in_rc_db(context, address)

        # Burn Prep registration fee
        context.engine.issue.burn(context, address, value)

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

    def get_next_main_preps(self, context: 'IconScoreContext') -> Optional[dict]:
        """Returns preps which will run as main preps during the next term in dict format

        :return:
        """
        prep_as_dict: Optional[dict] = \
            self.get_main_preps_in_dict(context.main_prep_count, context.preps.get_preps(0, context.main_prep_count))

        if prep_as_dict:
            prep_as_dict['irep'] = self.term.irep
            prep_as_dict['state'] = PrepResultState.NORMAL.value

        return prep_as_dict

    @staticmethod
    def get_main_preps_in_dict(main_prep_count: int, preps: List['PRep']) -> Optional[dict]:
        count: int = min(len(preps), main_prep_count)
        if count == 0:
            Logger.warning(tag="PREP", msg="No P-Rep candidates")
            return None

        prep_as_dict = {}
        preps_as_list = []
        prep_addresses_for_roothash = b''

        for i in range(count):
            prep: 'PRep' = preps[i]
            preps_as_list.append({
                ConstantKeys.PREP_ID: prep.address,
                ConstantKeys.PUBLIC_KEY: prep.public_key,
                ConstantKeys.P2P_ENDPOINT: prep.p2p_endpoint
            })
            prep_addresses_for_roothash += prep.address.to_bytes_including_prefix()

        prep_as_dict["preps"] = preps_as_list
        prep_as_dict["rootHash"]: bytes = hashlib.sha3_256(prep_addresses_for_roothash).digest()

        return prep_as_dict

    def _create_next_term(self, context: 'IconScoreContext') -> 'Term':
        # The current P-Rep term is over. Prepare the next P-Rep term
        irep: int = self._calculate_weighted_average_of_irep(context)

        next_term = Term()
        next_term.update(
            self.term.sequence + 1,
            context.main_prep_count,
            context.main_and_sub_prep_count,
            context.block.height,
            context.preps.get_preps(start_index=0, size=context.main_and_sub_prep_count),
            context.total_supply,
            self.term.period,
            irep
        )

        return next_term

    @staticmethod
    def _calculate_weighted_average_of_irep(context: 'IconScoreContext') -> int:
        preps: 'PRepContainer' = context.preps

        total_delegated = 0  # total delegated of top 22 preps
        total_weighted_irep = 0

        for i in range(context.main_prep_count):
            prep: 'PRep' = preps.get_by_index(i, mutable=False)
            total_weighted_irep += prep.irep * prep.delegated
            total_delegated += prep.delegated

        return total_weighted_irep // total_delegated if total_delegated > 0 else IISS_MIN_IREP

    def handle_get_prep(self, context: 'IconScoreContext', params: dict) -> dict:
        """Returns the details of a P-Rep including information on registration, delegation and statistics

        :param context:
        :param params:
        :return: the response for getPRep JSON-RPC request
        """
        ret_params: dict = TypeConverter.convert(params, ParamType.IISS_GET_PREP)
        address: 'Address' = ret_params[ConstantKeys.ADDRESS]

        prep: 'PRep' = self.preps.get_by_address(address)
        if prep is None:
            raise InvalidParamsException(f"P-Rep not found: {address}")

        account: 'Account' = context.storage.icx.get_account(context, address, Intent.STAKE)

        response: dict = prep.to_dict(PRepDictType.FULL)
        response["stake"] = account.stake
        return response

    @staticmethod
    def handle_set_prep(context: 'IconScoreContext', params: dict):
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

        validate_prep_data(context.tx.origin, kwargs, True)

        if ConstantKeys.P2P_ENDPOINT in kwargs:
            p2p_endpoint: str = kwargs[ConstantKeys.P2P_ENDPOINT]
            del kwargs[ConstantKeys.P2P_ENDPOINT]
            kwargs["p2p_endpoint"] = p2p_endpoint

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

    def handle_set_governance_variables(self, context: 'IconScoreContext', params: dict):
        """Handles setGovernanceVariables JSON-RPC API request

        :param context:
        :param params:
        :return:
        """
        # This API is available after IISS decentralization is enabled.
        if context.revision < REV_DECENTRALIZATION or self.term.sequence < 0:
            raise MethodNotFoundException("setGovernanceVariables is disabled")

        address: 'Address' = context.tx.origin

        prep: 'PRep' = context.preps.get_by_address(address, mutable=True)
        if prep is None:
            raise InvalidParamsException(f"P-Rep not found: {str(address)}")

        kwargs: dict = TypeConverter.convert(params, ParamType.IISS_SET_GOVERNANCE_VARIABLES)

        # Update incentive rep
        irep: int = kwargs["irep"]
        validate_irep(context, irep, prep)
        prep.set_irep(irep, context.block.height)

        # Update the changed properties of a P-Rep to stateDB
        context.storage.prep.put_prep(context, prep)

        # EventLog
        EventLogEmitter.emit_event_log(
            context,
            score_address=ZERO_SCORE_ADDRESS,
            event_signature="GovernanceVariablesSet(Address,int)",
            arguments=[address, irep],
            indexed_args_count=1
        )

    def handle_unregister_prep(self, context: 'IconScoreContext', _params: dict):
        """Unregister a P-Rep

        :param context:
        :param _params:
        :return:
        """
        address: 'Address' = context.tx.origin

        self.unregister_prep(context, address)

        # EventLog
        EventLogEmitter.emit_event_log(
            context,
            score_address=ZERO_SCORE_ADDRESS,
            event_signature="PRepUnregistered(Address)",
            arguments=[address],
            indexed_args_count=0
        )

    def unregister_prep(self, context: 'IconScoreContext', address: 'Address',
                        status: 'PRepStatus' = PRepStatus.UNREGISTERED):
        prep_storage: 'PRepStorage' = context.storage.prep

        # Remove a given P-Rep from context.preps
        context.preps.unregister(address, status)

        # Update stateDB
        prep_storage.delete_prep(context, address)

        # Update rcDB
        self._put_unreg_prep_for_iiss_db(context, address)

    @staticmethod
    def _put_unreg_prep_for_iiss_db(context: 'IconScoreContext', address: 'Address'):
        rc_tx_batch: list = context.rc_tx_batch
        block_height: int = context.block.height

        tx: 'PRepUnregisterTx' = RewardCalcDataCreator.create_tx_prep_unreg()
        iiss_tx_data: 'TxData' = RewardCalcDataCreator.create_tx(address, block_height, tx)
        context.storage.rc.put(rc_tx_batch, iiss_tx_data)

    def handle_get_main_prep_list(self, _context: 'IconScoreContext', _params: dict) -> dict:
        """Returns main P-Rep list in the current term

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
        """Returns sub P-Rep list in the present term

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

    def handle_get_prep_list(self, context: 'IconScoreContext', params: dict) -> dict:
        """Returns P-Reps ranging in ranking from start_ranking to end_ranking

        P-Rep means all P-Reps including main P-Reps and sub P-Reps

        :param context:
        :param params:
        :return:
        """
        ret_params: dict = TypeConverter.convert(params, ParamType.IISS_GET_PREP_LIST)

        preps: 'PRepContainer' = self.preps
        start_ranking: int = 0
        prep_list: list = []

        prep_count: int = preps.size(active_prep_only=True)

        if prep_count > 0:
            start_ranking: int = ret_params.get(ConstantKeys.START_RANKING, 1)
            end_ranking: int = min(ret_params.get(ConstantKeys.END_RANKING, prep_count), prep_count)

            if not 1 <= start_ranking <= end_ranking:
                raise InvalidParamsException(
                    f"Invalid ranking: startRanking({start_ranking}), endRanking({end_ranking})")

            for i in range(start_ranking - 1, end_ranking):
                prep: 'PRep' = preps.get_by_index(i)
                prep_list.append(prep.to_dict(PRepDictType.ABRIDGED))

        return {
            "blockHeight": context.block.height,
            "startRanking": start_ranking,
            "totalDelegated": preps.total_prep_delegated,
            "totalStake": context.storage.iiss.get_total_stake(context),
            "preps": prep_list
        }

    # IISSEngineListener implementation ---------------------------
    def on_set_stake(self, context: 'IconScoreContext', account: 'Account'):
        """Called on IISSEngine.handle_set_stake()

        :param context:
        :param account:
        :return:
        """
        prep: 'PRep' = context.preps.get_by_address(account.address, mutable=True)
        if prep:
            prep.stake = account.stake

    def on_set_delegation(
            self, context: 'IconScoreContext', updated_accounts: List['Account']):
        """Called on IISSEngine.handle_set_delegation()

        :param context:
        :param updated_accounts:
        return:
        """
        assert 0 <= len(updated_accounts) <= IISS_MAX_DELEGATIONS * 2

        for account in updated_accounts:
            assert isinstance(account, Account)
            address = account.address

            # If a delegated account is a P-Rep, then update its delegated amount
            if context.preps.contains(address, active_prep_only=True):
                context.preps.set_delegated_to_prep(address, account.delegated_amount)
