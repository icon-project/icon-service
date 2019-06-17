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

from .regulator import Regulator
from ... import ZERO_SCORE_ADDRESS, Address
from ...base.ComponentBase import EngineBase
from ...base.exception import InvalidParamsException
from ...icon_constant import ISSUE_CALCULATE_ORDER, ISSUE_EVENT_LOG_MAPPER, IssueDataKey
from ...iconscore.icon_score_event_log import EventLog
from ...icx.issue_data_validator import IssueDataValidator

if TYPE_CHECKING:
    from ...iconscore.icon_score_context import IconScoreContext


class Engine(EngineBase):
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
              prev_calc_period_issued_i_score: Optional[int],
              issue_data_in_tx: dict,
              issue_data_in_db: dict):
        total_issue_amount = 0

        for group_key in ISSUE_CALCULATE_ORDER:
            if group_key not in issue_data_in_db:
                continue

            if IssueDataValidator. \
                    validate_value(issue_data_in_tx[group_key], issue_data_in_db[group_key]):
                raise InvalidParamsException("Have difference between "
                                             "issue transaction and actual db data")
            issue_event_log: 'EventLog' = self._create_issue_event_log(group_key, issue_data_in_db)
            context.event_logs.append(issue_event_log)

            total_issue_amount += issue_data_in_db[group_key]["value"]

        calc_next_block_height = context.storage.iiss.get_calc_next_block_height(context)

        if calc_next_block_height == context.block.height:
            deducted_icx, remain_over_issued_icx, corrected_icx_issue_amount = \
                Regulator.correct_issue_amount_on_calc_period(context,
                                                              prev_calc_period_issued_i_score,
                                                              total_issue_amount)
        else:
            deducted_icx, remain_over_issued_icx, corrected_icx_issue_amount = \
                Regulator.correct_issue_amount(context, total_issue_amount)

        self._issue(context, to_address, corrected_icx_issue_amount)
        # todo: implement diff, fee event log
        # todo: hard corded fee data, will be removed
        fee = 0
        total_issue_event_log: 'EventLog' = self._create_total_issue_amount_event_log(corrected_icx_issue_amount,
                                                                                      fee,
                                                                                      deducted_icx,
                                                                                      remain_over_issued_icx)
        context.event_logs.append(total_issue_event_log)
