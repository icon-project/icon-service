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

from typing import TYPE_CHECKING, Optional

from iconcommons import Logger

from .issue_formula import IssueFormula
from .regulator import Regulator
from ... import SYSTEM_SCORE_ADDRESS
from ...base.ComponentBase import EngineBase
from ...base.exception import (
    OutOfBalanceException,
    InvalidParamsException,
    InternalServiceErrorException,
)
from ...icon_constant import ISSUE_CALCULATE_ORDER, ISSUE_EVENT_LOG_MAPPER, IssueDataKey, ICX_LOG_TAG, Revision
from ...iconscore.icon_score_event_log import EventLogEmitter

if TYPE_CHECKING:
    from ...iconscore.icon_score_context import IconScoreContext
    from ...base.address import Address
    from ...icx.icx_account import Account


class Engine(EngineBase):

    def __init__(self):
        super().__init__()

        self._formula: Optional['IssueFormula'] = None

    def open(self, context: 'IconScoreContext'):
        self._formula = IssueFormula(context.main_prep_count)

    def create_icx_issue_info(self, context: 'IconScoreContext') -> dict:
        irep: int = context.engine.prep.term.irep
        iiss_data_for_issue = {
            IssueDataKey.PREP: {
                IssueDataKey.IREP: irep,
                IssueDataKey.RREP: context.storage.iiss.get_reward_rate(context).reward_prep,
                IssueDataKey.TOTAL_DELEGATION: context.preps.total_delegated
            }
        }
        total_issue_amount = 0
        for group in iiss_data_for_issue:
            issue_amount_per_group = self._formula.calculate(context, group, iiss_data_for_issue[group])
            iiss_data_for_issue[group][IssueDataKey.VALUE] = issue_amount_per_group
            total_issue_amount += issue_amount_per_group

        context.regulator = Regulator(context, total_issue_amount)

        iiss_data_for_issue[IssueDataKey.ISSUE_RESULT] = {
            IssueDataKey.COVERED_BY_FEE: context.regulator.covered_icx_by_fee,
            IssueDataKey.COVERED_BY_OVER_ISSUED_ICX: context.regulator.covered_icx_by_over_issue,
            IssueDataKey.ISSUE: context.regulator.corrected_icx_issue_amount
        }
        return iiss_data_for_issue

    @staticmethod
    def _issue(context: 'IconScoreContext',
               to: 'Address',
               amount: int):
        if amount > 0:
            to_account: 'Account' = context.storage.icx.get_account(context, to)
            to_account.deposit(amount)
            current_total_supply = context.storage.icx.get_total_supply(context)
            context.storage.icx.put_account(context, to_account)
            context.storage.icx.put_total_supply(context, current_total_supply + amount)
            Logger.info(f"Issue icx. amount: {amount} "
                        f"Total supply: {current_total_supply + amount} "
                        f"Treasury: {to_account.balance}", ICX_LOG_TAG)

    def issue(self,
              context: 'IconScoreContext',
              to_address: 'Address',
              issue_data: dict):
        assert isinstance(context.regulator, Regulator)

        self._issue(context, to_address, context.regulator.corrected_icx_issue_amount)
        context.regulator.put_regulate_variable(context)

        for group_key in ISSUE_CALCULATE_ORDER:
            if group_key not in issue_data:
                continue
            event_signature: str = ISSUE_EVENT_LOG_MAPPER[group_key]["event_signature"]
            data: list = [issue_data[group_key][data_key] for data_key in ISSUE_EVENT_LOG_MAPPER[group_key]["data"]]
            EventLogEmitter.emit_event_log(context,
                                           score_address=SYSTEM_SCORE_ADDRESS,
                                           event_signature=event_signature,
                                           arguments=data,
                                           indexed_args_count=0)

        EventLogEmitter.emit_event_log(context,
                                       score_address=SYSTEM_SCORE_ADDRESS,
                                       event_signature=ISSUE_EVENT_LOG_MAPPER[IssueDataKey.TOTAL]["event_signature"],
                                       arguments=[context.regulator.covered_icx_by_fee,
                                                  context.regulator.covered_icx_by_over_issue,
                                                  context.regulator.corrected_icx_issue_amount,
                                                  context.regulator.remain_over_issued_icx],
                                       indexed_args_count=0)

    @staticmethod
    def _burn(context: 'IconScoreContext', address: 'Address', amount: int) -> int:
        if context.revision >= Revision.BURN_V2_ENABLED.value:
            address = SYSTEM_SCORE_ADDRESS

        account: 'Account' = context.storage.icx.get_account(context, address)
        if account.balance < amount:
            raise OutOfBalanceException(
                f'Not enough icx to burn: '
                f'balance({account.balance}) < icx_to_burn({amount})'
            )

        old_total_supply: int = context.storage.icx.get_total_supply(context)
        new_total_supply = old_total_supply - amount
        if new_total_supply < 0:
            raise InternalServiceErrorException(
                "Failed to burn icx: "
                f"total_supply({old_total_supply}) < icx_to_burn({amount})"
            )

        account.withdraw(amount)
        context.storage.icx.put_account(context, account)
        context.storage.icx.put_total_supply(context, new_total_supply)

        # Verify whether total_supply decreased by amount
        total_supply: int = context.storage.icx.get_total_supply(context)
        if total_supply != new_total_supply:
            raise InternalServiceErrorException(
                f"Failed to burn icx: new_total_supply={total_supply} "
                f"old_total_supply={old_total_supply} "
                f"icx_to_burn={amount}"
            )

        return new_total_supply

    def burn(self, context: 'IconScoreContext', address: 'Address', amount: int):
        """

        :param context:
        :param address: The address to burn ICX
        :param amount: the amount of ICX to burn
        :return:
        """
        revision: int = context.revision

        if revision >= Revision.BURN_V2_ENABLED.value and amount <= 0:
            raise InvalidParamsException(f"Invalid amount: {amount}")

        new_total_supply: int = self._burn(context, address, amount)
        self._log_burn_event(context, address, amount, new_total_supply)

    @staticmethod
    def _log_burn_event(
            context: 'IconScoreContext', address: 'Address', amount: int, new_total_supply: int):
        revision = context.revision

        # Event signature
        if revision < Revision.FIX_BURN_EVENT_SIGNATURE.value:
            event_sig = "ICXBurned"
        elif revision < Revision.BURN_V2_ENABLED.value:
            event_sig = "ICXBurned(int)"
        else:
            # 0: Who burns ICX
            # 1: The amount of ICX to burn
            # 2: New total supply
            event_sig = "ICXBurnedV2(Address,int,int)"

        # Arguments
        if revision < Revision.BURN_V2_ENABLED.value:
            arguments = [amount]
            indexed_args_count = 0
        else:
            arguments = [address, amount, new_total_supply]
            indexed_args_count = 1

        # Log event
        EventLogEmitter.emit_event_log(
            context,
            score_address=SYSTEM_SCORE_ADDRESS,
            event_signature=event_sig,
            arguments=arguments,
            indexed_args_count=indexed_args_count
        )
