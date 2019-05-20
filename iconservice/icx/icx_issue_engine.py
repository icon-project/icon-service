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

from typing import TYPE_CHECKING

from iconservice import ZERO_SCORE_ADDRESS, Address
from iconservice.base.exception import IconServiceBaseException
from iconservice.icon_constant import ISSUE_CALCULATE_ORDER, ISSUE_EVENT_LOG_MAPPER, IssueDataKey
from iconservice.iconscore.icon_score_event_log import EventLog
from iconservice.icx.issue_data_checker import IssueDataValidator

if TYPE_CHECKING:
    from ..iconscore.icon_score_context import IconScoreContext
    from ..icx.icx_storage import IcxStorage


class IcxIssueEngine:
    def __init__(self):
        self._storage: 'IcxStorage' = None

    def open(self, storage: 'IcxStorage'):
        self.close()
        self._storage = storage

    def close(self) -> None:
        """Close resources
        """
        if self._storage:
            self._storage.close(context=None)
            self._storage = None

    def _issue(self,
               context: 'IconScoreContext',
               to: Address,
               amount: int):
        assert amount > 0

        if amount > 0:
            to_account = self._storage.get_account(context, to)
            to_account.deposit(amount)
            current_total_supply = context.total_supply
            total_supply_after_issuing = current_total_supply + amount

            self._storage.put_account(context, to_account)
            self._storage.put_total_supply(context, total_supply_after_issuing)
            context.total_supply = total_supply_after_issuing

    @staticmethod
    def _create_issue_event_log(group_key, issue_data_in_db) -> 'EventLog':
        indexed = ISSUE_EVENT_LOG_MAPPER[group_key]["indexed"]
        data = [issue_data_in_db[group_key][data_key] for data_key in ISSUE_EVENT_LOG_MAPPER[group_key]["data"]]
        event_log = EventLog(ZERO_SCORE_ADDRESS, indexed, data)

        return event_log

    @staticmethod
    def _create_total_issue_amount_event_log(total_issue_amount) -> 'EventLog':
        total_issue_indexed = ISSUE_EVENT_LOG_MAPPER[IssueDataKey.TOTAL]["indexed"]
        total_issue_data = [total_issue_amount]
        total_issue_event_log = EventLog(ZERO_SCORE_ADDRESS, total_issue_indexed, total_issue_data)
        return total_issue_event_log

    def iiss_issue(self,
                   context: 'IconScoreContext',
                   to_address: 'Address',
                   issue_data_in_tx: dict,
                   issue_data_in_db: dict):
        total_issue_amount = 0

        for group_key in ISSUE_CALCULATE_ORDER:
            if group_key not in issue_data_in_db:
                continue

            if IssueDataValidator. \
                    check_difference_of_iiss_issue_data_value(issue_data_in_tx[group_key], issue_data_in_db[group_key]):
                raise IconServiceBaseException("Have difference between "
                                               "issue transaction and actual db data")
            issue_event_log = self._create_issue_event_log(group_key, issue_data_in_db)
            context.event_logs.append(issue_event_log)

            total_issue_amount += issue_data_in_db[group_key]["value"]

        # todo : issue amount = total_issue_amount - prev total transaction fee
        # to_address: Address to be deposited
        self._issue(context, to_address, total_issue_amount)
        total_issue_event_log = self._create_total_issue_amount_event_log(total_issue_amount)
        context.event_logs.append(total_issue_event_log)
