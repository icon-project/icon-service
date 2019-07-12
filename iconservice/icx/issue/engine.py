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

from typing import TYPE_CHECKING, Tuple, Optional

from .issue_formula import IssueFormula
from .regulator import Regulator
from ... import ZERO_SCORE_ADDRESS
from ...base.ComponentBase import EngineBase
from ...base.exception import OutOfBalanceException
from ...icon_constant import ISSUE_CALCULATE_ORDER, ISSUE_EVENT_LOG_MAPPER, IssueDataKey
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
        self._formula = IssueFormula()

    def create_icx_issue_info(self, context: 'IconScoreContext') -> Tuple[dict, 'Regulator']:
        irep: int = context.engine.prep.term.irep
        iiss_data_for_issue = {
            IssueDataKey.PREP: {
                IssueDataKey.IREP: irep,
                IssueDataKey.RREP: context.storage.iiss.get_reward_rate(context).reward_prep,
                IssueDataKey.TOTAL_DELEGATION: context.preps.total_prep_delegated
            }
        }
        total_issue_amount = 0
        for group in iiss_data_for_issue:
            issue_amount_per_group = self._formula.calculate(group, iiss_data_for_issue[group])
            iiss_data_for_issue[group][IssueDataKey.VALUE] = issue_amount_per_group
            total_issue_amount += issue_amount_per_group

        regulator = Regulator(context, total_issue_amount)

        iiss_data_for_issue[IssueDataKey.ISSUE_RESULT] = {
            IssueDataKey.COVERED_BY_FEE: regulator.covered_icx_by_fee,
            IssueDataKey.COVERED_BY_OVER_ISSUED_ICX: regulator.covered_icx_by_over_issue,
            IssueDataKey.ISSUE: regulator.corrected_icx_issue_amount
        }
        return iiss_data_for_issue, regulator

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

    def issue(self,
              context: 'IconScoreContext',
              to_address: 'Address',
              issue_data: dict,
              regulator: 'Regulator'):
        assert isinstance(regulator, Regulator)

        self._issue(context, to_address, regulator.corrected_icx_issue_amount)
        regulator.put_regulate_variable(context)

        for group_key in ISSUE_CALCULATE_ORDER:
            if group_key not in issue_data:
                continue
            event_signature: str = ISSUE_EVENT_LOG_MAPPER[group_key]["event_signature"]
            data: list = [issue_data[group_key][data_key] for data_key in ISSUE_EVENT_LOG_MAPPER[group_key]["data"]]
            EventLogEmitter.emit_event_log(context,
                                           score_address=ZERO_SCORE_ADDRESS,
                                           event_signature=event_signature,
                                           arguments=data,
                                           indexed_args_count=0)

        EventLogEmitter.emit_event_log(context,
                                       score_address=ZERO_SCORE_ADDRESS,
                                       event_signature=ISSUE_EVENT_LOG_MAPPER[IssueDataKey.TOTAL]["event_signature"],
                                       arguments=[regulator.covered_icx_by_fee,
                                                  regulator.covered_icx_by_over_issue,
                                                  regulator.corrected_icx_issue_amount,
                                                  regulator.remain_over_issued_icx],
                                       indexed_args_count=0)

    @staticmethod
    def _burn(context: 'IconScoreContext', address: 'Address', amount: int):
        to_account: 'Account' = context.storage.icx.get_account(context, address)
        if to_account.balance < amount:
            raise OutOfBalanceException(f'Not enough ICX to Burn: '
                                        f'balance({to_account.balance }) < intended burn amount({amount})')
        else:
            to_account.withdraw(amount)
            current_total_supply = context.storage.icx.get_total_supply(context)
            context.storage.icx.put_total_supply(context, current_total_supply - amount)

    def burn(self, context: 'IconScoreContext', address: 'Address', amount: int):
        self._burn(context, address, amount)
        EventLogEmitter.emit_event_log(context,
                                       score_address=ZERO_SCORE_ADDRESS,
                                       event_signature="ICXBurned",
                                       arguments=[amount],
                                       indexed_args_count=0)

    def get_limit_inflation_beta(self, expected_irep: int) -> int:
        return self._formula.get_limit_inflation_beta(expected_irep)
