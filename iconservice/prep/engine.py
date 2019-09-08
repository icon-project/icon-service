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

from typing import TYPE_CHECKING, Any, Optional, List, Dict, Tuple, Iterable

from iconcommons.logger import Logger

from .data import Term, PRepSnapshot
from .data.prep import PRep, PRepDictType
from .data.prep_container import PRepContainer
from .penalty_imposer import PenaltyImposer
from .validator import validate_prep_data, validate_irep
from ..base.ComponentBase import EngineBase
from ..base.address import Address, ZERO_SCORE_ADDRESS
from ..base.exception import InvalidParamsException, MethodNotFoundException
from ..base.type_converter import TypeConverter, ParamType
from ..base.type_converter_templates import ConstantKeys
from ..icon_constant import IISS_MAX_DELEGATIONS, REV_DECENTRALIZATION, IISS_MIN_IREP, PREP_PENALTY_SIGNATURE, \
    PenaltyReason
from ..icon_constant import PRepGrade, PRepResultState, PRepStatus
from ..iconscore.icon_score_context import IconScoreContext
from ..iconscore.icon_score_event_log import EventLogEmitter
from ..icx.icx_account import Account
from ..icx.storage import Intent
from ..iiss import IISSEngineListener
from ..iiss.reward_calc import RewardCalcDataCreator

if TYPE_CHECKING:
    from ..iiss.reward_calc.msg_data import PRepRegisterTx, PRepUnregisterTx, TxData
    from ..icx import IcxStorage
    from ..precommit_data_manager import PrecommitData


