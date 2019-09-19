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
import time
from abc import ABCMeta, abstractmethod
from typing import TYPE_CHECKING, Any, Optional, List, Dict, Tuple, Union

from iconcommons.logger import Logger

from .reward_calc.data_creator import DataCreator as RewardCalcDataCreator
from .reward_calc.ipc.message import CalculateDoneNotification, ReadyNotification
from .reward_calc.ipc.reward_calc_proxy import RewardCalcProxy
from ..base.ComponentBase import EngineBase
from ..base.address import Address
from ..base.address import ZERO_SCORE_ADDRESS
from ..base.exception import \
    InvalidParamsException, InvalidRequestException, OutOfBalanceException, FatalException
from ..base.type_converter import TypeConverter
from ..base.type_converter_templates import ConstantKeys, ParamType
from ..icon_constant import IISS_MAX_DELEGATIONS, ISCORE_EXCHANGE_RATE, IISS_MAX_REWARD_RATE, \
    IconScoreContextType, IISS_LOG_TAG, RCCalculateResult
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
    from ..iiss.storage import RewardRate
    from ..icx import IcxStorage
    from ..prep.data import Term
    from ..base.block import Block

_TAG = IISS_LOG_TAG

QUERY_CALCULATE_REPEAT_COUNT = 3


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
    TAG = "IISS"

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
            'queryIScore': self.handle_query_iscore,
            'estimateUnstakeLockPeriod': self.handle_estimate_unstake_lock_period
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

    @staticmethod
    def ready_callback(cb_data: 'ReadyNotification'):
        Logger.debug(tag=_TAG, msg=f"ready callback called with {cb_data}")

    def get_ready_future(self):
        return self._reward_calc_proxy.get_ready_future()

    def is_reward_calculator_ready(self):
        return self._reward_calc_proxy.is_reward_calculator_ready()

    def get_prev_period_iscore(self,
                               context: 'IconScoreContext',
                               end_block_height_of_calc: Optional[int] = None) -> int:
        Logger.debug(tag=_TAG, msg=f"get_prev_period_iscore start")
        iscore, rc_latest_calculate_bh = context.storage.rc.get_calc_response_from_rc()
        if end_block_height_of_calc is None:
            end_block_height_of_calc: int = context.storage.iiss.get_end_block_height_of_calc(context)
        calc_period: int = context.storage.iiss.get_calc_period(context)
        latest_calculate_bh: int = end_block_height_of_calc - calc_period

        # Check if the response has been received
        if iscore == -1:
            iscore: int = self._query_calculate_result(latest_calculate_bh)
        else:
            context.engine.iiss.check_calculate_request_block_height(rc_latest_calculate_bh,
                                                                     latest_calculate_bh)
        Logger.debug(tag=_TAG, msg=f"get_prev_period_iscore end with {iscore}")
        return iscore

    def _query_calculate_result(self, calc_bh: int, repeat_cnt: int = QUERY_CALCULATE_REPEAT_COUNT) -> int:
        Logger.debug(tag=_TAG, msg=f"_query_calculate_result start")
        calc_result_status: int = -1
        calc_result_bh: int = -1
        iscore: int = -1

        for cnt in range(repeat_cnt):
            calc_result_status, calc_result_bh, iscore, state_hash = \
                self._reward_calc_proxy.query_calculate_result(calc_bh)
            if calc_result_status == RCCalculateResult.SUCCESS:
                break
            elif calc_result_status == RCCalculateResult.IN_PROGRESS:
                time.sleep(1)
                Logger.debug(tag=_TAG, msg=f"Repeat query calculate result {repeat_cnt}")
                continue
            else:
                raise FatalException(f'RC has a problem about calculating: {calc_result_status}')

        if calc_result_status != RCCalculateResult.SUCCESS:
            raise FatalException(f'RC has a problem about calculating: {calc_result_status}')

        if calc_result_bh != calc_bh:
            raise FatalException(f'Unexpected calculate result response '
                           f'(reward calc: {calc_result_bh} icon service: {calc_bh}')

        if iscore < 0:
            raise FatalException(f'Invalid I-SCORE value: {iscore}')
        Logger.debug(tag=_TAG, msg=f"_query_calculate_result end with "
                                   f"status:{calc_result_status} calc_result_bh: {calc_result_bh} iscore: {iscore}")

        return iscore

    @staticmethod
    def check_calculate_request_block_height(reward_calc_bh: int,
                                             icon_service_bh: int):

        if reward_calc_bh != icon_service_bh:
            raise FatalException(f"request block height is not matched: "
                                 f"response from RC:{reward_calc_bh} "
                                 f"request:{reward_calc_bh} ")

    def calculate_done_callback(self, cb_data: 'CalculateDoneNotification'):
        Logger.debug(tag=_TAG, msg=f"calculate_done_callback start")
        # cb_data.success == False: RC has reset the state to before 'CALCULATE' request
        if not cb_data.success:
            raise FatalException(f"Reward calc has failed calculating about block height:{cb_data.block_height}")

        # context for searching db data
        context: 'IconScoreContext' = IconScoreContext(IconScoreContextType.QUERY)
        end_block_height_of_calc: int = context.storage.iiss.get_end_block_height_of_calc(context)
        calc_period: int = context.storage.iiss.get_calc_period(context)

        latest_calculate_bh: int = end_block_height_of_calc - calc_period
        self.check_calculate_request_block_height(cb_data.block_height, latest_calculate_bh)

        IconScoreContext.storage.rc.put_calc_response_from_rc(cb_data.iscore, cb_data.block_height)
        Logger.debug(tag=_TAG, msg=f"calculate done callback called with {cb_data}")

    def _init_reward_calc_proxy(self, log_dir: str, data_path: str, socket_path: str):
        self._reward_calc_proxy = RewardCalcProxy(calc_done_callback=self.calculate_done_callback,
                                                  ready_callback=self.ready_callback)
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
        stake: int = ret_params[ConstantKeys.VALUE]
        total_stake: int = context.storage.iiss.get_total_stake(context)

        if not isinstance(stake, int) or stake < 0:
            raise InvalidParamsException('Failed to stake: value is not int type or value < 0')

        account: 'Account' = context.storage.icx.get_account(context, address, Intent.ALL)
        self._check_from_can_stake(context, stake, account)

        unstake_lock_period: int = self._calculate_unstake_lock_period(context.storage.iiss.lock_min,
                                                                       context.storage.iiss.lock_max,
                                                                       context.storage.iiss.reward_point,
                                                                       total_stake,
                                                                       context.total_supply)
        # subtract account's staked amount from the total stake
        total_stake -= account.stake
        account.set_stake(stake, unstake_lock_period)
        # add account's newly set staked amount from the total stake
        total_stake += account.stake
        context.storage.icx.put_account(context, account)
        context.storage.iiss.put_total_stake(context, total_stake)
        # TODO tx_result make if needs
        for listener in self._listeners:
            listener.on_set_stake(context, account)

    @classmethod
    def _check_from_can_stake(cls,
                              context: 'IconScoreContext',
                              stake: int,
                              account: 'Account'):
        fee: int = context.step_counter.step_price * context.step_counter.step_used

        if account.balance + account.total_stake < stake + fee:
            raise OutOfBalanceException(
                f'Out of balance: balance({account.balance}) + total_stake({account.total_stake})'
                f' < stake({stake}) + fee({fee})')

        if stake < account.delegations_amount:
            raise InvalidParamsException(f"Failed to stake: stake({stake})"
                                         f" < delegations_amount({account.delegations_amount})")

    @classmethod
    def _calculate_unstake_lock_period(cls,
                                       lmin: int,
                                       lmax: int,
                                       rpoint: int,
                                       total_stake: int,
                                       total_supply: int):
        stake_percentage: float = total_stake / total_supply
        if stake_percentage >= rpoint / IISS_MAX_REWARD_RATE:
            return lmin

        first_operand: float = (lmax - lmin) / (rpoint / IISS_MAX_REWARD_RATE) ** 2
        second_operand: float = (stake_percentage - (rpoint / IISS_MAX_REWARD_RATE)) ** 2
        return int(first_operand * second_operand) + lmin

    def handle_get_stake(self, context: 'IconScoreContext', params: dict) -> dict:

        ret_params: dict = TypeConverter.convert(params, ParamType.IISS_GET_STAKE)
        address: 'Address' = ret_params[ConstantKeys.ADDRESS]
        return self._get_stake(context, address)

    @classmethod
    def _get_stake(cls, context: 'IconScoreContext', address: 'Address') -> dict:

        account: 'Account' = context.storage.icx.get_account(context, address, Intent.STAKE)

        stake: int = account.stake
        unstake: int = account.unstake
        unstake_block_height: int = account.unstake_block_height

        data = {
            "stake": stake
        }

        if unstake_block_height:
            data["unstake"] = unstake
            data["unstakeBlockHeight"] = unstake_block_height
            data["remainingBlocks"] = unstake_block_height - context.block.height

        return data

    def handle_estimate_unstake_lock_period(self, context: 'IconScoreContext', _params: dict):
        total_stake: int = context.storage.iiss.get_total_stake(context)
        unstake_lock_period: int = self._calculate_unstake_lock_period(context.storage.iiss.lock_min,
                                                                       context.storage.iiss.lock_max,
                                                                       context.storage.iiss.reward_point,
                                                                       total_stake,
                                                                       context.total_supply)
        return {
            "unstakeLockPeriod": unstake_lock_period
        }

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

    @classmethod
    def _convert_params_of_set_delegation(cls,
                                          params: dict) -> Tuple[int, List[Tuple['Address', int]]]:
        """Convert delegations format

        [{"address": "hxe7af5fcfd8dfc67530a01a0e403882687528dfcb", "value", "0xde0b6b3a7640000"}, ...] ->
        [("hxe7af5fcfd8dfc67530a01a0e403882687528dfcb", 1000000000000000000), ...]

        :param params: params of setDelegation JSON-RPC API request
        :return: total_delegating, (address, delegated)
        """

        if len(params) == 1:
            delegations: Optional[List[Dict[str, str]]] = params[ConstantKeys.DELEGATIONS]
        elif len(params) == 0:
            delegations = None
        else:
            raise InvalidParamsException(f"Invalid params: {params}")

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

    @classmethod
    def _check_voting_power_is_enough(cls,
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
        account: 'Account' = context.storage.icx.get_account(context, sender, Intent.ALL)
        assert isinstance(account, Account)

        if account.voting_weight < delegating:
            raise InvalidRequestException("Not enough voting power")

        cached_accounts[sender] = account, 0

    @classmethod
    def _get_old_delegations_from_sender_account(cls,
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

    @classmethod
    def _calc_delegations(cls,
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

    @classmethod
    def _put_delegation_to_state_db(cls,
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

    @classmethod
    def _put_delegation_to_rc_db(cls,
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

    def handle_get_delegation(self,
                              context: 'IconScoreContext',
                              params: dict) -> dict:
        """Handles getDelegation JSON-RPC API request

        :param context:
        :param params:
        :return:
        """
        ret_params: dict = TypeConverter.convert(params, ParamType.IISS_GET_DELEGATION)
        address: 'Address' = ret_params[ConstantKeys.ADDRESS]
        return self._get_delegation(context, address)

    @classmethod
    def _get_delegation(cls,
                        context: 'IconScoreContext',
                        address: 'Address') -> dict:

        account: 'Account' = context.storage.icx.get_account(context, address, Intent.ALL)
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
    def _iscore_to_icx(cls,
                       iscore: int) -> int:
        """Exchange iscore to icx

        10 ** -18 icx == 1 loop == 1000 iscore

        :param iscore:
        :return: icx
        """
        return iscore // ISCORE_EXCHANGE_RATE

    def handle_claim_iscore(self,
                            context: 'IconScoreContext',
                            _params: dict):
        """Handles claimIScore JSON-RPC request

        :param context:
        :param _params:
        :return:
        """
        Logger.debug(tag=_TAG, msg=f"handle_claim_iscore() start")

        iscore, block_height = self._claim_iscore(context)

        if iscore > 0:
            self._commit_claim(context, iscore)

        else:
            Logger.info(tag=_TAG, msg="I-Score is zero")

        Logger.debug(tag=_TAG, msg="handle_claim_iscore() end")

    def _claim_iscore(self, context: 'IconScoreContext') -> (int, int):
        address: 'Address' = context.tx.origin
        block: 'Block' = context.block

        if context.type == IconScoreContextType.INVOKE:
            iscore, block_height = self._reward_calc_proxy.claim_iscore(
                address, block.height, block.hash)
        else:
            # For debug_estimateStep request
            iscore, block_height = 0, 0

        return iscore, block_height

    def _commit_claim(self, context: 'IconScoreContext', iscore: int):
        address: 'Address' = context.tx.origin
        block: 'Block' = context.block
        success = True

        try:
            icx: int = self._iscore_to_icx(iscore)

            from_account: 'Account' = context.storage.icx.get_account(context, address)
            treasury_address: 'Address' = context.storage.icx.fee_treasury
            treasury_account: 'Account' = context.storage.icx.get_account(context, treasury_address)

            treasury_account.withdraw(icx)
            from_account.deposit(icx)
            context.storage.icx.put_account(context, treasury_account)
            context.storage.icx.put_account(context, from_account)

            EventLogEmitter.emit_event_log(
                context,
                score_address=ZERO_SCORE_ADDRESS,
                event_signature="IScoreClaimed(int,int)",
                arguments=[iscore, icx],
                indexed_args_count=0
            )
        except BaseException as e:
            Logger.exception(tag=_TAG, msg=str(e))
            success = False
            raise e
        finally:
            self._reward_calc_proxy.commit_claim(success, address, block.height, block.hash)

    def handle_query_iscore(self,
                            _context: 'IconScoreContext',
                            params: dict) -> dict:
        ret_params: dict = TypeConverter.convert(params, ParamType.IISS_QUERY_ISCORE)
        address: 'Address' = ret_params[ConstantKeys.ADDRESS]

        # TODO: error handling
        iscore, block_height = self._reward_calc_proxy.query_iscore(address)

        data = {
            "iscore": iscore,
            "estimatedICX": self._iscore_to_icx(iscore),
            "blockHeight": block_height
        }

        return data

    def update_db(self,
                  context: 'IconScoreContext',
                  term: Optional['Term'],
                  prev_block_generator: Optional['Address'],
                  prev_block_votes: Optional[List[Tuple['Address', int]]],
                  flag: 'PrecommitFlag'):

        # every block time
        self._put_block_produce_info_to_rc_db(context, prev_block_generator, prev_block_votes)

        if not self._is_iiss_calc(flag):
            # In-term P-Rep replacement
            if term:
                self._put_gv(context, term)
                self._put_preps_to_rc_db(context, term)
            return

        # every term
        self._put_last_calc_info(context)
        self._put_end_calc_block_height(context)

        self._put_header_to_rc_db(context)
        self._put_gv(context, term)
        self._put_preps_to_rc_db(context, term)

    def send_ipc(self,
                 context: 'IconScoreContext',
                 precommit_data: 'PrecommitData'):
        block_height: int = precommit_data.block.height

        # every block time
        self._reward_calc_proxy.commit_block(True, block_height, precommit_data.block.hash)

        if not self._is_iiss_calc(precommit_data.precommit_flag):
            return

        path: str = context.storage.rc.create_db_for_calc(block_height)
        context.storage.rc.put_version_and_revision(precommit_data.revision)
        self._reward_calc_proxy.calculate(path, block_height)

    @classmethod
    def _is_iiss_calc(cls,
                      flag: 'PrecommitFlag') -> bool:
        return bool(flag & (PrecommitFlag.GENESIS_IISS_CALC | PrecommitFlag.IISS_CALC))

    @classmethod
    def _check_update_calc_period(cls,
                                  context: 'IconScoreContext') -> bool:
        block_height: int = context.block.height
        check_end_block_height: Optional[int] = context.storage.iiss.get_end_block_height_of_calc(context)
        if check_end_block_height is None:
            return False

        return block_height == check_end_block_height

    @classmethod
    def _put_last_calc_info(cls,
                            context: 'IconScoreContext'):

        _, last_calc_end = context.storage.meta.get_last_calc_info(context)
        if last_calc_end > 0:
            start: int = last_calc_end + 1
            end: int = context.block.height
        else:
            # first
            start: int = -1
            end: int = context.block.height
        context.storage.meta.put_last_calc_info(context,
                                                start,
                                                end)

    @classmethod
    def _put_end_calc_block_height(cls,
                                   context: 'IconScoreContext'):
        calc_period: int = context.storage.iiss.get_calc_period(context)
        if calc_period is None:
            raise InvalidParamsException("Fail put next calc block height: didn't init yet")
        context.storage.iiss.put_end_block_height_of_calc(context, context.block.height + calc_period)

    @classmethod
    def _put_header_to_rc_db(cls,
                             context: 'IconScoreContext'):
        version: int = context.storage.rc.current_version
        revision: int = context.storage.rc.current_revision
        data: 'Header' = RewardCalcDataCreator.create_header(version, context.block.height, revision)
        context.storage.rc.put(context.rc_block_batch, data)

    @classmethod
    def _put_gv(cls,
                context: 'IconScoreContext',
                term: Optional['Term']):

        """
            we should divide logic that case updated term during normal term.
            because updated term(only changed preps and total_delegated)
            must be changed by using determined term before.
        """
        if term is None:
            # Prevoting
            current_total_supply: int = context.storage.icx.get_total_supply(context)
            current_total_prep_delegated: int = context.preps.total_delegated
        else:
            # Decentralization
            current_total_supply: int = term.total_supply
            current_total_prep_delegated: int = term.total_delegated

        reward_rate: 'RewardRate' = context.storage.iiss.get_reward_rate(context)
        reward_prep: int = IssueFormula.calculate_rrep(context.storage.iiss.reward_min,
                                                       context.storage.iiss.reward_max,
                                                       context.storage.iiss.reward_point,
                                                       current_total_supply,
                                                       current_total_prep_delegated)

        reward_rate.reward_prep = reward_prep
        irep: int = term.irep if term is not None else 0
        calculated_irep: int = IssueFormula.calculate_irep_per_block_contributor(irep)

        reward_prep_for_rc = IssueFormula.calculate_temporary_reward_prep(reward_prep)

        # todo: versioning at this point?
        # end block height of term
        version: int = context.storage.rc.current_version
        data: 'GovernanceVariable' = RewardCalcDataCreator.create_gv_variable(version,
                                                                              context.block.height,
                                                                              calculated_irep,
                                                                              reward_prep_for_rc,
                                                                              context.main_prep_count,
                                                                              context.main_and_sub_prep_count)
        context.storage.iiss.put_reward_rate(context, reward_rate)
        context.storage.rc.put(context.rc_block_batch, data)

    @classmethod
    def _put_block_produce_info_to_rc_db(cls,
                                         context: 'IconScoreContext',
                                         prev_block_generator: Optional['Address'] = None,
                                         prev_block_votes: Optional[List[Tuple['Address', int]]] = None):
        """Called on every block

        :param context:
        :param prev_block_generator:
        :param prev_block_votes:
        :return:
        """
        if prev_block_generator is None or prev_block_votes is None:
            return

        Logger.debug(f"put_block_produce_info_for_rc", "iiss")
        data: 'BlockProduceInfoData' = RewardCalcDataCreator.create_block_produce_info_data(context.block.height,
                                                                                            prev_block_generator,
                                                                                            prev_block_votes)
        context.storage.rc.put(context.rc_block_batch, data)

    @classmethod
    def _put_preps_to_rc_db(cls,
                            context: 'IconScoreContext',
                            term: Optional['Term']):
        # if not decentralized, term is None.
        if not context.is_decentralized():
            return

        Logger.debug(
            tag=cls.TAG,
            msg="_put_preps_for_rc_db() start: "
                f"total_elected_prep_delegated={term.total_elected_prep_delegated}")

        data: 'PRepsData' = RewardCalcDataCreator.create_prep_data(
            context.block.height, term.total_elected_prep_delegated, term.preps)
        context.storage.rc.put(context.rc_block_batch, data)
