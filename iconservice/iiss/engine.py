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

from abc import ABCMeta, abstractmethod
from typing import TYPE_CHECKING, Any, Optional, List, Dict, Tuple, Union

from iconcommons.logger import Logger
from .reward_calc.data_creator import DataCreator as RewardCalcDataCreator
from .reward_calc.ipc.message import CalculateResponse, VersionResponse
from .reward_calc.ipc.reward_calc_proxy import RewardCalcProxy
from ..base.ComponentBase import EngineBase
from ..base.address import Address
from ..base.address import ZERO_SCORE_ADDRESS
from ..base.exception import InvalidParamsException, InvalidRequestException, OutOfBalanceException, FatalException
from ..base.type_converter import TypeConverter
from ..base.type_converter_templates import ConstantKeys, ParamType
from ..icon_constant import IISS_MAX_DELEGATIONS, ISCORE_EXCHANGE_RATE, ICON_SERVICE_LOG_TAG
from ..icon_constant import PREP_MAIN_PREPS
from ..iconscore.icon_score_context import IconScoreContext
from ..iconscore.icon_score_event_log import EventLogEmitter
from ..icx import Intent
from ..icx.icx_account import Account
from ..icx.issue.issue_formula import IssueFormula
from ..precommit_data_manager import PrecommitFlag

if TYPE_CHECKING:
    from ..precommit_data_manager import PrecommitData
    from .reward_calc.msg_data import TxData, DelegationInfo, DelegationTx, Header, BlockProduceInfoData, PRepsData
    from .reward_calc.msg_data import GovernanceVariable
    from .storage import Reward
    from ..prep.data.prep import PRep
    from ..icx import IcxStorage


class EngineListener(metaclass=ABCMeta):
    @abstractmethod
    def on_set_stake(self, context: 'IconScoreContext', account: 'Account'):
        pass

    @abstractmethod
    def on_set_delegation(self, context: 'IconScoreContext', delegated_accounts: List['Account']):
        pass