class Engine(EngineBase, IISSEngineListener):
    """PRepEngine class

    Roles:
    * Manages term and preps
    * Handles P-Rep related JSON-RPC API requests
    """
    TAG = "PREP"

    def __init__(self):
        super().__init__()
        Logger.debug(tag=self.TAG, msg="PRepEngine.__init__() start")

        self._invoke_handlers: dict = {
            "registerPRep": self.handle_register_prep,
            "setPRep": self.handle_set_prep,
            "setGovernanceVariables": self.handle_set_governance_variables,
            "unregisterPRep": self.handle_unregister_prep
        }

        self._query_handler: dict = {
            "getPRep": self.handle_get_prep,
            "getMainPReps": self.handle_get_main_preps,
            "getSubPReps": self.handle_get_sub_preps,
            "getPReps": self.handle_get_preps,
            "getP2PEndpoints": self.handle_get_p2p_endpoints
        }

        self.preps = PRepContainer()
        # self.term should be None before decentralization
        self.term: Optional['Term'] = None
        self._initial_irep: Optional[int] = None
        self._penalty_imposer: Optional['PenaltyImposer'] = None

        Logger.debug(tag=self.TAG, msg="PRepEngine.__init__() end")

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

        self._load_preps(context)
        self.term: Optional['Term'] = context.storage.prep.get_term()
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

    def _load_preps(self, context: 'IconScoreContext'):
        """Load a prep from db

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

        # Exchange a term instance for some reasons:
        # - penalty for elected P-Reps(main, sub)
        # - A new term is started
        if precommit_data.term is not None:
            self.term: 'Term' = precommit_data.term

    def rollback(self):
        pass

    def on_block_invoked(self, context: 'IconScoreContext'):
        """Called on IconServiceEngine.invoke()

        1. Adjust the grade for invalid P-Reps
        2. Update elected P-Reps in this term

        :param context:
        :return:
        """
        self._handle_invalid_elected_preps(context)

    def _handle_invalid_elected_preps(self, context: 'IconScoreContext'):
        """Handles invalid P-Reps
        Exchange invalid main P-Reps with sub P-Reps

        :param context:
        """
        if len(context.invalid_elected_preps) == 0:
            return

        assert self.term is not None
        self.term.update(context.invalid_elected_preps.keys())

    def on_term_ended(self, context: 'IconScoreContext') -> Tuple[dict, 'Term']:
        """Called in IconServiceEngine.invoke() every time when a term is ended

        Update P-Rep grades according to PRep.delegated
        """

        self._put_last_term_info(context, self.term)

        # All block validation penalties are released
        self._release_block_validation_penalty(context)

        # Update the grades of the elected preps on the current and next term
        self._update_prep_grades_on_term_ended(context)

        # Create a term with context.preps whose grades are up-to-date
        next_term: 'Term' = self._create_next_term(self.term, context)
        main_preps_as_dict: dict = \
            self._get_updated_main_preps(context, next_term, PRepResultState.NORMAL)

        context.storage.prep.put_term(context, next_term)

        return main_preps_as_dict, next_term

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

    def on_term_updated(self, context: 'IconScoreContext') -> Tuple[dict, Optional['Term']]:
        """Update term with invalid elected P-Rep list during this term

        We have to consider 4 cases below:
        1. No invalid elected P-Rep
            - Nothing to do
        2. Only main P-Reps are invalidated
            - Send new main P-Rep list to loopchain
            - Save the new term to DB
        3. Only sub P-Reps are invalidated
            - Save the new term to DB
        4. Both of them are invalidated
            - Send new main P-Rep list to loopchain
            - Save the new term to DB

        :param context:
        :return:
        """
        # No invalid elected P-Reps in this block
        if len(context.invalid_elected_preps) == 0:
            return {}, None

        new_term = self.term.copy()
        new_term.update(context.invalid_elected_preps)
        assert new_term.is_dirty()
        new_term.freeze()

        if self.term.root_hash != new_term.root_hash:
            # Case 2 or 4: Some main P-Reps are invalidated
            main_preps_as_dict: dict = self._get_updated_main_preps(
                context, new_term, PRepResultState.IN_TERM_UPDATED)
        else:
            # Case 3: Only sub P-Reps are invalidated
            main_preps_as_dict = {}

        context.storage.prep.put_term(context, new_term)
        return main_preps_as_dict, new_term

    def _update_prep_grades_on_term_ended(self, context: 'IconScoreContext'):
        """Update the grades of the existing elected P-Reps every time when the next term begins

        Assume that block validation penalty has been already reset in preceding processes

        :param context:
        :return:
        """
        # Constants
        _OLD, _NEW = 0, 1

        main_prep_count: int = context.main_prep_count
        main_and_sub_prep_count: int = context.main_and_sub_prep_count
        old_preps: Iterable['PRepSnapshot'] = self.term.preps
        new_preps: 'PRepContainer' = context.preps

        # 0: old grade, 1: new grade
        prep_grades: Dict['Address', Tuple['PRepGrade', 'PRepGrade']] = {}

        # Put the address and grade of a old P-Rep to prep_grades dict
        for prep in old_preps:
            # grades[0] is an old grade and grades[1] is a new grade
            prep_grades[prep.address] = (prep.grade, PRepGrade.CANDIDATE)

        # Remove the P-Reps which preserve the same grade in the next term from prep_grades dict
        for i in range(main_and_sub_prep_count):
            prep: 'PRep' = new_preps.get_by_index(i)
            if prep is None:
                Logger.warning(tag=self.TAG, msg=f"Not enough P-Reps: {new_preps.size(active_prep_only=True)}")
                break

            prep_address: 'Address' = prep.address
            grades: tuple = prep_grades.get(prep_address, (PRepGrade.CANDIDATE, PRepGrade.CANDIDATE))

            old_grade: 'PRepGrade' = grades[_OLD]
            new_grade: 'PRepGrade' = PRepGrade.MAIN if i < main_prep_count else PRepGrade.SUB

            if old_grade == new_grade:
                del prep_grades[prep_address]
            else:
                prep_grades[prep_address] = (old_grade, new_grade)

        # Update the grades of P-Reps for the next term
        for address, grades in prep_grades.items():
            dirty_prep: 'PRep' = context.get_prep(address, mutable=True)
            assert dirty_prep is not None

            dirty_prep.grade = grades[_NEW]
            context.put_dirty_prep(dirty_prep)

        context.update_dirty_prep_batch()

    def _release_block_validation_penalty(self, context: 'IconScoreContext'):
        old_preps = self.preps

        for prep in old_preps:
            if prep.penalty == PenaltyReason.BLOCK_VALIDATION:
                dirty_prep = context.get_prep(prep.address, mutable=True)
                dirty_prep.reset_block_validation_penalty()
                context.put_dirty_prep(dirty_prep)

        context.update_dirty_prep_batch()

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

        address: 'Address' = context.tx.origin
        if context.preps.contains(address, active_prep_only=False):
            raise InvalidParamsException(f"P-Rep already exists: {address}")

        # Check Prep registration fee
        value = context.msg.value
        if value != context.storage.prep.prep_registration_fee:
            raise InvalidParamsException(f"Invalid prep registration fee. "
                                         f"Registration Fee Must be {context.storage.prep.prep_registration_fee} "
                                         f"not {value}")

        ret_params: dict = TypeConverter.convert(params, ParamType.IISS_REG_PREP)
        validate_prep_data(ret_params)

        account: 'Account' = icx_storage.get_account(context, address, Intent.STAKE | Intent.DELEGATED)

        # Create a PRep object and assign delegated amount from account to prep
        # prep.irep is set to IISS_MIN_IREP by default
        dirty_prep = PRep.from_dict(address, ret_params, context.block.height, context.tx.index)
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
            score_address=ZERO_SCORE_ADDRESS,
            event_signature="PRepRegistered(Address)",
            arguments=[address],
            indexed_args_count=0
        )

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
        prep_as_dict: Optional[dict] = \
            cls._get_main_preps_in_dict(context, term)

        if prep_as_dict:
            prep_as_dict['irep'] = term.irep
            prep_as_dict['state'] = state.value

        return prep_as_dict

    @classmethod
    def _get_main_preps_in_dict(cls,
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
                ConstantKeys.PREP_ID: prep.address,
                ConstantKeys.P2P_ENDPOINT: prep.p2p_endpoint
            })

        prep_as_dict["preps"] = preps_as_list
        prep_as_dict["rootHash"]: bytes = term.root_hash

        return prep_as_dict

    @classmethod
    def _create_next_term(cls,
                          prev_term: Optional['Term'],
                          context: 'IconScoreContext') -> 'Term':
        new_preps: List['PRep'] = context.preps.get_preps(
            start_index=0, size=context.main_and_sub_prep_count)

        sequence = 0 if prev_term is None else prev_term.sequence + 1
        start_block_height = context.block.height + 1
        if prev_term:
            assert start_block_height == prev_term.end_block_height + 1

        # The current P-Rep term is over. Prepare the next P-Rep term
        irep: int = cls._calculate_weighted_average_of_irep(new_preps[:context.main_prep_count])

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

    def handle_get_prep(self, _context: 'IconScoreContext', params: dict) -> dict:
        """Returns the details of a P-Rep including information on registration, delegation and statistics

        :param _context:
        :param params:
        :return: the response for getPRep JSON-RPC request
        """
        ret_params: dict = TypeConverter.convert(params, ParamType.IISS_GET_PREP)
        address: 'Address' = ret_params[ConstantKeys.ADDRESS]

        prep: 'PRep' = self.preps.get_by_address(address)
        if prep is None:
            raise InvalidParamsException(f"P-Rep not found: {address}")

        response: dict = prep.to_dict(PRepDictType.FULL)
        return response

    @classmethod
    def handle_set_prep(cls, context: 'IconScoreContext', params: dict):
        """Update a P-Rep registration information

        :param context:
        :param params:
        :return:
        """
        address: 'Address' = context.tx.origin

        dirty_prep: Optional['PRep'] = context.get_prep(address, mutable=True)
        if dirty_prep is None:
            raise InvalidParamsException(f"P-Rep not found: {address}")

        kwargs: dict = TypeConverter.convert(params, ParamType.IISS_SET_PREP)

        validate_prep_data(kwargs, True)

        if ConstantKeys.P2P_ENDPOINT in kwargs:
            p2p_endpoint: str = kwargs[ConstantKeys.P2P_ENDPOINT]
            del kwargs[ConstantKeys.P2P_ENDPOINT]
            kwargs["p2p_endpoint"] = p2p_endpoint

        # EventLog
        EventLogEmitter.emit_event_log(
            context,
            score_address=ZERO_SCORE_ADDRESS,
            event_signature="PRepSet(Address)",
            arguments=[address],
            indexed_args_count=0
        )

        # Update registration info
        dirty_prep.set(**kwargs)
        context.put_dirty_prep(dirty_prep)

    def handle_set_governance_variables(self,
                                        context: 'IconScoreContext',
                                        params: dict):
        """Handles setGovernanceVariables JSON-RPC API request

        :param context:
        :param params:
        :return:
        """
        # This API is available after IISS decentralization is enabled.
        if context.revision < REV_DECENTRALIZATION or self.term.sequence < 0:
            raise MethodNotFoundException("setGovernanceVariables is disabled")

        address: 'Address' = context.tx.origin

        dirty_prep: Optional['PRep'] = context.get_prep(address, mutable=True)
        if dirty_prep is None:
            raise InvalidParamsException(f"P-Rep not found: {address}")

        kwargs: dict = TypeConverter.convert(params, ParamType.IISS_SET_GOVERNANCE_VARIABLES)

        # Update incentive rep
        irep: int = kwargs["irep"]
        validate_irep(context, irep, dirty_prep)

        # EventLog
        EventLogEmitter.emit_event_log(
            context,
            score_address=ZERO_SCORE_ADDRESS,
            event_signature="GovernanceVariablesSet(Address,int)",
            arguments=[address, irep],
            indexed_args_count=1
        )

        # Update the changed properties of a P-Rep to stateDB
        # context.storage.prep.put_dirty_prep(context, prep)
        dirty_prep.set_irep(irep, context.block.height)
        context.put_dirty_prep(dirty_prep)

    def handle_unregister_prep(self, context: 'IconScoreContext', _params: dict):
        """Unregister a P-Rep

        :param context:
        :param _params:
        :return:
        """
        address: 'Address' = context.tx.origin

        dirty_prep: Optional['PRep'] = context.get_prep(address, mutable=True)
        if dirty_prep is None:
            raise InvalidParamsException(f"P-Rep not found: {address}")

        if dirty_prep.status != PRepStatus.ACTIVE:
            raise InvalidParamsException(f"Inactive P-Rep: {address}")

        dirty_prep.status = PRepStatus.UNREGISTERED
        context.put_dirty_prep(dirty_prep)

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
            score_address=ZERO_SCORE_ADDRESS,
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
        # TODO: Check how the exception is handled in governance SCORE (goldworm)

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

    def handle_get_main_preps(self, _context: 'IconScoreContext', _params: dict) -> dict:
        """Returns main P-Rep list in the current term

        :param _context:
        :param _params:
        :return:
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

    def handle_get_sub_preps(self, _context: 'IconScoreContext', _params: dict) -> dict:
        """Returns sub P-Rep list in the present term

        :param _context:
        :param _params:
        :return:
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

    def handle_get_preps(self, context: 'IconScoreContext', params: dict) -> dict:
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
            "totalDelegated": preps.total_delegated,
            "totalStake": context.storage.iiss.get_total_stake(context),
            "preps": prep_list
        }

    def handle_get_p2p_endpoints(self, _context: 'IconScoreContext', _params: dict) -> List[str]:
        if self.term is None:
            raise MethodNotFoundException("getP2PEndpoints not ready")

        endpoints: List[str] = []

        for prep_snapshot in self.term.preps:
            prep: 'PRep' = self.preps.get_by_address(prep_snapshot.address)
            endpoints.append(prep.p2p_endpoint)

        return endpoints

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
        assert 0 <= len(updated_accounts) <= IISS_MAX_DELEGATIONS * 2

        for account in updated_accounts:
            assert isinstance(account, Account)
            address = account.address

            # If a delegated account is a P-Rep, then update its delegated amount
            dirty_prep: Optional['PRep'] = context.get_prep(address, mutable=True)
            if dirty_prep:
                dirty_prep.delegated = account.delegated_amount
                context.put_dirty_prep(dirty_prep)
