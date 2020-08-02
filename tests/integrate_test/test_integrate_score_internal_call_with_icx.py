# -*- coding: utf-8 -*-

# Copyright 2018 ICON Foundation
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

"""IconScoreEngine testcase
"""

import random
from typing import List, Tuple

from iconservice.base.address import Address
from iconservice.base.address import SYSTEM_SCORE_ADDRESS
from iconservice.base.exception import ExceptionCode
from iconservice.iconscore.icon_score_result import TransactionResult
from iconservice.iconscore.typing.conversion import base_object_to_str
from tests.integrate_test.test_integrate_base import TestIntegrateBase


class TestIntegrateScoreInternalCallWithIcx(TestIntegrateBase):

    SCORE_ROOT = "icx_method_chaining"

    def _deploy_sample_scores(self) -> Tuple[Address, Address]:
        sender = self._admin

        tx1: dict = self.create_deploy_score_tx(
            score_root=self.SCORE_ROOT,
            score_name="callee_score",
            from_=sender,
            to_=SYSTEM_SCORE_ADDRESS
        )

        tx2: dict = self.create_deploy_score_tx(
            score_root=self.SCORE_ROOT,
            score_name="caller_score",
            from_=sender,
            to_=SYSTEM_SCORE_ADDRESS
        )

        tx_results: List[TransactionResult] = self.process_confirm_block_tx([tx1, tx2])
        callee: Address = tx_results[0].score_address
        caller: Address = tx_results[1].score_address

        self.score_call(
            from_=sender,
            to_=caller,
            func_name="setCallee",
            params={"address": str(callee)}
        )

        return callee, caller

    def test_score_internal_call_with_icx(self):
        sender = self._admin
        callee, caller = self._deploy_sample_scores()

        call_info = (
            ("setBool", "getBool", True),
            ("setBytes", "getBytes", b"hello"),
            ("setInt", "getInt", 333),
            ("setStr", "getStr", "world"),
            ("setAddress", "getAddress", self._accounts[0].address),
        )

        amount = random.randint(1, 999)
        expected_callee_balance = 0
        for setter, getter, value in call_info:
            before_sender_balance: int = self.get_balance(sender)

            tx_results = self.score_call(
                from_=sender,
                to_=caller,
                value=amount,
                func_name=setter,
                params={"value": base_object_to_str(value)},
                expected_status=True
            )

            expected_callee_balance += amount
            fee: int = tx_results[0].step_price * tx_results[0].step_used

            assert self.get_balance(sender) == before_sender_balance - amount - fee
            assert self.get_balance(callee) == expected_callee_balance
            assert self.get_balance(caller) == 0

            ret = self.query_score(from_=sender, to_=callee, func_name=getter)
            assert ret == value

    def test_non_payable_internal_call(self):
        sender = self._admin
        callee, caller = self._deploy_sample_scores()
        amount = 100

        before_balance: int = self.get_balance(sender)

        tx_results = self.score_call(
            from_=sender,
            to_=caller,
            value=amount,
            func_name="func_with_non_payable_internal_call",
            expected_status=False
        )

        tx_result = tx_results[0]
        fee: int = tx_result.step_price * tx_result.step_used

        assert tx_result.failure.code == ExceptionCode.METHOD_NOT_PAYABLE
        assert self.get_balance(sender) == before_balance - fee

    def test_payable_internal_call(self):
        sender = self._admin
        callee, caller = self._deploy_sample_scores()
        amount = 100

        before_sender_balance: int = self.get_balance(sender)
        before_callee_balance: int = self.get_balance(callee)
        before_caller_balance: int = self.get_balance(caller)

        tx_results = self.score_call(
            from_=sender,
            to_=caller,
            value=amount,
            func_name="func_with_payable_internal_call",
            expected_status=True
        )

        tx_result = tx_results[0]
        fee: int = tx_result.step_price * tx_result.step_used

        assert self.get_balance(sender) == before_sender_balance - fee - amount
        assert self.get_balance(callee) == before_callee_balance + amount
        assert self.get_balance(caller) == before_caller_balance

    def test_non_payable_func_with_negative_icx_internal_call(self):
        sender = self._admin
        callee, caller = self._deploy_sample_scores()

        self.transfer_icx(from_=sender, to_=caller, value=100)

        tx_results = self.score_call(
            from_=sender,
            to_=caller,
            value=0,
            func_name="non_payable_func_with_icx_internal_call",
            params={"value": base_object_to_str(-77)},
            expected_status=False
        )

        tx_result = tx_results[0]
        assert tx_result.failure.code == ExceptionCode.INVALID_PARAMETER

    def test_non_payable_func_with_positive_icx_internal_call(self):
        sender = self._admin
        callee, caller = self._deploy_sample_scores()
        self.transfer_icx(from_=sender, to_=caller, value=1000)

        amount = random.randint(1, 499)
        before_sender_balance: int = self.get_balance(sender)
        before_caller_balance: int = self.get_balance(caller)
        before_callee_balance: int = self.get_balance(callee)

        # Caller will call a method of callee with amount icx
        tx_results = self.score_call(
            from_=sender,
            to_=caller,
            value=0,
            func_name="non_payable_func_with_icx_internal_call",
            params={"value": base_object_to_str(amount)},
            expected_status=True
        )

        tx_result = tx_results[0]
        fee: int = tx_result.step_price * tx_result.step_used

        assert self.get_balance(sender) == before_sender_balance - fee
        assert self.get_balance(caller) == before_caller_balance - amount
        assert self.get_balance(callee) == before_callee_balance + amount

    def test_non_payable_func_with_out_of_balance_internal_call(self):
        sender = self._admin
        callee, caller = self._deploy_sample_scores()
        self.transfer_icx(from_=sender, to_=caller, value=1000)

        amount = 2000
        before_sender_balance: int = self.get_balance(sender)
        before_caller_balance: int = self.get_balance(caller)
        before_callee_balance: int = self.get_balance(callee)

        # Caller will try to call a method of callee with icx
        # which is larger than caller owns
        # So this tx should occur out of balance exception
        tx_results = self.score_call(
            from_=sender,
            to_=caller,
            value=0,
            func_name="non_payable_func_with_icx_internal_call",
            params={"value": base_object_to_str(amount)},
            expected_status=False
        )

        tx_result = tx_results[0]
        assert tx_result.failure.code == ExceptionCode.OUT_OF_BALANCE

        fee: int = tx_result.step_price * tx_result.step_used

        assert self.get_balance(sender) == before_sender_balance - fee
        assert self.get_balance(caller) == before_caller_balance
        assert self.get_balance(callee) == before_callee_balance

    def test_fallback_with_icx_internal_call(self):
        sender = self._admin
        callee, caller = self._deploy_sample_scores()

        value = 500
        half_value = value // 2
        before_sender_balance: int = self.get_balance(sender)
        before_caller_balance: int = self.get_balance(caller)
        before_callee_balance: int = self.get_balance(callee)

        # Caller passes a half of icx which it gets from fallback() to callee
        tx_results = self.transfer_icx(from_=sender, to_=caller, value=value)

        tx_result = tx_results[0]
        fee: int = tx_result.step_price * tx_result.step_used

        assert self.get_balance(sender) == before_sender_balance - fee - value
        assert self.get_balance(caller) == before_caller_balance + half_value
        assert self.get_balance(callee) == before_callee_balance + half_value
