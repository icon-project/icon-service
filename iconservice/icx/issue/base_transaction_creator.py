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

from copy import deepcopy
from typing import TYPE_CHECKING

from ...base.type_converter import TypeConverter
from ...icon_constant import BASE_TRANSACTION_VERSION
from ...utils.hashing.hash_generator import HashGenerator

if TYPE_CHECKING:
    from ...iconscore.icon_score_context import IconScoreContext


class BaseTransactionCreator(object):
    @staticmethod
    def create_base_transaction(context: 'IconScoreContext') -> dict:
        issue_data: dict = context.engine.issue.create_icx_issue_info(context)
        params = {
            "version": BASE_TRANSACTION_VERSION,
            "timestamp": context.block.timestamp,
            "dataType": "base",
            "data": issue_data
        }
        params["txHash"]: bytes = BaseTransactionCreator._generate_transaction_hash(params)

        transaction = {
            "method": "icx_sendTransaction",
            "params": params
        }
        return transaction

    @staticmethod
    def _generate_transaction_hash(transaction_params: dict) -> bytes:
        copied_transaction_params: dict = deepcopy(transaction_params)
        converted_transaction_params: dict = TypeConverter.convert_type_reverse(copied_transaction_params)
        return HashGenerator.generate_hash(converted_transaction_params)
