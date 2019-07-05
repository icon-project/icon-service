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
from typing import Tuple

from iconservice.base.type_converter import TypeConverter
from iconservice.icon_constant import BASE_TRANSACTION_VERSION
from iconservice.icx.issue.regulator import Regulator
from iconservice.utils.hashing.hash_generator import HashGenerator


class BaseTransactionCreator(object):
    @staticmethod
    def create_issue_data(context: 'IconScoreContext') -> Tuple[dict, 'Regulator']:
        issue_data, total_issue_amount = context.engine.issue.create_icx_issue_info(context)
        regulator = Regulator()
        regulator.set_corrected_issue_data(context, total_issue_amount)

        issue_data["result"] = {
            "coveredByFee": regulator.covered_icx_by_fee,
            "coveredByOverIssuedICX": regulator.covered_icx_by_over_issue,
            "issue": regulator.corrected_icx_issue_amount
        }
        return issue_data, regulator

    @staticmethod
    def create_base_transaction(context: 'IconScoreContext') -> Tuple[dict, 'Regulator']:
        issue_data, regulator = BaseTransactionCreator.create_issue_data(context)
        # todo: check about reverse
        params = {
            "version": BASE_TRANSACTION_VERSION,
            "timestamp": context.block.timestamp,
            "dataType": "base",
            "data": issue_data
        }
        # todo: tests about tx hash
        params["txHash"] = BaseTransactionCreator._generate_transaction_hash(params)

        transaction = {
            "method": "icx_sendTransaction",
            "params": params
        }
        return transaction, regulator

    @staticmethod
    def _generate_transaction_hash(transaction_params: dict) -> str:
        copied_transaction_params = deepcopy(transaction_params)
        converted_transaction_params = TypeConverter.convert_type_reverse(copied_transaction_params)
        return HashGenerator.generate_hash(converted_transaction_params)