class Engine(EngineBase):
    """IISSEngine class

    """

    def __init__(self):
        super().__init__()

        self._invoke_handlers: dict = {
            'setStake': self.handle_set_stake,
            'setDelegation': self.handle_set_delegation,
            'claimIScore': self.handle_claim_iscore
        }

        self._query_handler: dict = {
            'getStake': self.handle_get_stake,
            'getDelegation': self.handle_get_delegation,
            'queryIScore': self.handle_query_iscore
        }

        self._reward_calc_proxy: Optional['RewardCalcProxy'] = None
        self._listeners: List['EngineListener'] = []

    def open(self, context: 'IconScoreContext', log_dir: str, data_path: str, socket_path: str):
        self._init_reward_calc_proxy(log_dir, data_path, socket_path)

    def add_listener(self, listener: 'EngineListener'):
        assert isinstance(listener, EngineListener)
        self._listeners.append(listener)

    def remove_listener(self, listener: 'EngineListener'):
        assert isinstance(listener, EngineListener)
        self._listeners.remove(listener)

    # TODO implement version callback function
    @staticmethod
    def version_callback(cb_data: 'VersionResponse'):
        Logger.debug(tag="iiss", msg=f"version callback called with {cb_data}")

    @staticmethod
    def calculate_callback(cb_data: 'CalculateResponse'):
        # cb_data.success == False: RC has reset the state to before 'CALCULATE' request
        if not cb_data.success:
            raise FatalException(f"Reward calc has failed calculating about block height:{cb_data.block_height}")

        IconScoreContext.storage.rc.put_prev_calc_period_issued_iscore(cb_data.iscore)
        Logger.debug(f"calculate callback called with {cb_data}", ICON_SERVICE_LOG_TAG)

    def _init_reward_calc_proxy(self, log_dir: str, data_path: str, socket_path: str):
        self._reward_calc_proxy = RewardCalcProxy(calc_callback=self.calculate_callback,
                                                  version_callback=self.version_callback)
        self._reward_calc_proxy.open(log_dir=log_dir, sock_path=socket_path, iiss_db_path=data_path)
        self._reward_calc_proxy.start()

    def _close_reward_calc_proxy(self):
        self._reward_calc_proxy.stop()
        self._reward_calc_proxy.close()

    def _init_handlers(self, handlers: list):
        for handler in handlers:
            handler.reward_calc_proxy = self._reward_calc_proxy

    def close(self):
        self._close_reward_calc_proxy()

    def invoke(self, context: 'IconScoreContext', data: dict) -> None:
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

    def handle_set_stake(self, context: 'IconScoreContext', params: dict):

        address: 'Address' = context.tx.origin
        ret_params: dict = TypeConverter.convert(params, ParamType.IISS_SET_STAKE)
        value: int = ret_params[ConstantKeys.VALUE]

        if not isinstance(value, int) or value < 0:
            raise InvalidParamsException('Failed to stake: value is not int type or value < 0')

        account: 'Account' = context.storage.icx.get_account(context, address, Intent.STAKE)

        unstake_lock_period = context.storage.iiss.get_unstake_lock_period(context)
        account.set_stake(value, unstake_lock_period)
        context.storage.icx.put_account(context, account)
        # TODO tx_result make if needs

        for listener in self._listeners:
            listener.on_set_stake(context, account)

        self._check_from_can_charge_fee_v3(context, value, account.balance, account.total_stake)

    @classmethod
    def _check_from_can_charge_fee_v3(cls, context: 'IconScoreContext', value: int, balance: int, total_stake: int):
        fee: int = context.step_counter.step_price * context.step_counter.step_used
        amount: int = balance + total_stake
        if amount < value + fee:
            raise OutOfBalanceException(
                f'Out of balance: balance({amount}) < value({value}) + fee({fee})')

    def handle_get_stake(self, context: 'IconScoreContext', params: dict) -> dict:

        ret_params: dict = TypeConverter.convert(params, ParamType.IISS_GET_STAKE)
        address: 'Address' = ret_params[ConstantKeys.ADDRESS]
        return self._get_stake(context, address)

    @classmethod
    def _get_stake(cls, context: 'IconScoreContext', address: 'Address') -> dict:

        account: 'Account' = context.storage.icx.get_account(context, address, Intent.STAKE)

        stake: int = account.stake
        unstake: int = account.unstake
        unstake_block_beight: int = account.unstake_block_height

        data = {
            "stake": stake
        }

        if unstake_block_beight:
            data["unstake"] = unstake
            data["unstakeBlockHeight"] = unstake_block_beight

        return data

    def handle_set_delegation(self, context: 'IconScoreContext', params: dict):
        """Handles setDelegation JSON-RPC API request

        :param context:
        :param params:
        :return:
        """
        sender: 'Address' = context.tx.origin
        cached_accounts: Dict['Address', Tuple['Account', int]] = {}

        # Convert setDelegation params
        total_delegating, new_delegations = \
            self._convert_params_of_set_delegation(params)

        # Check whether voting power is enough to delegate
        self._check_voting_power_is_enough(context, sender, total_delegating, cached_accounts)

        # Get old delegations from delegating accounts
        self._get_old_delegations_from_sender_account(context, sender, cached_accounts)

        # Calculate delegations with old and new delegations
        self._calc_delegations(context, new_delegations, cached_accounts)

        # Put updated delegation data to stateDB
        updated_accounts: List['Account'] = \
            self._put_delegation_to_state_db(context, sender, new_delegations, cached_accounts)

        # Put updated delegation data to rcDB
        self._put_delegation_to_rc_db(context, sender, new_delegations)

        for listener in self._listeners:
            listener.on_set_delegation(context, updated_accounts)

    @staticmethod
    def _convert_params_of_set_delegation(params: dict) -> Tuple[int, List[Tuple['Address', int]]]:
        """Convert delegations format

        [{"address": "hxe7af5fcfd8dfc67530a01a0e403882687528dfcb", "value", "0xde0b6b3a7640000"}, ...] ->
        [("hxe7af5fcfd8dfc67530a01a0e403882687528dfcb", 1000000000000000000), ...]

        :param params: params of setDelegation JSON-RPC API request
        :return: total_delegating, (address, delegated)
        """
        delegations: Optional[List[Dict[str, str]]] = params.get(ConstantKeys.DELEGATIONS)
        assert delegations is None or isinstance(delegations, list)

        if delegations is None or len(delegations) == 0:
            return 0, []

        if len(delegations) > IISS_MAX_DELEGATIONS:
            raise InvalidParamsException("Delegations out of range")

        ret_params: dict = TypeConverter.convert(params, ParamType.IISS_SET_DELEGATION)
        delegations: List[Dict[str, Union['Address', int]]] = \
            ret_params[ConstantKeys.DELEGATIONS]

        total_delegating: int = 0
        converted_delegations: List[Tuple['Address', int]] = []
        delegated_addresses: Dict['Address', int] = {}

        for delegation in delegations:
            address: 'Address' = delegation["address"]
            value: int = delegation["value"]
            assert isinstance(address, Address)
            assert isinstance(value, int)

            if value < 0:
                raise InvalidParamsException(f"Invalid delegating amount: {value}")

            if address in delegated_addresses:
                raise InvalidParamsException(f"Duplicated address: {address}")

            delegated_addresses[address] = value

            if value > 0:
                total_delegating += value
                converted_delegations.append((address, value))

        return total_delegating, converted_delegations

    @staticmethod
    def _check_voting_power_is_enough(
            context: 'IconScoreContext',
            sender: 'Address', delegating: int,
            cached_accounts: Dict['Address', Tuple['Account', int]]):
        """

        :param context:
        :param sender:
        :param cached_accounts:
        :param delegating:
        :return:
        """
        account: 'Account' = context.storage.icx.get_account(context, sender, Intent.DELEGATING)
        assert isinstance(account, Account)

        if account.voting_weight < delegating:
            raise InvalidRequestException("Not enough voting power")

        cached_accounts[sender] = account, 0

    @staticmethod
    def _get_old_delegations_from_sender_account(
            context: 'IconScoreContext',
            sender: 'Address',
            cached_accounts: Dict['Address', Tuple['Account', int]]):
        """Get old delegations from sender account

        :param context:
        :param sender:
        :param cached_accounts:
        :return:
        """
        icx_storage = context.storage.icx
        sender_account: 'Account' = cached_accounts[sender][0]

        old_delegations: List[Tuple[Address, int]] = sender_account.delegations
        if not old_delegations:
            return

        for address, old_delegated in old_delegations:
            assert old_delegated > 0

            cached: Tuple['Account', int] = cached_accounts.get(address)
            if cached is None:
                account: 'Account' = icx_storage.get_account(context, address, Intent.DELEGATED)
            else:
                account: 'Account' = cached[0]

            assert account.delegated_amount >= old_delegated
            cached_accounts[address] = account, -old_delegated

    @staticmethod
    def _calc_delegations(
            context: 'IconScoreContext',
            new_delegations: List[Tuple['Address', int]],
            cached_accounts: Dict['Address', Tuple['Account', int]]):
        """Calculate new delegated amounts for each address with old and new delegations

        :param new_delegations:
        :param cached_accounts:
        :return:
        """
        icx_storage = context.storage.icx

        for address, new_delegated in new_delegations:
            assert new_delegated > 0

            if address in cached_accounts:
                account, old_delegated = cached_accounts[address]
            else:
                account: 'Account' = icx_storage.get_account(context, address, Intent.DELEGATED)
                old_delegated = 0

            cached_accounts[address] = account, new_delegated + old_delegated

    @staticmethod
    def _put_delegation_to_state_db(
            context: 'IconScoreContext',
            sender: 'Address',
            delegations: List[Tuple['Address', int]],
            cached_accounts: Dict['Address', Tuple['Account', int]]) -> List['Account']:
        """Put updated delegations to stateDB

        :param context:
        :param sender:
        :param delegations:
        :param cached_accounts:
        :return: updated account list
        """
        icx_storage: 'IcxStorage' = context.storage.icx

        sender_account: 'Account' = cached_accounts[sender][0]
        sender_account.set_delegations(delegations)

        updated_accounts: List['Account'] = []

        # Save changed accounts to stateDB
        for account, delegated_offset in cached_accounts.values():
            if delegated_offset != 0:
                account.delegation_part.delegated_amount += delegated_offset

            icx_storage.put_account(context, account)
            updated_accounts.append(account)

        return updated_accounts

    @staticmethod
    def _put_delegation_to_rc_db(
            context: 'IconScoreContext',
            address: 'Address',
            delegations: List[Tuple['Address', int]]):
        """Put new delegations from setDelegation JSON-RPC API request to RewardCalcDB

        :param context:
        :param address: The address of delegating account
        :param delegations: The list of delegations that the given address did
        :return:
        """
        delegation_list: list = []

        for delegation in delegations:
            info: 'DelegationInfo' = RewardCalcDataCreator.create_delegation_info(*delegation)
            delegation_list.append(info)

        delegation_tx: 'DelegationTx' = RewardCalcDataCreator.create_tx_delegation(delegation_list)
        iiss_tx_data: 'TxData' = RewardCalcDataCreator.create_tx(address, context.block.height, delegation_tx)
        context.storage.rc.put(context.rc_block_batch, iiss_tx_data)

    def handle_get_delegation(self, context: 'IconScoreContext', params: dict) -> dict:
        """Handles getDelegation JSON-RPC API request

        :param context:
        :param params:
        :return:
        """
        ret_params: dict = TypeConverter.convert(params, ParamType.IISS_GET_DELEGATION)
        address: 'Address' = ret_params[ConstantKeys.ADDRESS]
        return self._get_delegation(context, address)

    @classmethod
    def _get_delegation(cls, context: 'IconScoreContext', address: 'Address') -> dict:

        account: 'Account' = context.storage.icx.get_account(context, address, Intent.DELEGATING)
        delegation_list: list = []
        for address, value in account.delegations:
            delegation_list.append({"address": address, "value": value})

        data = {
            "delegations": delegation_list,
            "totalDelegated": account.delegations_amount,
            "votingPower": account.voting_power
        }

        return data

    @classmethod
    def _iscore_to_icx(cls, iscore: int) -> int:
        """Exchange iscore to icx

        10 ** -18 icx == 1 loop == 1000 iscore

        :param iscore:
        :return: icx
        """
        return iscore // ISCORE_EXCHANGE_RATE

    def handle_claim_iscore(self, context: 'IconScoreContext', _params: dict):
        """Handles claimIScore JSON-RPC request

        :param context:
        :param _params:
        :return:
        """
        address: 'Address' = context.tx.origin

        # TODO: error handling
        iscore, block_height = self._reward_calc_proxy.claim_iscore(
            address, context.block.height, context.block.hash)

        icx: int = self._iscore_to_icx(iscore)

        from_account: 'Account' = context.storage.icx.get_account(context, address)
        from_account.deposit(icx)
        context.storage.icx.put_account(context, from_account)

        EventLogEmitter.emit_event_log(
            context,
            score_address=ZERO_SCORE_ADDRESS,
            event_signature="IScoreClaimed(int,int)",
            arguments=[iscore, icx],
            indexed_args_count=0
        )

    def handle_query_iscore(self, _context: 'IconScoreContext', params: dict) -> dict:
        ret_params: dict = TypeConverter.convert(params, ParamType.IISS_QUERY_ISCORE)
        address: 'Address' = ret_params[ConstantKeys.ADDRESS]

        # TODO: error handling
        iscore, block_height = self._reward_calc_proxy.query_iscore(address)

        data = {
            "iscore": iscore,
            "icx": self._iscore_to_icx(iscore),
            "blockHeight": block_height
        }

        return data

    def update_db(self,
                  context: 'IconScoreContext',
                  prev_block_generator: Optional['Address'],
                  prev_block_validators: Optional[List['Address']],
                  flag: 'PrecommitFlag'):
        # every block time
        self._put_block_produce_info_to_rc_db(context, prev_block_generator, prev_block_validators)

        if not self._is_iiss_calc(flag):
            return

        self._put_next_calc_block_height(context)

        self._put_header_to_rc_db(context)
        self._put_gv(context)
        self._put_preps_to_rc_db(context)

    def send_ipc(self, context: 'IconScoreContext', precommit_data: 'PrecommitData'):
        block_height: int = precommit_data.block.height

        # every block time
        self._reward_calc_proxy.commit_block(True, block_height, precommit_data.block.hash)

        if not self._is_iiss_calc(precommit_data.precommit_flag):
            return

        path: str = context.storage.rc.create_db_for_calc(block_height)
        self._reward_calc_proxy.calculate(path, block_height)

    @classmethod
    def _is_iiss_calc(cls, flag: 'PrecommitFlag') -> bool:
        return bool(flag & (PrecommitFlag.GENESIS_IISS_CALC | PrecommitFlag.IISS_CALC))

    @classmethod
    def _check_update_calc_period(cls, context: 'IconScoreContext') -> bool:
        block_height: int = context.block.height
        check_end_block_height: Optional[int] = context.storage.iiss.get_end_block_height_of_calc(context)
        if check_end_block_height is None:
            return False

        return block_height == check_end_block_height

    @classmethod
    def _put_next_calc_block_height(cls, context: 'IconScoreContext'):
        calc_period: int = context.storage.iiss.get_calc_period(context)
        if calc_period is None:
            raise InvalidParamsException("Fail put next calc block height: didn't init yet")
        context.storage.iiss.put_end_block_height_of_calc(context, context.block.height + calc_period)

    @classmethod
    def _put_header_to_rc_db(cls, context: 'IconScoreContext'):
        data: 'Header' = RewardCalcDataCreator.create_header(0, context.block.height)
        context.storage.rc.put(context.rc_block_batch, data)

    @classmethod
    def _put_gv(cls, context: 'IconScoreContext'):
        current_total_supply = context.storage.icx.get_total_supply(context)
        current_total_prep_delegated: int = context.preps.total_prep_delegated
        reward_prep: 'Reward' = context.storage.iiss.get_reward_prep(context)

        reward_rep: int = IssueFormula.calculate_rrep(reward_prep.reward_min,
                                                      reward_prep.reward_max,
                                                      reward_prep.reward_point,
                                                      current_total_supply,
                                                      current_total_prep_delegated)

        irep: int = context.engine.prep.term.irep
        calculated_irep: int = IssueFormula.calculate_irep_per_block_contributor(irep)
        reward_prep.reward_rate = reward_rep

        data: 'GovernanceVariable' = RewardCalcDataCreator.create_gv_variable(context.block.height,
                                                                              calculated_irep,
                                                                              reward_rep)
        context.storage.iiss.put_reward_prep(context, reward_prep)
        context.storage.rc.put(context.rc_block_batch, data)

    @classmethod
    def _put_block_produce_info_to_rc_db(cls,
                                         context: 'IconScoreContext',
                                         prev_block_generator: Optional['Address'] = None,
                                         prev_block_validators: Optional[List['Address']] = None):
        if prev_block_generator is None or prev_block_validators is None:
            return

        Logger.debug(f"put_block_produce_info_for_rc", "iiss")
        data: 'BlockProduceInfoData' = RewardCalcDataCreator.create_block_produce_info_data(context.block.height,
                                                                                            prev_block_generator,
                                                                                            prev_block_validators)
        context.storage.rc.put(context.rc_block_batch, data)

    @classmethod
    def _put_preps_to_rc_db(cls, context: 'IconScoreContext'):
        preps: List['PRep'] = \
            context.engine.prep.preps.get_preps(start_index=0, size=PREP_MAIN_PREPS)

        if len(preps) == 0:
            return

        total_prep_delegated: int = 0
        for prep in preps:
            total_prep_delegated += prep.delegated

        Logger.debug(f"put_preps_for_rc: total_prep_delegated{total_prep_delegated}", "iiss")

        data: 'PRepsData' = RewardCalcDataCreator.create_prep_data(context.block.height,
                                                                   total_prep_delegated,
                                                                   preps)
        context.storage.rc.put(context.rc_block_batch, data)
