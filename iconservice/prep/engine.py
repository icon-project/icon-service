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

from typing import TYPE_CHECKING, Any, Optional, List, Dict, Tuple

from iconcommons.logger import Logger

from .data.prep import PRep, PRepDictType
from .data.prep_container import PRepContainer
from .term import Term
from .validator import validate_prep_data, validate_irep
from ..base.ComponentBase import EngineBase
from ..base.address import Address, ZERO_SCORE_ADDRESS
from ..base.exception import InvalidParamsException, MethodNotFoundException, ServiceNotReadyException
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
from ..utils.hashing.hash_generator import RootHashGenerator

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
            "getPReps": self.handle_get_prep_list,
            "getPRepTerm": self.handle_get_prep_term,
            "getBlacklistPReps": self.handle_get_blacklist_prep_list
        }

        self.preps = PRepContainer()
        self.term = Term()
        self._initial_irep: Optional[int] = None

        Logger.debug("PRepEngine.__init__() end")

    def open(self,
             context: 'IconScoreContext',
             term_period: int,
             irep: int,
             penalty_grace_period: int,
             min_productivity_percentage: int,
             max_unvalidated_sequence_block: int):

        # this logic doesn't need to save to DB yet
        PRep.init_prep_config(penalty_grace_period,
                              min_productivity_percentage,
                              max_unvalidated_sequence_block)

        self._load_preps(context)
        self.term.load(context, term_period)
        self._initial_irep = irep

        context.engine.iiss.add_listener(self)

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

        # Updated every term
        if precommit_data.term is not None:
            self.term: 'Term' = precommit_data.term

    def rollback(self):
        pass

    def on_term_ended(self, context: 'IconScoreContext') -> Tuple[dict, 'Term']:
        """Called in IconServiceEngine.invoke() every time when a term is ended

        Update P-Rep grades according to PRep.delegated
        """
        self._put_last_term_info(context, self.term)
        context.storage.meta.put_last_main_preps(context, self.term.main_preps)

        self._update_prep_grades(context)

        invalid_preps: List[int] = self.get_invalid_preps(self.term, context)
        self.term.update_suspended_preps(invalid_preps)

        self._release_turn_over(context)

        term: 'Term' = self._create_next_term(self.term, context)
        main_preps_as_dict: dict = self.get_updated_main_preps(term, PRepResultState.NORMAL)
        term.save(context)
        return main_preps_as_dict, term

    @classmethod
    def _put_last_term_info(cls,
                            context: 'IconScoreContext',
                            term: 'Term'):

        _, last_calc_end = context.storage.meta.get_last_term_info(context)
        if last_calc_end > 0:
            start: int = term.start_block_height
            end: int = term.end_block_height
        else:
            # first
            start: int = -1
            end: int = context.block.height
        context.storage.meta.put_last_term_info(context,
                                                start,
                                                end)

    def on_term_updated(self, context: 'IconScoreContext') -> Tuple[dict, Optional['Term']]:
        context.storage.meta.put_last_main_preps(context, self.term.main_preps)

        invalid_preps: List[int] = self.get_invalid_preps(self.term, context)
        self.term.update_suspended_preps(invalid_preps)

        term: Optional['Term'] = self._create_updated_term(self.term, invalid_preps)
        if term:
            main_preps_as_dict: dict = self.get_updated_main_preps(term, PRepResultState.IN_TERM_UPDATED)
            term.save(context)
        else:
            main_preps_as_dict: dict = {}
        return main_preps_as_dict, term

    def _update_prep_grades(self, context: 'IconScoreContext'):
        main_prep_count: int = context.main_prep_count
        main_and_sub_prep_count: int = context.main_and_sub_prep_count
        old_preps: List['PRep'] = self.term.preps
        new_preps: 'PRepContainer' = context.preps

        prep_grades: Dict['Address', Tuple['PRepGrade', 'PRepGrade']] = {}

        # Put the address and grade of a old P-Rep to prep_grades dict
        for prep in old_preps:
            # grades[0] is an old grade and grades[1] is a new grade
            prep_grades[prep.address] = (prep.grade, PRepGrade.CANDIDATE)

        # Remove the P-Reps which preserve the same grade in the next term from prep_grades dict
        for i in range(main_and_sub_prep_count):
            prep: 'PRep' = new_preps.get_by_index(i)
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
            dirty_prep: 'PRep' = context.get_prep(address, mutable=True)
            assert dirty_prep is not None

            dirty_prep.grade = grades[1]
            context.put_dirty_prep(dirty_prep)

        context.update_dirty_prep_batch()

    def _release_turn_over(self, context: 'IconScoreContext'):
        for address in self.term.suspended_preps:
            prep: 'PRep' = context.preps.remove(address)
            assert prep is not None

            dirty_prep = prep.copy()
            dirty_prep.release_suspend()
            context.preps.add(dirty_prep)

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

    def check_end_block_height_of_term(self, context: 'IconScoreContext') -> bool:
        """Is the last block of the current term

        :param context:
        :return:
        """
        return self.term.end_block_height == context.block.height

    @classmethod
    def get_updated_main_preps(cls, term: 'Term', state: 'PRepResultState') -> Optional[dict]:
        """Returns preps which will run as main preps during the next term in dict format

        :return:
        """
        prep_as_dict: Optional[dict] = \
            cls.get_main_preps_in_dict(term.main_preps)

        if prep_as_dict:
            prep_as_dict['irep'] = term.irep
            prep_as_dict['state'] = state.value

        return prep_as_dict

    @classmethod
    def get_main_preps_in_dict(cls, preps: List['PRep']) -> Optional[dict]:
        count: int = len(preps)
        if count == 0:
            Logger.warning(tag="PREP", msg="No P-Rep candidates")
            return None

        prep_as_dict: dict = {}
        preps_as_list: list = []
        prep_addresses: List[bytes] = []

        for i in range(count):
            prep: 'PRep' = preps[i]
            preps_as_list.append({
                ConstantKeys.PREP_ID: prep.address,
                ConstantKeys.P2P_ENDPOINT: prep.p2p_endpoint
            })
            prep_addresses.append(prep.address.to_bytes_including_prefix())

        prep_as_dict["preps"] = preps_as_list
        prep_as_dict["rootHash"]: bytes = RootHashGenerator.generate_root_hash(values=prep_addresses, do_hash=True)

        return prep_as_dict

    @classmethod
    def _create_next_term(cls,
                          src_term: 'Term',
                          context: 'IconScoreContext') -> 'Term':
        new_preps: List['PRep'] = context.preps.get_preps(start_index=0, size=context.main_and_sub_prep_count)

        # The current P-Rep term is over. Prepare the next P-Rep term
        irep: int = cls._calculate_weighted_average_of_irep(new_preps[:context.main_prep_count])

        term: 'Term' = Term.create_next_term(
            src_term.sequence + 1,
            context.main_prep_count,
            context.main_and_sub_prep_count,
            context.block.height,
            new_preps,
            context.total_supply,
            context.preps.total_delegated,
            src_term.period,
            irep
        )

        return term

    @classmethod
    def _create_updated_term(cls,
                             src_term: 'Term',
                             invalid_preps: List[int]) -> Optional['Term']:
        if invalid_preps:
            term: 'Term' = Term.create_update_term(src_term, invalid_preps)
        else:
            term = None
        return term

    @classmethod
    def get_invalid_preps(cls,
                          src_term: 'Term',
                          context: 'IconScoreContext') -> List[int]:

        # gather PReps who has gotten a penalty on this block
        invalid_preps: List[int] = []
        for i, main_prep in enumerate(src_term.main_preps):
            prep: 'PRep' = context.get_prep(main_prep.address)
            if prep.status != PRepStatus.ACTIVE:
                invalid_preps.append(i)
        return invalid_preps

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

        if not self._unregister_prep(context, address, PRepStatus.UNREGISTERED):
            return

        # EventLog
        EventLogEmitter.emit_event_log(
            context,
            score_address=ZERO_SCORE_ADDRESS,
            event_signature="PRepUnregistered(Address)",
            arguments=[address],
            indexed_args_count=0
        )

    @classmethod
    def impose_block_validation_penalty(
            cls,
            context: 'IconScoreContext',
            address: 'Address'):

        dirty_prep: Optional['PRep'] = context.get_prep(address, mutable=True)

        if dirty_prep is None:
            raise InvalidParamsException(f"P-Rep not found: {address}")

        if dirty_prep.status != PRepStatus.ACTIVE:
            return

        dirty_prep.status: 'PRepStatus' = PRepStatus.SUSPENDED
        dirty_prep.penalty: 'PenaltyReason' = PenaltyReason.BLOCK_VALIDATION
        context.put_dirty_prep(dirty_prep)

        EventLogEmitter.emit_event_log(
            context,
            score_address=ZERO_SCORE_ADDRESS,
            event_signature=PREP_PENALTY_SIGNATURE,
            arguments=[
                dirty_prep.address,
                PRepStatus.SUSPENDED.value,
                PenaltyReason.BLOCK_VALIDATION.value],
            indexed_args_count=1)

    @classmethod
    def impose_low_productivity_penalty(
            cls,
            context: 'IconScoreContext',
            address: 'Address'):

        if not cls._unregister_prep(context,
                                    address=address,
                                    status=PRepStatus.DISQUALIFIED,
                                    reason=PenaltyReason.LOW_PRODUCTIVITY):
            return

        # TODO slashing

        EventLogEmitter.emit_event_log(
            context,
            score_address=ZERO_SCORE_ADDRESS,
            event_signature=PREP_PENALTY_SIGNATURE,
            arguments=[
                address,
                PRepStatus.DISQUALIFIED.value,
                PenaltyReason.LOW_PRODUCTIVITY.value
            ],
            indexed_args_count=1)

    @classmethod
    def impose_prep_disqualified_penalty(
            cls,
            context: 'IconScoreContext',
            address: 'Address'):

        if not cls._unregister_prep(context,
                                    address=address,
                                    status=PRepStatus.DISQUALIFIED,
                                    reason=PenaltyReason.PREP_DISQUALIFICATION):
            return

        # TODO slashing

        EventLogEmitter.emit_event_log(
            context,
            score_address=ZERO_SCORE_ADDRESS,
            event_signature=PREP_PENALTY_SIGNATURE,
            arguments=[
                address,
                PRepStatus.DISQUALIFIED.value,
                PenaltyReason.PREP_DISQUALIFICATION.value,
            ],
            indexed_args_count=1)

    @classmethod
    def _unregister_prep(
            cls,
            context: 'IconScoreContext',
            address: 'Address',
            status: 'PRepStatus',
            reason: 'PenaltyReason' = PenaltyReason.NONE):

        dirty_prep: Optional['PRep'] = context.get_prep(address, mutable=True)
        if dirty_prep is None:
            raise InvalidParamsException(f"P-Rep not found: {address}")

        if dirty_prep.status == status:
            return False

        if status == PRepStatus.UNREGISTERED and dirty_prep.status != PRepStatus.ACTIVE:
            raise InvalidParamsException(f"Inactive P-Rep: {address}")

        dirty_prep.status: 'PRepStatus' = status
        dirty_prep.penalty: 'PenaltyReason' = reason
        context.put_dirty_prep(dirty_prep)

        # Update rcDB
        cls._put_unreg_prep_for_iiss_db(context, address)

        return True

    @classmethod
    def _put_unreg_prep_for_iiss_db(cls, context: 'IconScoreContext', address: 'Address'):
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
            "totalDelegated": preps.total_delegated,
            "totalStake": context.storage.iiss.get_total_stake(context),
            "preps": prep_list
        }

    def handle_get_blacklist_prep_list(self, context: 'IconScoreContext', params: dict) -> dict:
        """
        Returns unregistered PReps called blacklist preps
        of which status is out of UNREGISTERED, DISQUALIFIED and SUSPENDED

        :param context: IconScoreContext
        :param params: parameters
        :return: block height and blacklist preps in dict
        """
        preps: 'PRepContainer' = self.preps
        prep_list: list = preps.get_inactive_preps()
        prep_list = [prep.to_dict(PRepDictType.ABRIDGED) for prep in prep_list]
        return {
            "blockHeight": context.block.height,
            "preps": prep_list
        }

    def handle_get_prep_term(self, context: 'IconScoreContext', params: dict) -> dict:
        """Provides the information on the current term

        :param context:
        :param params:
        :return:
        """
        if self.term.sequence < 0:
            raise ServiceNotReadyException("Term is not ready")

        preps: List['PRep'] = self.term.preps
        preps_data = []
        for prep in preps:
            preps_data.append(
                {
                    "name": prep.name,
                    "country": prep.country,
                    "city": prep.city,
                    "grade": prep.grade.value,
                    "address": prep.address,
                    "p2pEndpoint": prep.p2p_endpoint
                }
            )

        return {
            "blockHeight": context.block.height,
            "sequence": self.term.sequence,
            "startBlockHeight": self.term.start_block_height,
            "endBlockHeight": self.term.end_block_height,
            "totalSupply": context.total_supply,
            "totalDelegated": self.term.total_delegated,
            "irep": self.term.irep,
            "preps": preps_data
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
        assert 0 <= len(updated_accounts) <= IISS_MAX_DELEGATIONS * 2

        for account in updated_accounts:
            assert isinstance(account, Account)
            address = account.address

            # If a delegated account is a P-Rep, then update its delegated amount
            dirty_prep: Optional['PRep'] = context.get_prep(address, mutable=True)
            if dirty_prep:
                dirty_prep.delegated = account.delegated_amount
                context.put_dirty_prep(dirty_prep)
