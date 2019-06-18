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
from collections import namedtuple
from typing import TYPE_CHECKING, Optional, Tuple

from iconservice.iiss.issue_formula import IssueFormula
from .regulator import Regulator
from ... import ZERO_SCORE_ADDRESS, Address
from ...base.ComponentBase import EngineBase
from ...base.exception import InvalidParamsException
from ...icon_constant import ISSUE_CALCULATE_ORDER, ISSUE_EVENT_LOG_MAPPER, IssueDataKey
from ...iconscore.icon_score_event_log import EventLog
from ...icx.issue_data_validator import IssueDataValidator

if TYPE_CHECKING:
    from ...iconscore.icon_score_context import IconScoreContext

CorrectedIssueInfo = namedtuple('CorrectedIssueInfo',
                                'deducted_icx, remain_over_issued_icx, corrected_icx_issue_amount')


class Engine(EngineBase):
    def __init__(self):
        super().__init__()

        self._formula: 'IssueFormula' = None
        # todo: naming
        self._corrected_issue_info = {}

    def open(self, context: 'IconScoreContext', path: str):
        self._formula = IssueFormula()

    def clear(self):
        self._corrected_issue_info.clear()

    def _create_icx_issue_info(self, context: 'IconScoreContext') -> Tuple[dict, int]:
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

    def calculate_corrected_issue_amount(self, context: 'IconScoreContext') -> dict:
        issue_data, total_issue_amount = self._create_icx_issue_info(context)
        calc_next_block_height = context.storage.iiss.get_calc_next_block_height(context)

        # todo: should consider raising error about no response
        if calc_next_block_height == context.block.height:
            i_score: Optional[int] = context.storage.rc.get_prev_calc_period_issued_i_score()
            deducted_icx, remain_over_issued_icx, corrected_icx_issue_amount = \
                Regulator.correct_issue_amount_on_calc_period(context,
                                                              i_score,
                                                              total_issue_amount)
        else:
            deducted_icx, remain_over_issued_icx, corrected_icx_issue_amount = \
                Regulator.correct_issue_amount(context, total_issue_amount)
        self._corrected_issue_info[context.tx.hash] = \
            CorrectedIssueInfo(deducted_icx, remain_over_issued_icx, corrected_icx_issue_amount)
        # todo: fee
        fee = 10
        issue_data["result"] = {
            "deductedFromFee": fee,
            "deductedFromOverIssuedICX": deducted_icx - fee,
            "issue": corrected_icx_issue_amount
        }

        return issue_data



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
    def _create_total_issue_amount_event_log(total_issue_amount: int,
                                             deducted_fee: int,
                                             deducted_over_issued_icx: int,
                                             remain_over_issued_icx: int) -> 'EventLog':
        total_issue_indexed: list = ISSUE_EVENT_LOG_MAPPER[IssueDataKey.TOTAL]["indexed"]
        total_issue_data: list = [deducted_fee, deducted_over_issued_icx, remain_over_issued_icx, total_issue_amount]
        total_issue_event_log: 'EventLog' = EventLog(ZERO_SCORE_ADDRESS, total_issue_indexed, total_issue_data)
        return total_issue_event_log

    def issue(self,
              context: 'IconScoreContext',
              to_address: 'Address',
              issue_data: dict):

        for group_key in ISSUE_CALCULATE_ORDER:
            if group_key not in issue_data:
                continue
            issue_event_log: 'EventLog' = self._create_issue_event_log(group_key, issue_data)
            context.event_logs.append(issue_event_log)

        issue_info_for_eventlog: CorrectedIssueInfo = self._corrected_issue_info.pop(context.tx.hash)
        fee = issue_data["result"][""]
        self._issue(context, to_address, issue_info_for_eventlog.corrected_icx_issue_amount)

        total_issue_event_log: 'EventLog' = \
            self._create_total_issue_amount_event_log(issue_info_for_eventlog.corrected_icx_issue_amount,
                                                      fee,
                                                      issue_info_for_eventlog.deducted_icx,
                                                      issue_info_for_eventlog.remain_over_issued_icx)
        context.event_logs.append(total_issue_event_log)
