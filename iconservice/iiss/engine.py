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
from collections import OrderedDict
from typing import TYPE_CHECKING, Any, Optional, List, Dict, Tuple, Union

from iconcommons.logger import Logger
from .reward_calc.data_creator import DataCreator as RewardCalcDataCreator
from .reward_calc.ipc.message import CalculateResponse, VersionResponse
from .reward_calc.ipc.reward_calc_proxy import RewardCalcProxy
from ..base.ComponentBase import EngineBase
from ..base.address import Address
from ..base.address import ZERO_SCORE_ADDRESS
from ..base.exception import InvalidParamsException
from ..base.type_converter import TypeConverter
from ..base.type_converter_templates import ConstantKeys, ParamType
from ..icon_constant import IISS_SOCKET_PATH, IISS_MAX_DELEGATIONS, ISCORE_EXCHANGE_RATE, ICON_SERVICE_LOG_TAG
from ..icon_constant import PREP_MAIN_PREPS
from ..iconscore.icon_score_context import IconScoreContext
from ..iconscore.icon_score_event_log import EventLogEmitter
from ..icx import Intent
from ..icx.issue.issue_formula import IssueFormula
from ..precommit_data_manager import PrecommitFlag

if TYPE_CHECKING:
    from ..precommit_data_manager import PrecommitData
    from ..icx.icx_account import Account
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

    def open(self, context: 'IconScoreContext', path: str):
        self._init_reward_calc_proxy(path)

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
            raise AssertionError(f"Reward calc has failed calculating about block height:{cb_data.block_height}")

        IconScoreContext.storage.rc.put_prev_calc_period_issued_iscore(cb_data.iscore)
        Logger.debug(f"calculate callback called with {cb_data}", ICON_SERVICE_LOG_TAG)

    def _init_reward_calc_proxy(self, data_path: str):
        self._reward_calc_proxy = RewardCalcProxy(calc_callback=self.calculate_callback,
                                                  version_callback=self.version_callback)
        self._reward_calc_proxy.open(sock_path=IISS_SOCKET_PATH, iiss_db_path=data_path)
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
        params: dict = data['params']

        handler: callable = self._invoke_handlers[method]
        handler(context, params)

    def query(self, context: 'IconScoreContext', data: dict) -> Any:
        method: str = data['method']
        params: dict = data['params']

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
        address: 'Address' = context.tx.origin

        delegations: List[Tuple['Address', int]] = self._convert_params_of_set_delegation(params)

        delegated_accounts: List['Account'] = \
            self._put_delegation_to_state_db(context, address, delegations)
        self._put_delegation_to_rc_db(context, address, delegations)

        for listener in self._listeners:
            listener.on_set_delegation(context, delegated_accounts)

    @staticmethod
    def _convert_params_of_set_delegation(params: dict) -> List[Tuple['Address', int]]:
        """Convert delegations format

        [{"address": "hxe7af5fcfd8dfc67530a01a0e403882687528dfcb", "value", "0xde0b6b3a7640000"}, ...] ->
        [("hxe7af5fcfd8dfc67530a01a0e403882687528dfcb", 1000000000000000000), ...]

        :param params: params of setDelegation JSON-RPC API request
        :return:
        """
        delegations: Optional[List[Dict[str, str]]] = params.get(ConstantKeys.DELEGATIONS)
        assert delegations is None or isinstance(delegations, list)

        if delegations is None or len(delegations) == 0:
            return []

        if len(delegations) > IISS_MAX_DELEGATIONS:
            raise InvalidParamsException("Delegations out of range")

        delegated_addresses: Dict['Address', int] = {}

        ret_params: dict = TypeConverter.convert(params, ParamType.IISS_SET_DELEGATION)
        delegations: List[Dict[str, Union['Address', int]]] = \
            ret_params[ConstantKeys.DELEGATIONS]

        delegation_list = []
        for delegation in delegations:
            address: 'Address' = delegation["address"]
            value: int = delegation["value"]
            assert isinstance(address, Address)
            assert isinstance(value, int)

            if value < 0:
                raise InvalidParamsException(f"Invalid delegating amount: {value}")

            if address in delegated_addresses:
                raise InvalidParamsException(f"Duplicated address: {address}")

            delegation_list.append((address, value))
            delegated_addresses[address] = 1

        return delegation_list

    @staticmethod
    def _put_delegation_to_state_db(
            context: 'IconScoreContext',
            delegating_address: 'Address',
            delegations: List[Tuple['Address', int]]) -> List['Account']:

        icx_storage: 'IcxStorage' = context.storage.icx

        account_dict: Dict['Address', Tuple['Account', int]] = OrderedDict()
        account_list = []

        delegating_account: 'Account' = \
            icx_storage.get_account(context, delegating_address, Intent.DELEGATING)

        # Get old delegations from delegating account
        old_delegations: List[Tuple[Address, int]] = delegating_account.delegations
        if old_delegations:
            for address, delegated in old_delegations:
                assert delegated > 0

                if address == delegating_address:
                    account: 'Account' = delegating_account
                else:
                    account: 'Account' = icx_storage.get_account(context, address, Intent.DELEGATED)

                assert account.delegated_amount >= delegated
                account_dict[address] = (account, -delegated)

        # Update the delegation list of tx.sender
        delegating_account.delegation_part.set_delegations(delegations)

        # Merge old and new delegations
        for address, delegated in delegations:
            assert delegated > 0

            if address in account_dict:
                account, offset = account_dict[address]
                offset += delegated
            else:
                if address == delegating_address:
                    account: 'Account' = delegating_account
                else:
                    account: 'Account' = icx_storage.get_account(context, address, Intent.DELEGATED)
                offset = delegated

            if offset != 0:
                account_dict[address] = (account, offset)

        # Save delegating and delegated accounts to stateDB
        for address, (account, offset) in account_dict.items():
            account.delegation_part.delegated_amount += offset
            icx_storage.put_account(context, account)
            account_list.append(account)

        # Save delegating account to stateDB
        if delegating_address not in account_dict:
            icx_storage.put_account(context, delegating_account)

        return account_list

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
