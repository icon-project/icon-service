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

from iconservice.icx.icx_issue_storage import IcxIssueStorage
from .. import ZERO_SCORE_ADDRESS, Address
from ..base.exception import IconServiceBaseException
from ..icon_constant import ISSUE_CALCULATE_ORDER, ISSUE_EVENT_LOG_MAPPER, IssueDataKey
from ..iconscore.icon_score_event_log import EventLog
from ..icx.issue_data_validator import IssueDataValidator

if TYPE_CHECKING:
    from ..iconscore.icon_score_context import IconScoreContext
    from ..icx.icx_storage import IcxStorage


class IcxIssueEngine:
    _MAX_I_SCORE = 1_000

    def __init__(self):
        self._storage: 'IcxStorage' = None
        self._issue_storage: 'IcxIssueStorage' = None
        self._issued_amount_in_calc_period: int = 0
        self._prev_calc_period_total_issued_amount: int = 0

    def open(self, storage: 'IcxStorage'):
        self.close()
        self._storage = storage
        self._issue_storage = IcxIssueStorage(self._storage.db)
        self._issued_amount_in_calc_period = self._load_current_calc_period_issued_amount()
        self._prev_calc_period_total_issued_amount = self._load_prev_calc_period_total_issued_amount()

    def close(self):
        """Close resources
        """
        if self._storage:
            self._storage.close(context=None)
            self._storage = None

        if self._issue_storage:
            self._issue_storage.close(context=None)
            self._issue_storage = None

    def _issue(self,
               context: 'IconScoreContext',
               to: 'Address',
               amount: int):
        if amount == 0:
            return

        if amount > 0:
            to_account = self._storage.get_account(context, to)
            to_account.deposit(amount)
            current_total_supply = self._storage.get_total_supply(context)
            self._storage.put_account(context, to_account)
            self._storage.put_total_supply(context, current_total_supply + amount)

    def _load_current_calc_period_issued_amount(self) -> int:
        context = None
        return self._issue_storage.get_current_calc_period_issued_icx(context)

    def _load_prev_calc_period_total_issued_amount(self) -> int:
        context = None
        return self._issue_storage.get_current_calc_period_issued_icx(context)

    @staticmethod
    def _create_issue_event_log(group_key: str, issue_data_in_db: dict) -> 'EventLog':
        indexed: list = ISSUE_EVENT_LOG_MAPPER[group_key]["indexed"]
        data: list = [issue_data_in_db[group_key][data_key] for data_key in ISSUE_EVENT_LOG_MAPPER[group_key]["data"]]
        event_log: 'EventLog' = EventLog(ZERO_SCORE_ADDRESS, indexed, data)

        return event_log

    @staticmethod
    def _create_total_issue_amount_event_log(total_issue_amount: int) -> 'EventLog':
        total_issue_indexed: list = ISSUE_EVENT_LOG_MAPPER[IssueDataKey.TOTAL]["indexed"]
        total_issue_data: list = [total_issue_amount]
        total_issue_event_log: 'EventLog' = EventLog(ZERO_SCORE_ADDRESS, total_issue_indexed, total_issue_data)
        return total_issue_event_log

    def get_difference_between_icx_and_i_score(self, icx_amount, i_score_amount) -> int:
        diff = icx_amount * 1_000 - i_score_amount
        return diff

    # todo: consider name: issue_for_iiss
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
                raise IconServiceBaseException("Have difference between "
                                               "issue transaction and actual db data")
            issue_event_log: 'EventLog' = self._create_issue_event_log(group_key, issue_data_in_db)
            context.event_logs.append(issue_event_log)

            total_issue_amount += issue_data_in_db[group_key]["value"]

        current_calc_period_issued_amount = self._issue_storage.get_current_calc_period_issued_icx(context)
        current_calc_period_issued_amount += total_issue_amount

        # todo : iiss_engine 에 calc 주기를 넘겨주는 method를 생성하거나 variable property를 생성
        issue_variable = context.iiss_engine._variable.issue
        calc_next_block_height = issue_variable.get_calc_next_block_height(context)

        if calc_next_block_height == context.block.height:
            prev_calc_period_issued_amount: Optional[int] = self._issue_storage.get_prev_calc_period_issued_icx(context)
            if prev_calc_period_issued_i_score and prev_calc_period_issued_amount:
                prev_over_issued_icx = self._issue_storage.get_over_issued_icx(context)
                prev_over_issued_i_score = self._issue_storage.get_over_issued_i_score(context)

                current_over_issued_i_score = \
                    self.get_difference_between_icx_and_i_score(prev_calc_period_issued_amount,
                                                                prev_calc_period_issued_i_score)

                total_over_issued_i_score = current_over_issued_i_score + \
                                            prev_over_issued_icx * self._MAX_I_SCORE + prev_over_issued_i_score

                max_i_score = self._MAX_I_SCORE if total_over_issued_i_score >= 0 else -self._MAX_I_SCORE
                over_issued_icx = total_over_issued_i_score // max_i_score
                over_issued_i_score = total_over_issued_i_score % max_i_score

                # 현재 발행에 반영
                total_issue_amount -= over_issued_icx
                over_issued_icx = -total_issue_amount if total_issue_amount < 0 else 0

                self._issue_storage.put_over_issued_i_score(context, over_issued_i_score)
                self._issue_storage.put_over_issued_icx(context, over_issued_icx)

            elif not prev_calc_period_issued_i_score and prev_calc_period_issued_amount:
                # if prev_calc is exists, but not i score,
                raise Exception
            self._issue_storage.put_prev_calc_period_issued_icx(context, current_calc_period_issued_amount)
            current_calc_period_issued_amount = 0
        else:
            prev_over_issued_icx = self._issue_storage.get_over_issued_icx(context)
            if prev_over_issued_icx > 0:
                total_issue_amount -= prev_over_issued_icx
                if total_issue_amount < 0:
                    over_issued_icx = total_issue_amount
                    total_issue_amount = 0
                else:
                    over_issued_icx = 0
                self._issue_storage.put_over_issued_icx(context, over_issued_icx)

        # todo : issue amount = total_issue_amount - prev total transaction fee
        self._issue(context, to_address, total_issue_amount)
        self._issue_storage.put_current_calc_period_issued_icx(context, current_calc_period_issued_amount)
        # todo: implement diff, fee event log
        total_issue_event_log: 'EventLog' = self._create_total_issue_amount_event_log(total_issue_amount)
        context.event_logs.append(total_issue_event_log)
