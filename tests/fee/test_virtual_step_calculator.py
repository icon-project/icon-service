#!/usr/bin/env python
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
from decimal import Decimal
from unittest import TestCase

from iconservice.base.exception import InvalidRequestException
from iconservice.fee.deposit import Deposit
from iconservice.fee.fee_engine import VirtualStepCalculator


class TestVirtualStepCalculator(TestCase):

    def test_calculate_issuance_virtual_step(self):
        icx_amount_in_loop = 5_000 * 10 ** 18
        deposit_term = 1_296_000
        expected_issuance = 6_263_460_000
        result = VirtualStepCalculator.calculate_virtual_step_issuance(icx_amount_in_loop, 0, deposit_term)
        self.assertEqual(expected_issuance, result)

        icx_amount_in_loop = 5_000 * 10 ** 18
        deposit_term = 1_296_000 * 2
        expected_issuance = 14_627_340_000
        result = VirtualStepCalculator.calculate_virtual_step_issuance(icx_amount_in_loop, 0, deposit_term)
        self.assertEqual(expected_issuance, result)

    def test_calculate_penalty(self):
        icx_amount_in_loop = 5_000 * 10 ** 18
        deposit_factor = 1_296_000
        deposit_term = deposit_factor * 2
        step_price = 10 ** 10
        expected_penalty = Decimal(14_627_340_000 - 6_263_460_000) * step_price + Decimal(icx_amount_in_loop * 0.01)
        result = VirtualStepCalculator.calculate_penalty(icx_amount_in_loop, 0, deposit_term, deposit_factor, 10**10)
        self.assertEqual(result, expected_penalty)

    def test_calculate_withdrawal_amount_success_case(self):
        deposit = Deposit(deposit_amount=1000, deposit_used=100)
        step_price = 10 ** 10
        penalty = 100
        expected_amount = 800
        result = VirtualStepCalculator.calculate_withdrawal_amount(deposit, penalty, step_price)
        self.assertEqual(result, expected_amount)

    def test_calculate_withdrawal_amount_success_case2(self):
        deposit = Deposit(deposit_amount=1000, deposit_used=200, virtual_step_issued=1000, virtual_step_used=100)
        step_price = 10 ** 10
        penalty = 100
        expected_amount = 800
        result = VirtualStepCalculator.calculate_withdrawal_amount(deposit, penalty, step_price)
        self.assertGreater(result, expected_amount)

    def test_calculate_withdrawal_amount_fail_case(self):
        deposit = Deposit(deposit_amount=1000, deposit_used=100)
        step_price = 10 ** 10
        penalty = 950
        self.assertRaises(InvalidRequestException, VirtualStepCalculator.calculate_withdrawal_amount,
                          deposit, penalty, step_price)
