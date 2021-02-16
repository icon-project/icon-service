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

from copy import deepcopy
from typing import TYPE_CHECKING, Any, Optional, List, Dict, Tuple

from iconcommons.logger import Logger

from .data import Term
from .data.prep import PRep, PRepDictType
from .data.prep_container import PRepContainer
from .penalty_imposer import PenaltyImposer
from .validator import validate_prep_data, validate_irep
from ..base.ComponentBase import EngineBase
from ..base.address import Address, SYSTEM_SCORE_ADDRESS
from ..base.exception import (
    AccessDeniedException, InvalidParamsException, MethodNotFoundException, ServiceNotReadyException,
    InvalidRequestException
)
from ..base.type_converter_templates import ConstantKeys
from ..icon_constant import PRepGrade, PRepResultState, PRepStatus, ROLLBACK_LOG_TAG
from ..icon_constant import Revision, IISS_MIN_IREP, PREP_PENALTY_SIGNATURE, \
    PenaltyReason, TermFlag, IconScoreContextType
from ..iconscore.icon_score_context import IconScoreContext
from ..iconscore.icon_score_event_log import EventLogEmitter
from ..iconscore.icon_score_step import StepType
from ..icx.icx_account import Account
from ..icx.storage import Intent
from ..iiss.listener import EngineListener as IISSEngineListener
from ..iiss.reward_calc import RewardCalcDataCreator
from ..prep.prep_address_converter import PRepAddressConverter

if TYPE_CHECKING:
    from ..iiss.reward_calc.msg_data import PRepRegisterTx, PRepUnregisterTx, TxData
    from ..icx import IcxStorage
    from ..precommit_data_manager import PrecommitData

_TAG = "PREP"


class Method:
    REGISTER = 'registerPRep'
    UNREGISTER = 'unregisterPRep'
    SET_PREP = 'setPRep'
    SET_GOVERNANCE_VARIABLES = 'setGovernanceVariables'
    GET_PREP = 'getPRep'
    GET_MAIN_PREPS = 'getMainPReps'
    GET_SUB_PREPS = 'getSubPReps'
    GET_PREPS = 'getPReps'
    GET_PREP_TERM = 'getPRepTerm'
    GET_INACTIVE_PREPS = 'getInactivePReps'


