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

from iconservice.base.exception import IllegalFormatException

if TYPE_CHECKING:
    pass


class IssueDataValidator:

    @staticmethod
    def validate_iiss_issue_data_format(tx_data: dict, db_data: dict):
        # todo: need to refactoring (to recursive subroutine)
        sorted_db_data_keys = sorted(db_data.keys())
        if not sorted(tx_data.keys()) == sorted_db_data_keys:
            raise IllegalFormatException("invalid issue transaction format")

        for key in sorted_db_data_keys:
            diff_set = tx_data[key].keys() ^ db_data[key].keys()
            if not len(diff_set) == 0:
                raise IllegalFormatException("invalid issue transaction format")

    @staticmethod
    def check_difference_of_iiss_issue_data_value(issue_data_in_tx: dict,
                                                  issue_data_in_db: dict) -> bool:
        return issue_data_in_tx != issue_data_in_db
