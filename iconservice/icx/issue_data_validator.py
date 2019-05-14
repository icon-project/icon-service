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

from typing import Any

from ..base.exception import IllegalFormatException


class IssueDataValidator:
    @staticmethod
    def validate_format(tx_data: dict, db_data: dict):
        try:
            if not tx_data.keys() == db_data.keys():
                raise IllegalFormatException("invalid issue transaction format")
        except AttributeError:
            raise IllegalFormatException("invalid issue transaction format")

        for key, val in db_data.items():
            if isinstance(val, dict):
                IssueDataValidator.validate_format(tx_data[key], db_data[key])

    @staticmethod
    def validate_value(issue_data_in_tx: dict,
                       issue_data_in_db: dict) -> bool:
        return issue_data_in_tx != issue_data_in_db
