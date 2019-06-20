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
from typing import TYPE_CHECKING, Tuple

from .regulator import Regulator
from ... import ZERO_SCORE_ADDRESS, Address
from ...base.ComponentBase import EngineBase
from ...icon_constant import ISSUE_CALCULATE_ORDER, ISSUE_EVENT_LOG_MAPPER, IssueDataKey
from ...iconscore.icon_score_event_log import EventLog
from ...iiss.issue_formula import IssueFormula

if TYPE_CHECKING:
    from ...iconscore.icon_score_context import IconScoreContext


class Engine(EngineBase):

    def __init__(self):
        super().__init__()

        self._formula: 'IssueFormula' = None

    def open(self, context: 'IconScoreContext'):
        self._formula = IssueFormula()

    def create_icx_issue_info(self, context: 'IconScoreContext') -> Tuple[dict, int]:
        incentive_rep: int = context.engine.prep.term.incentive_rep
        iiss_data_for_issue = {
            "prep": {
                "incentive": incentive_rep,
                "rewardRate": context.storage.iiss.get_reward_prep(context).reward_rate,
                "totalDelegation": context.storage.iiss.get_total_prep_delegated(context)
            }
        }
        total_issue_amount = 0
        for group in iiss_data_for_issue:
            issue_amount_per_group = self._formula.calculate(group, iiss_data_for_issue[group])
            iiss_data_for_issue[group]["value"] = issue_amount_per_group
            total_issue_amount += issue_amount_per_group

        return iiss_data_for_issue, total_issue_amount

    @staticmethod
    def _issue(context: 'IconScoreContext',
               to: 'Address',
               amount: int):
        if amount > 0:
            to_account = context.storage.icx.get_account(context, to)
            to_account.deposit(amount)
            current_total_supply = context.storage.icx.get_total_supply(context)
            context.storage.icx.put_account(context, to_account)
            context.storage.icx.put_total_supply(context, current_total_supply + amount)

    @staticmethod
    def _create_issue_event_log(group_key: str, issue_data_in_db: dict) -> 'EventLog':
        indexed: list = ISSUE_EVENT_LOG_MAPPER[group_key]["indexed"]
        data: list = [issue_data_in_db[group_key][data_key] for data_key in ISSUE_EVENT_LOG_MAPPER[group_key]["data"]]
        event_log: 'EventLog' = EventLog(ZERO_SCORE_ADDRESS, indexed, data)

        return event_log

    @staticmethod
    def _create_total_issue_amount_event_log(deducted_over_issued_icx: int,
                                             deducted_fee: int,
                                             remain_over_issued_icx: int,
                                             total_issue_amount: int) -> 'EventLog':
        total_issue_indexed: list = ISSUE_EVENT_LOG_MAPPER[IssueDataKey.TOTAL]["indexed"]
        total_issue_data: list = [deducted_fee, deducted_over_issued_icx, remain_over_issued_icx, total_issue_amount]
        total_issue_event_log: 'EventLog' = EventLog(ZERO_SCORE_ADDRESS, total_issue_indexed, total_issue_data)
        return total_issue_event_log

    def issue(self,
              context: 'IconScoreContext',
              to_address: 'Address',
              issue_data: dict,
              regulator: 'Regulator'):

        # todo: fee TBD
        fee = 0
        self._issue(context, to_address, regulator.corrected_icx_issue_amount)
        regulator.put_regulate_variable(context)

        for group_key in ISSUE_CALCULATE_ORDER:
            if group_key not in issue_data:
                continue
            issue_event_log: 'EventLog' = self._create_issue_event_log(group_key, issue_data)
            context.event_logs.append(issue_event_log)

        total_issue_event_log: 'EventLog' = \
            self._create_total_issue_amount_event_log(regulator.deducted_icx,
                                                      fee,
                                                      regulator.remain_over_issued_icx,
                                                      regulator.corrected_icx_issue_amount)
        context.event_logs.append(total_issue_event_log)