class Engine(EngineBase, IISSEngineListener):
    """PRepEngine class

    Roles:
    * Manages term and preps
    * Handles P-Rep related JSON-RPC API requests
    """

    INVOKE_METHOD_TABLE = [
        Method.REGISTER,
        Method.UNREGISTER,
        Method.SET_PREP,
        Method.SET_GOVERNANCE_VARIABLES,
    ]
    QUERY_METHOD_TABLE = [
        Method.GET_PREP,
        Method.GET_MAIN_PREPS,
        Method.GET_SUB_PREPS,
        Method.GET_PREPS,
        Method.GET_PREP_TERM,
        Method.GET_INACTIVE_PREPS,
    ]
    METHOD_TABLE = INVOKE_METHOD_TABLE + QUERY_METHOD_TABLE

    def __init__(self):
        super().__init__()
        Logger.debug(tag=_TAG, msg="PRepEngine.__init__() start")

        self._invoke_handlers: dict = {
            Method.REGISTER: self.handle_register_prep,
            Method.UNREGISTER: self.handle_unregister_prep,
            Method.SET_PREP: self.handle_set_prep,
            Method.SET_GOVERNANCE_VARIABLES: self.handle_set_governance_variables,
            Method.GET_PREP: self.handle_get_prep,
            Method.GET_MAIN_PREPS: self.handle_get_main_preps,
            Method.GET_SUB_PREPS: self.handle_get_sub_preps,
            Method.GET_PREPS: self.handle_get_preps,
            Method.GET_PREP_TERM: self.handle_get_prep_term,
            Method.GET_INACTIVE_PREPS: self.handle_get_inactive_preps
        }

        self._query_handler: dict = {
            Method.GET_PREP: self.handle_get_prep,
            Method.GET_MAIN_PREPS: self.handle_get_main_preps,
            Method.GET_SUB_PREPS: self.handle_get_sub_preps,
            Method.GET_PREPS: self.handle_get_preps,
            Method.GET_PREP_TERM: self.handle_get_prep_term,
            Method.GET_INACTIVE_PREPS: self.handle_get_inactive_preps
        }

        self.preps: 'PRepContainer' = PRepContainer()
        # self.term should be None before decentralization
        self.term: Optional['Term'] = None
        self._initial_irep: Optional[int] = None
        self._penalty_imposer: Optional['PenaltyImposer'] = None

        self.prep_address_converter: 'PRepAddressConverter' = None

        Logger.debug(tag=_TAG, msg="PRepEngine.__init__() end")

    def open(self,
             context: 'IconScoreContext',
             term_period: int,
             irep: int,
             penalty_grace_period: int,
             low_productivity_penalty_threshold: int,
             block_validation_penalty_threshold: int):

        # This logic doesn't need to save to DB yet
        self._init_penalty_imposer(penalty_grace_period,
                                   low_productivity_penalty_threshold,
                                   block_validation_penalty_threshold)

        self.prep_address_converter: 'PRepAddressConverter' = context.storage.meta.get_prep_address_converter(context)

        self.preps = self._load_preps(context)
        self.term = self._load_term(context)
        self._initial_irep = irep

        context.engine.iiss.add_listener(self)

    def _init_penalty_imposer(self,
                              penalty_grace_period: int,
                              low_productivity_penalty_threshold: int,
                              block_validation_penalty_threshold: int):
        """Initialize PenaltyImposer

        :param penalty_grace_period:
        :param low_productivity_penalty_threshold:
        :param block_validation_penalty_threshold:
        :return:
        """
        self._penalty_imposer = PenaltyImposer(penalty_grace_period,
                                               low_productivity_penalty_threshold,
                                               block_validation_penalty_threshold)

    def _load_preps(self, context: 'IconScoreContext') -> 'PRepContainer':
        """Load preps from state db

        :return: new prep container instance
        """
        icx_storage: 'IcxStorage' = context.storage.icx
        preps = PRepContainer()

        for prep in context.storage.prep.get_prep_iterator():

            if prep.status == PRepStatus.ACTIVE:
                self.prep_address_converter.add_node_address(node=prep.node_address, prep=prep.address)

            account: 'Account' = icx_storage.get_account(context, prep.address, Intent.ALL)

            prep.stake = account.stake
            prep.delegated = account.delegated_amount

            preps.add(prep)

        preps.freeze()
        return preps

    @classmethod
    def _load_term(cls, context: 'IconScoreContext') -> Optional['Term']:
        term = context.storage.prep.get_term(context)
        if term:
            term.freeze()

        return term

    def close(self):
        IconScoreContext.engine.iiss.remove_listener(self)

    @classmethod
    def check_method(cls, method: str) -> bool:
        return method in cls.METHOD_TABLE

    @classmethod
    def check_invoke_method(cls, method: str) -> bool:
        return method in cls.INVOKE_METHOD_TABLE

    @classmethod
    def check_query_method(cls, method: str) -> bool:
        return method in cls.QUERY_METHOD_TABLE

    def invoke(self, context: 'IconScoreContext', method: str, params: dict):
        if context.revision < Revision.IISS.value:
            context.step_counter.apply_step(StepType.CONTRACT_CALL, 1)
            raise InvalidParamsException(f"Method Not Found: {method}")
        handler: callable = self._invoke_handlers[method]
        handler(context, **params)

    def query(self, context: 'IconScoreContext', method: str, params: dict) -> Any:
        if context.revision < Revision.SYSTEM_SCORE_ENABLED.value and \
                context.type == IconScoreContextType.INVOKE:
            raise InvalidRequestException(f"Do not call readonly method '{method}' with 'icx_sendTransaction'")
        handler: callable = self._query_handler[method]
        ret = handler(context, **params)
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

        # Exchange a term instance for some reasons:
        # - penalty for elected P-Reps(main, sub)
        # - A new term is started
        if precommit_data.term is not None:
            self.term: 'Term' = precommit_data.term

        self.prep_address_converter: 'PRepAddressConverter' = precommit_data.prep_address_converter

    def rollback(self, context: 'IconScoreContext', _block_height: int, _block_hash: bytes):
        """After rollback is called, the state of prep_engine is reverted to that of a given block

        :param context:
        :param _block_height: the height of the block to go back
        :param _block_hash:
        :return:
        """
        Logger.info(tag=ROLLBACK_LOG_TAG, msg="rollback() start")

        self.prep_address_converter: 'PRepAddressConverter' = context.storage.meta.get_prep_address_converter(context)

        self.preps = self._load_preps(context)
        self.term = self._load_term(context)

        Logger.info(tag=ROLLBACK_LOG_TAG, msg=f"rollback() end: {self.term}")

    def on_block_invoked(
            self,
            context: 'IconScoreContext',
            is_decentralization_started: bool) -> Tuple[Optional[dict], Optional['Term']]:
        """Called on IconServiceEngine._after_transaction_process()

        1. Adjust the grade for invalid P-Reps
        2. Update elected P-Reps in this term

        :param context:
        :param is_decentralization_started:
            True: Decentralization will begin at the next block
        :return:
        """

        if is_decentralization_started or self._is_term_ended(context):
            # The current P-Rep term is over. Prepare the next P-Rep term
            next_preps, new_term = self._on_term_ended(context)
        elif context.is_decentralized():
            # In-term P-Rep replacement
            next_preps, new_term = self._on_term_updated(context)
        else:
            next_preps, new_term = None, None

        if new_term:
            self._update_prep_grades(context, context.preps, self.term, new_term)
            context.storage.prep.put_term(context, new_term)

        return next_preps, new_term

    def _is_term_ended(self, context: 'IconScoreContext') -> bool:
        if self.term is None:
            return False

        return context.block.height == self.term.end_block_height

    def _on_term_ended(self, context: 'IconScoreContext') -> Tuple[dict, 'Term']:
        """Called in IconServiceEngine.invoke() every time when a term is ended

        Update P-Rep grades according to PRep.delegated
        """
        self._put_last_term_info(context, self.term)

        if self.term:
            main_preps: List['Address'] = [prep.address for prep in self.term.main_preps]
        else:
            # first term
            new_preps: List['PRep'] = context.preps.get_preps(
                start_index=0,
                size=context.main_prep_count
            )
            main_preps: List['Address'] = [prep.address for prep in new_preps]

        context.storage.meta.put_last_main_preps(context, main_preps)

        # All block validation penalties are released
        self._reset_block_validation_penalty(context)

        # Create a term with context.preps whose grades are up-to-date
        new_term: 'Term' = self._create_next_term(context, self.term)
        next_preps: dict = self._get_updated_main_preps(
            context=context,
            term=new_term,
            state=PRepResultState.NORMAL
        )

        Logger.debug(tag=_TAG, msg=f"{new_term}")

        return next_preps, new_term

    @classmethod
    def _put_last_term_info(cls, context: 'IconScoreContext', term: 'Term'):

        _, last_calc_end = context.storage.meta.get_last_term_info(context)
        if last_calc_end > 0:
            start: int = term.start_block_height
            end: int = term.end_block_height
        else:
            # first
            start: int = -1
            end: int = context.block.height

        context.storage.meta.put_last_term_info(context, start, end)

    def _on_term_updated(self, context: 'IconScoreContext') -> Tuple[Optional[dict], Optional['Term']]:
        """Update term with invalid elected P-Rep list during this term
        (In-term P-Rep replacement)

        We have to consider 5 cases below:
        1. No invalid elected P-Rep
            - Nothing to do
        2. Only main P-Reps are invalidated
            - Send a new main P-Rep list to loopchain
            - Save the new term to DB
        3. Only sub P-Reps are invalidated
            - Save the new term to DB
        4. Both of them are invalidated
            - Send new main P-Rep list to loopchain
            - Save the new term to DB
        5. p2pEndpoint of a Main P-Rep is updated
            - Send new main P-Rep list to loopchain
            - No need to save the new term to DB

        :param context:
        :return:
        """

        main_preps: List['Address'] = [prep.address for prep in self.term.main_preps]
        context.storage.meta.put_last_main_preps(context, main_preps)

        new_term = context.term
        if not new_term.is_dirty():
            return None, None

        if bool(new_term.flags & (TermFlag.MAIN_PREPS |
                                  TermFlag.MAIN_PREP_P2P_ENDPOINT |
                                  TermFlag.MAIN_PREP_NODE_ADDRESS)):
            next_preps = self._get_updated_main_preps(
                context=context,
                term=new_term,
                state=PRepResultState.IN_TERM_UPDATED
            )
        else:
            next_preps = None

        return next_preps, new_term

    @classmethod
    def _update_prep_grades(cls,
                            context: 'IconScoreContext',
                            new_preps: 'PRepContainer',
                            old_term: Optional['Term'],
                            new_term: 'Term'):
        """Update the grades of P-Reps every time when a block is invoked

        Do NOT change any properties of P-Reps after this method is called in this block

        :param context:
        :return:
        """
        Logger.debug(tag=_TAG, msg="_update_prep_grades() start")

        # 0: old grade, 1: new grade
        _OLD, _NEW = 0, 1
        prep_grades: Dict['Address', Tuple['PRepGrade', 'PRepGrade']] = {}

        if old_term:
            for prep_snapshot in old_term.main_preps:
                prep_grades[prep_snapshot.address] = (PRepGrade.MAIN, PRepGrade.CANDIDATE)

            for prep_snapshot in old_term.sub_preps:
                prep_grades[prep_snapshot.address] = (PRepGrade.SUB, PRepGrade.CANDIDATE)

        # Remove the P-Reps which preserve the same grade in the next term from prep_grades dict
        main_prep_count: int = len(new_term.main_preps)
        for i, prep_snapshot in enumerate(new_term.preps):
            prep_address: 'Address' = prep_snapshot.address
            grades: tuple = prep_grades.get(prep_address, (PRepGrade.CANDIDATE, PRepGrade.CANDIDATE))

            old_grade: 'PRepGrade' = grades[_OLD]
            new_grade: 'PRepGrade' = PRepGrade.MAIN if i < main_prep_count else PRepGrade.SUB

            if old_grade == new_grade:
                del prep_grades[prep_address]
            else:
                prep_grades[prep_address] = (old_grade, new_grade)

        # Update the grades of P-Reps for the next term
        # CAUTION: DO NOT use context.put_dirty_prep() here
        for address, grades in prep_grades.items():
            prep: 'PRep' = new_preps.get_by_address(address)
            assert prep is not None

            if prep.grade == grades[_NEW]:
                continue

            prep = prep.copy()
            prep.grade = grades[_NEW]
            new_preps.replace(prep)
            context.storage.prep.put_prep(context, prep)

            Logger.info(tag=_TAG,
                        msg=f"P-Rep grade changed: {address} {grades[_OLD]} -> {grades[_NEW]}")

        Logger.debug(tag=_TAG, msg="_update_prep_grades() end")

    @classmethod
    def _reset_block_validation_penalty(cls, context: 'IconScoreContext'):
        """Reset block validation penalty in the end of every term

        :param context:
        :return:
        """

        for prep in context.preps:
            if prep.penalty == PenaltyReason.BLOCK_VALIDATION and prep.status == PRepStatus.ACTIVE:
                dirty_prep = context.get_prep(prep.address, mutable=True)
                dirty_prep.reset_block_validation_penalty()
                context.put_dirty_prep(dirty_prep)

        context.update_dirty_prep_batch()

    def handle_register_prep(self, context: 'IconScoreContext', **kwargs):
        """Register a P-Rep

        Roles
        * Update preps in context
        * Update stateDB
        * Update rcDB
        """
        if context.msg.sender.is_contract:
            raise AccessDeniedException(f"SCORE is not allowed.")

        icx_storage: 'IcxStorage' = context.storage.icx

        address: 'Address' = context.tx.origin
        if context.preps.contains(address, active_prep_only=False):
            raise InvalidParamsException(f"P-Rep already exists: {address}")

        # Check Prep registration fee
        value = context.msg.value
        if value != context.storage.prep.prep_registration_fee:
            raise InvalidParamsException(f"Invalid prep registration fee. "
                                         f"Registration Fee Must be {context.storage.prep.prep_registration_fee} "
                                         f"not {value}")

        if context.revision < Revision.DIVIDE_NODE_ADDRESS.value:
            self._remove_node_address_from_params(params=kwargs)

        validate_prep_data(context=context,
                           prep_address=address,
                           tx_data=kwargs)

        account: 'Account' = icx_storage.get_account(context, address, Intent.STAKE | Intent.DELEGATED)

        # Create a PRep object and assign delegated amount from account to prep
        # prep.irep is set to IISS_MIN_IREP by default
        dirty_prep = PRep.from_dict(address, kwargs, context.block.height, context.tx.index)
        dirty_prep.stake = account.stake
        dirty_prep.delegated = account.delegated_amount

        # Set an initial value to irep of a P-Rep on registerPRep
        if context.is_decentralized():
            dirty_prep.set_irep(self.term.irep, context.block.height)
        else:
            dirty_prep.set_irep(self._initial_irep, context.block.height)

        # Update preps in context
        context.put_dirty_prep(dirty_prep)

        # Update rcDB
        self._put_reg_prep_in_rc_db(context, address)

        # Burn Prep registration fee
        context.engine.issue.burn(context, address, value)

        # EventLog
        EventLogEmitter.emit_event_log(
            context,
            score_address=SYSTEM_SCORE_ADDRESS,
            event_signature="PRepRegistered(Address)",
            arguments=[address],
            indexed_args_count=0
        )

    @classmethod
    def _remove_node_address_from_params(cls, params: dict):
        """Just for backward compatibility with the previous version

        :param params: parameters of registerPRep or setPRep
        """
        if ConstantKeys.NODE_ADDRESS in params:
            del params[ConstantKeys.NODE_ADDRESS]

    @classmethod
    def _put_reg_prep_in_rc_db(cls, context: 'IconScoreContext', address: 'Address'):
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

    @classmethod
    def _get_updated_main_preps(cls,
                                context: 'IconScoreContext',
                                term: 'Term',
                                state: 'PRepResultState') -> Optional[dict]:
        """Returns preps which will run as main preps during the next term in dict format

        :return:
        """
        updated_main_preps: Optional[dict] = \
            cls.get_main_preps_in_dict(context, term)

        if updated_main_preps:
            updated_main_preps['irep'] = term.irep
            updated_main_preps['state'] = state.value

        return updated_main_preps

    @classmethod
    def get_main_preps_in_dict(cls,
                               context: 'IconScoreContext',
                               term: 'Term') -> Optional[dict]:
        if len(term.main_preps) == 0:
            Logger.warning(tag="PREP", msg="No P-Rep candidates")
            return None

        prep_as_dict: dict = {}
        preps_as_list: list = []

        for prep_snapshot in term.main_preps:
            prep: 'PRep' = context.get_prep(prep_snapshot.address)
            preps_as_list.append({
                ConstantKeys.PREP_ID: prep.node_address,
                ConstantKeys.P2P_ENDPOINT: prep.p2p_endpoint
            })

        prep_as_dict["preps"] = preps_as_list
        prep_as_dict["rootHash"]: bytes = term.root_hash

        return prep_as_dict

    @classmethod
    def _create_next_term(cls,
                          context: 'IconScoreContext',
                          prev_term: Optional['Term']) -> 'Term':
        """Create the next term instance at the end of the current term

        :param prev_term:
        :param context:
        :return:
        """
        new_preps: List['PRep'] = context.preps.get_preps(
            start_index=0, size=context.main_and_sub_prep_count)

        sequence = 0 if prev_term is None else prev_term.sequence + 1
        start_block_height = context.block.height + 1
        if prev_term:
            assert start_block_height == prev_term.end_block_height + 1

        # The current P-Rep term is over. Prepare the next P-Rep term
        if context.revision < Revision.SET_IREP_VIA_NETWORK_PROPOSAL.value:
            irep: int = cls._calculate_weighted_average_of_irep(new_preps[:context.main_prep_count])
        else:
            irep: int = context.inv_container.irep

        term = Term(
            sequence,
            start_block_height,
            context.term_period,
            irep,
            context.total_supply,
            context.preps.total_delegated
        )

        term.set_preps(new_preps, context.main_prep_count, context.main_and_sub_prep_count)

        return term

    @classmethod
    def _calculate_weighted_average_of_irep(cls, new_main_preps: List['PRep']) -> int:
        total_delegated = 0  # total delegated of top 22 preps
        total_weighted_irep = 0

        for prep in new_main_preps:
            total_weighted_irep += prep.irep * prep.delegated
            total_delegated += prep.delegated

        return total_weighted_irep // total_delegated if total_delegated > 0 else IISS_MIN_IREP

    def handle_get_prep(self, context: 'IconScoreContext', address: 'Address') -> dict:
        """Returns the details of a P-Rep including information on registration, delegation and statistics

        :return: the response for getPRep JSON-RPC request
        """
        prep: 'PRep' = self.preps.get_by_address(address)
        if prep is None:
            raise InvalidParamsException(f"P-Rep not found: {address}")

        response: dict = prep.to_dict(PRepDictType.FULL)
        return response

    @classmethod
    def handle_set_prep(cls, context: 'IconScoreContext', **kwargs):
        """Update a P-Rep registration information

        :param context:
        :param kwargs:
        :return:
        """
        if context.msg.sender.is_contract:
            raise AccessDeniedException(f"SCORE is not allowed.")

        address: 'Address' = context.tx.origin

        dirty_prep: Optional['PRep'] = context.get_prep(address, mutable=True)
        if dirty_prep is None:
            raise InvalidParamsException(f"P-Rep not found: {address}")

        params: dict = deepcopy(kwargs)

        if context.revision < Revision.DIVIDE_NODE_ADDRESS.value:
            cls._remove_node_address_from_params(params=params)

        validate_prep_data(context=context,
                           prep_address=address,
                           tx_data=params,
                           set_prep=True)

        if ConstantKeys.P2P_ENDPOINT in params:
            p2p_endpoint: str = params[ConstantKeys.P2P_ENDPOINT]
            del params[ConstantKeys.P2P_ENDPOINT]
            params["p2p_endpoint"] = p2p_endpoint

        if ConstantKeys.NODE_ADDRESS in params:
            node_address: 'Address' = params[ConstantKeys.NODE_ADDRESS]
            del params[ConstantKeys.NODE_ADDRESS]
            params["node_address"] = node_address

        # EventLog
        EventLogEmitter.emit_event_log(
            context,
            score_address=SYSTEM_SCORE_ADDRESS,
            event_signature="PRepSet(Address)",
            arguments=[address],
            indexed_args_count=0
        )

        cls._validate_node_key_back_compatibillity_below_rev_9(context, kwargs)
        # Update registration info
        dirty_prep.set(**params)

        context.put_dirty_prep(dirty_prep)

    @classmethod
    def _validate_node_key_back_compatibillity_below_rev_9(cls, context: 'IconScoreContext', data: dict):
        if context.revision < Revision.DIVIDE_NODE_ADDRESS.value:
            if ConstantKeys.NODE_ADDRESS in data and \
                    data[ConstantKeys.NODE_ADDRESS] is not None:
                # For Backward compatibility
                raise TypeError("nodeAddress not Allowed")


    def handle_set_governance_variables(self, context: 'IconScoreContext', irep: int):
        """Handles setGovernanceVariables JSON-RPC API request
        """
        if context.msg.sender.is_contract:
            raise AccessDeniedException(f"SCORE is not allowed.")

        # This API is available after IISS decentralization is enabled.
        if context.revision < Revision.DECENTRALIZATION.value or self.term.sequence < 0:
            raise MethodNotFoundException("setGovernanceVariables is disabled")

        # This API is disabled after SET_IREP_VIA_NETWORK_PROPOSAL
        if context.revision >= Revision.SET_IREP_VIA_NETWORK_PROPOSAL.value:
            raise MethodNotFoundException("setGovernanceVariables is disabled")

        address: 'Address' = context.tx.origin

        dirty_prep: Optional['PRep'] = context.get_prep(address, mutable=True)
        if dirty_prep is None:
            raise InvalidParamsException(f"P-Rep not found: {address}")

        # Update incentive rep
        validate_irep(context, irep, dirty_prep)

        # EventLog
        EventLogEmitter.emit_event_log(
            context,
            score_address=SYSTEM_SCORE_ADDRESS,
            event_signature="GovernanceVariablesSet(Address,int)",
            arguments=[address, irep],
            indexed_args_count=1
        )

        # Update the changed properties of a P-Rep to stateDB
        # context.storage.prep.put_dirty_prep(context, prep)
        dirty_prep.set_irep(irep, context.block.height)
        context.put_dirty_prep(dirty_prep)

    def handle_unregister_prep(self, context: 'IconScoreContext'):
        """Unregister a P-Rep

        :param context:
        :return:
        """
        if context.msg.sender.is_contract:
            raise AccessDeniedException(f"SCORE is not allowed.")

        address: 'Address' = context.tx.origin

        dirty_prep: Optional['PRep'] = context.get_prep(address, mutable=True)
        if dirty_prep is None:
            raise InvalidParamsException(f"P-Rep not found: {address}")

        if dirty_prep.status != PRepStatus.ACTIVE:
            raise InvalidParamsException(f"Inactive P-Rep: {address}")

        dirty_prep.status = PRepStatus.UNREGISTERED
        dirty_prep.grade = PRepGrade.CANDIDATE
        context.put_dirty_prep(dirty_prep)

        # Update rcDB
        self._put_unreg_prep_for_iiss_db(context, address)

        # EventLog
        EventLogEmitter.emit_event_log(
            context,
            score_address=SYSTEM_SCORE_ADDRESS,
            event_signature="PRepUnregistered(Address)",
            arguments=[address],
            indexed_args_count=0
        )

    def impose_penalty(self, context: 'IconScoreContext'):
        """Impose penalties on main P-Reps every block
        Called on IconServiceEngine._process_base_transaction()

        :param context:
        """
        for snapshot in self.term.main_preps:
            # Get a up-to-date main prep from context
            prep: 'PRep' = context.get_prep(snapshot.address)
            assert isinstance(prep, PRep)

            self._penalty_imposer.run(context, prep, self._on_penalty_imposed)

    @classmethod
    def _on_penalty_imposed(cls,
                            context: 'IconScoreContext',
                            address: 'Address',
                            reason: 'PenaltyReason'):
        """Called on PenaltyImposer.run()

        Penalty: low productivity, block validation, disqualification

        :param context:
        :param address: The address of a Main P-PRep on this term
        :param reason: penalty reason
        :return:
        """
        dirty_prep: Optional['PRep'] = context.get_prep(address, mutable=True)
        assert isinstance(dirty_prep, PRep)
        assert dirty_prep.status == PRepStatus.ACTIVE

        if reason == PenaltyReason.BLOCK_VALIDATION:
            status: 'PRepStatus' = PRepStatus.ACTIVE
        else:
            status: 'PRepStatus' = PRepStatus.DISQUALIFIED
            # Update rcDB not to supply a reward for the inactive P-Rep
            cls._put_unreg_prep_for_iiss_db(context, address)

        dirty_prep.status = status
        dirty_prep.penalty = reason
        dirty_prep.grade = PRepGrade.CANDIDATE
        context.put_dirty_prep(dirty_prep)

        EventLogEmitter.emit_event_log(
            context,
            score_address=SYSTEM_SCORE_ADDRESS,
            event_signature=PREP_PENALTY_SIGNATURE,
            arguments=[
                dirty_prep.address,
                dirty_prep.status.value,
                dirty_prep.penalty.value],
            indexed_args_count=1)

    @classmethod
    def impose_prep_disqualified_penalty(
            cls, context: 'IconScoreContext', address: 'Address'):
        """Called on disqualification network proposal

        :param context:
        :param address:
        :return:
        """
        prep: 'PRep' = context.get_prep(address)
        if prep is None:
            raise InvalidParamsException(f"P-Rep not found: {address}")

        if prep.status != PRepStatus.ACTIVE:
            raise InvalidParamsException(f"Inactive P-Rep: {address}")

        cls._on_penalty_imposed(context, address, PenaltyReason.PREP_DISQUALIFICATION)

    @classmethod
    def _put_unreg_prep_for_iiss_db(cls, context: 'IconScoreContext', address: 'Address'):
        rc_tx_batch: list = context.rc_tx_batch
        block_height: int = context.block.height

        tx: 'PRepUnregisterTx' = RewardCalcDataCreator.create_tx_prep_unreg()
        iiss_tx_data: 'TxData' = RewardCalcDataCreator.create_tx(address, block_height, tx)
        context.storage.rc.put(rc_tx_batch, iiss_tx_data)

    def handle_get_main_preps(self, _context: 'IconScoreContext') -> dict:
        """Returns main P-Rep list in the current term
        """
        total_delegated = 0 if self.term is None else self.term.total_delegated
        prep_list: list = []

        if self.term:
            for snapshot in self.term.main_preps:
                item = {
                    "address": snapshot.address,
                    "delegated": snapshot.delegated
                }
                prep_list.append(item)

        return {
            "totalDelegated": total_delegated,
            "preps": prep_list
        }

    def handle_get_sub_preps(self, _context: 'IconScoreContext') -> dict:
        """Returns sub P-Rep list in the present term
        """
        total_delegated: int = 0 if self.term is None else self.term.total_delegated
        prep_list: list = []

        if self.term:
            for prep in self.term.sub_preps:
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

    def handle_get_preps(self,
                         context: "IconScoreContext",
                         startRanking: Optional[int],
                         endRanking: Optional[int]) -> dict:
        """
        Returns P-Reps ranging in ranking from startRanking to endRanking

        P-Rep means all P-Reps including main P-Reps and sub P-Reps
        """
        preps: 'PRepContainer' = self.preps
        prep_count: int = preps.size(active_prep_only=True)
        prep_list: list = []

        start_ranking = 1 if startRanking is None else startRanking

        if endRanking is None:
            end_ranking = max(start_ranking, prep_count)
        else:
            end_ranking = endRanking

        if not self._verify_rankings(start_ranking, end_ranking):
            raise InvalidParamsException(
                f"Invalid ranking: startRanking({start_ranking}), "
                f"endRanking({end_ranking})"
            )

        for i in range(start_ranking - 1, end_ranking):
            if i >= prep_count:
                break

            prep: 'PRep' = preps.get_by_index(i)
            prep_list.append(prep.to_dict(PRepDictType.FULL))

        return {
            "blockHeight": context.block.height,
            "startRanking": start_ranking,
            "totalDelegated": preps.total_delegated,
            "totalStake": context.storage.iiss.get_total_stake(context),
            "preps": prep_list
        }

    @classmethod
    def _verify_rankings(cls, start_ranking: int, end_ranking: int) -> bool:
        if not (isinstance(start_ranking, int) and isinstance(end_ranking, int)):
            return False

        return 0 < start_ranking <= end_ranking

    def handle_get_prep_term(self, context: 'IconScoreContext') -> dict:
        """Provides the information on the current term
        """
        if self.term is None:
            raise ServiceNotReadyException("Term is not ready")

        preps_data = []

        # Collect Main and Sub P-Reps
        for prep_snapshot in self.term.preps:
            prep = self.preps.get_by_address(prep_snapshot.address)
            preps_data.append(prep.to_dict(PRepDictType.FULL))

        # Collect P-Reps which got penalized for consecutive 660 block validation failure
        def _func(node: 'PRep') -> bool:
            return node.penalty == PenaltyReason.BLOCK_VALIDATION and node.status == PRepStatus.ACTIVE

        # Sort preps in descending order by delegated
        preps_on_block_validation_penalty = \
            sorted(filter(_func, self.preps), key=lambda x: x.order())

        for prep in preps_on_block_validation_penalty:
            preps_data.append(prep.to_dict(PRepDictType.FULL))

        return {
            "blockHeight": context.block.height,
            "sequence": self.term.sequence,
            "startBlockHeight": self.term.start_block_height,
            "endBlockHeight": self.term.end_block_height,
            "totalSupply": self.term.total_supply,
            "totalDelegated": self.term.total_delegated,
            "irep": self.term.irep,
            "preps": preps_data
        }

    def handle_get_inactive_preps(self, context: 'IconScoreContext') -> dict:
        """Returns inactive P-Reps which is unregistered or receiving prep disqualification or low productivity penalty.
        """
        sorted_inactive_preps: List['PRep'] = \
            sorted(self.preps.get_inactive_preps(), key=lambda node: node.order())

        total_delegated = 0
        inactive_preps_data = []
        for prep in sorted_inactive_preps:
            inactive_preps_data.append(prep.to_dict(PRepDictType.FULL))
            total_delegated += prep.delegated

        return {
            "blockHeight": context.block.height,
            "totalDelegated": total_delegated,
            "preps": inactive_preps_data
        }

    # IISSEngineListener implementation ---------------------------
    def on_set_stake(self, context: 'IconScoreContext', account: 'Account'):
        """Called on IISSEngine.handle_set_stake()

        :param context:
        :param account:
        :return:
        """
        dirty_prep: 'PRep' = context.get_prep(account.address, mutable=True)
        if dirty_prep:
            dirty_prep.stake = account.stake
            context.put_dirty_prep(dirty_prep)

    def on_set_delegation(
            self, context: 'IconScoreContext', updated_accounts: List['Account']):
        """Called on IISSEngine.handle_set_delegation()

        :param context:
        :param updated_accounts:
        return:
        """
        if context.revision <= Revision.DECENTRALIZATION.value:
            # Although the following statement has a bug,
            # preserve it for state compatibility
            # max delegations (i.e. 10) * 2 + 1 is correct
            assert 0 <= len(updated_accounts) <= context.engine.iiss.get_max_delegations_by_revision(context) * 2

        for account in updated_accounts:
            assert isinstance(account, Account)
            address = account.address

            # If a delegated account is a P-Rep, then update its delegated amount
            dirty_prep: Optional['PRep'] = context.get_prep(address, mutable=True)
            if dirty_prep:
                dirty_prep.delegated = account.delegated_amount
                context.put_dirty_prep(dirty_prep)
