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

from typing import TYPE_CHECKING, Any, Optional, List

from iconcommons.logger import Logger

from .reward_calc.data_creator import DataCreator as RewardCalcDataCreator
from .reward_calc.ipc.message import CalculateResponse, VersionResponse
from .reward_calc.ipc.reward_calc_proxy import RewardCalcProxy
from ..base.ComponentBase import EngineBase
from ..base.exception import InvalidParamsException
from ..base.type_converter import TypeConverter
from ..base.type_converter_templates import ConstantKeys, ParamType
from ..icon_constant import IISS_SOCKET_PATH, IISS_MAX_DELEGATIONS, ISCORE_EXCHANGE_RATE, ICON_SERVICE_LOG_TAG
from ..iconscore.icon_score_context import IconScoreContext
from ..iconscore.icon_score_event_log import EventLogEmitter
from ..icx import Intent
from ..icx.issue.issue_formula import IssueFormula

if TYPE_CHECKING:
    from ..precommit_data_manager import PrecommitData
    from ..base.address import Address, ZERO_SCORE_ADDRESS
    from ..icx.icx_account import Account
    from .reward_calc.msg_data import TxData, DelegationInfo, DelegationTx, Header, BlockProduceInfoData, PRepsData
    from .reward_calc.msg_data import GovernanceVariable
    from .storage import Reward
    from ..prep.data.prep import PRep


class Engine(EngineBase):

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

        self._reward_calc_proxy: 'RewardCalcProxy' = None

    def open(self, context: 'IconScoreContext', path: str):
        self._init_reward_calc_proxy(path)

    # TODO implement version callback function
    def version_callback(self, cb_data: 'VersionResponse'):
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

        self._put_stake_for_state_db(context, address, value)

    @classmethod
    def _put_stake_for_state_db(cls, context: 'IconScoreContext', address: 'Address', value: int):

        if not isinstance(value, int) or value < 0:
            raise InvalidParamsException('Failed to stake: value is not int type or value < 0')

        account: 'Account' = context.storage.icx.get_account(context, address, Intent.STAKE)
        unstake_lock_period = context.storage.iiss.get_unstake_lock_period(context)
        account.set_stake(value, unstake_lock_period)
        context.storage.icx.put_account(context, account)
        # TODO tx_result make if needs

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
            "stake": stake,
            "unstake": unstake,
            "unstakedBlockHeight": unstake_block_beight
        }
        return data

    def handle_set_delegation(self, context: 'IconScoreContext', params: dict):

        address: 'Address' = context.tx.origin
        ret_params: dict = TypeConverter.convert(params, ParamType.IISS_SET_DELEGATION)
        data: list = ret_params[ConstantKeys.DELEGATIONS]

        self._put_delegation_for_state_db(context, address, data)
        self._put_delegation_for_iiss_db(context, address, data)

    @classmethod
    def _put_delegation_for_state_db(cls,
                                     context: 'IconScoreContext',
                                     delegating_address: 'Address',
                                     delegations: list):

        if not isinstance(delegations, list):
            raise InvalidParamsException('Failed to delegation: delegations is not list type')

        if len(delegations) > IISS_MAX_DELEGATIONS:
            raise InvalidParamsException(f'Failed to delegation: Overflow Max Input List')

        delegating: 'Account' = context.storage.icx.get_account(context, delegating_address, Intent.DELEGATING)
        preps: dict = cls._make_preps(delegating.delegations, delegations)
        cls._set_delegations(delegating, preps)
        dirty_accounts: list = cls._delegated_preps(context, delegating, preps)
        dirty_accounts.append(delegating)

        for dirty_account in dirty_accounts:
            context.storage.icx.put_account(context, dirty_account)
            if dirty_account.address in context.preps:
                context.preps.update(dirty_account.address, dirty_account.delegated_amount)
        # TODO tx_result make if needs

    @classmethod
    def _make_preps(cls, old_delegations: list, new_delegations: list) -> dict:
        preps: dict = {}

        if old_delegations:
            for address, old in old_delegations:
                preps[address] = (old, 0)

        for delegation in new_delegations:
            address, new = delegation.values()
            if address in preps:
                old, _ = preps[address]
                preps[address] = (old, new)
            else:
                preps[address] = (0, new)
        return preps

    @classmethod
    def _set_delegations(cls, delegating: 'Account', preps: dict):
        new_delegations: list = [(address, new) for address, (before, new) in preps.items() if new > 0]
        delegating.set_delegations(new_delegations)

        if delegating.delegations_amount > delegating.stake:
            raise InvalidParamsException(
                f"Failed to delegation: delegation_amount{delegating.delegations_amount} > stake{delegating.stake}")

    @classmethod
    def _delegated_preps(cls, context: 'IconScoreContext', delegating: 'Account', preps: dict) -> list:
        dirty_accounts: list = []
        for address, (before, new) in preps.items():
            if address == delegating.address:
                prep: 'Account' = delegating
            else:
                prep: 'Account' = context.storage.icx.get_account(context, address, Intent.DELEGATED)
                dirty_accounts.append(prep)

            offset: int = new - before
            prep.update_delegated_amount(offset)

            if address in context.preps:
                total: int = context.storage.iiss.get_total_prep_delegated(context)
                context.storage.iiss.put_total_prep_delegated(context, total + offset)
        return dirty_accounts

    @classmethod
    def _put_delegation_for_iiss_db(cls, context: 'IconScoreContext', address: 'Address', delegations: list):

        delegation_list: list = []

        for delegation in delegations:
            delegation_address, delegation_value = delegation.values()
            info: 'DelegationInfo' = RewardCalcDataCreator.create_delegation_info(delegation_address, delegation_value)
            delegation_list.append(info)

        delegation_tx: 'DelegationTx' = RewardCalcDataCreator.create_tx_delegation(delegation_list)
        iiss_tx_data: 'TxData' = RewardCalcDataCreator.create_tx(address, context.block.height, delegation_tx)
        context.storage.rc.put(context.rc_block_batch, iiss_tx_data)

    def handle_get_delegation(self, context: 'IconScoreContext', params: dict) -> dict:

        ret_params: dict = TypeConverter.convert(params, ParamType.IISS_GET_STAKE)
        address: 'Address' = ret_params[ConstantKeys.ADDRESS]
        return self._get_delegation(context, address)

    @classmethod
    def _get_delegation(cls, context: 'IconScoreContext', address: 'Address') -> dict:

        account: 'Account' = context.storage.icx.get_account(context, address, Intent.DELEGATED)
        delegation_list: list = []
        for address, value in account.delegations:
            delegation_list.append({"address": address, "value": value})

        data = {
            "delegations": delegation_list,
            "totalDelegated": account.delegations_amount
        }

        return data

    @classmethod
    def _iscore_to_icx(cls, iscore: int) -> int:
        return iscore // ISCORE_EXCHANGE_RATE

    def handle_claim_iscore(self, context: 'IconScoreContext', params: dict):
        address: 'Address' = context.tx.origin

        # TODO: error handling
        iscore, block_height = self._reward_calc_proxy.claim_iscore(address, context.block.height, context.block.hash)

        icx: int = self._iscore_to_icx(iscore)

        from_account: 'Account' = context.storage.icx.get_account(context, address)
        from_account.deposit(icx)
        context.storage.icx.put_account(context, from_account)
        self._create_tx_result(context, iscore, icx)

    @classmethod
    def _create_tx_result(cls, context: 'IconScoreContext', iscore: int, icx: int):
        # make tx result
        event_signature: str = 'IScoreClaimed(int,int)'
        arguments = [iscore, icx]
        index = 0
        EventLogEmitter.emit_event_log(context, ZERO_SCORE_ADDRESS, event_signature, arguments, index)

    def handle_query_iscore(self, context: 'IconScoreContext', params: dict) -> dict:
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
                  is_first: bool):
        # every block time
        self._put_block_produce_info_for_rc(context, prev_block_generator, prev_block_validators)

        if not is_first and not self._check_update_calc_period(context):
            return

        self._put_next_calc_block_height(context)

        self._put_header_for_rc(context)
        self._put_gv(context)
        self._put_preps_for_rc(context)

    def send_ipc(self, context: 'IconScoreContext', precommit_data: 'PrecommitData', is_first: bool):
        block_height: int = precommit_data.block.height

        # every block time
        self._reward_calc_proxy.commit_block(True, block_height, precommit_data.block.hash)

        if not is_first and not self._check_update_calc_period(context):
            return

        path: str = context.storage.rc.create_db_for_calc(block_height)
        self._reward_calc_proxy.calculate(path, block_height)

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
    def _put_header_for_rc(cls, context: 'IconScoreContext'):
        data: 'Header' = RewardCalcDataCreator.create_header(0, context.block.height)
        context.storage.rc.put(context.rc_block_batch, data)

    @classmethod
    def _put_gv(cls, context: 'IconScoreContext'):
        current_total_supply = context.storage.icx.get_total_supply(context)
        current_total_prep_delegated = context.storage.iiss.get_total_prep_delegated(context)
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
    def _put_block_produce_info_for_rc(cls,
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
    def _put_preps_for_rc(cls, context: 'IconScoreContext'):
        preps: List['PRep'] = context.preps.get_preps()

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
