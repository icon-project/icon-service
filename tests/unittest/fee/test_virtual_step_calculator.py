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
from collections import namedtuple
from decimal import Decimal

import pytest

from iconservice.fee.engine import (
    VirtualStepCalculator,
    FIXED_TERM,
    ICX_IN_LOOP,
    BLOCKS_IN_ONE_MONTH,
)

STEP_PRICE = 10 ** 10

VirtualStepInfo = namedtuple("VirtualStepInfo", "deposit_icx, term, rate")

VIRTUAL_STEP_ISSUANCE_TABLE_FROM_YELLOW_PAPER = [
    # (deposit_amount(in icx unit), deposit_term(block), virtual_step_issuance_rate)
    # virtual step issuance rate is based on the virtual_step output table in the Yellow Paper.
    VirtualStepInfo(5_000, 1_296_000, 0.01253),
    VirtualStepInfo(50_000, 1_296_000, 0.01790),
    VirtualStepInfo(100_000, 1_296_000, 0.02386),
    VirtualStepInfo(5_000, 7_776_000, 0.13621),
    VirtualStepInfo(50_000, 7_776_000, 0.19458),
    VirtualStepInfo(100_000, 7_776_000, 0.25944),
    VirtualStepInfo(5_000, 15_552_000, 0.40596),
    VirtualStepInfo(50_000, 15_552_000, 0.57994),
    VirtualStepInfo(100_000, 15_552_000, 0.77326),
    VirtualStepInfo(5_000, 23_328_000, 0.78802),
    VirtualStepInfo(50_000, 23_328_000, 1.12574),
    VirtualStepInfo(100_000, 23_328_000, 1.50098),
    VirtualStepInfo(5_000, 31_104_000, 1.26116),
    VirtualStepInfo(50_000, 31_104_000, 1.80166),
    VirtualStepInfo(100_000, 31_104_000, 2.40221),
]


def _get_expected_issuance(deposit_icx, rate):
    return (
        Decimal(deposit_icx) * Decimal(10 ** 18) * Decimal(rate) / Decimal(STEP_PRICE)
    )


def test_calculate_issuance_virtual_step_fixed_term():
    virtual_step_table = {
        (5_000 * ICX_IN_LOOP, 400 * 10 ** 8),
        (10_000 * ICX_IN_LOOP, 800 * 10 ** 8),
        (15_000 * ICX_IN_LOOP, 1200 * 10 ** 8),
        (25_200 * ICX_IN_LOOP, 2016 * 10 ** 8),
        (40_000 * ICX_IN_LOOP, 3200 * 10 ** 8),
        (5123456789000000000000, 40987654312),
        (5001234567891200000000, 40009876543),
    }
    for amount_in_loop, expected in virtual_step_table:
        issued = VirtualStepCalculator.calculate_virtual_step(
            amount_in_loop, BLOCKS_IN_ONE_MONTH, STEP_PRICE
        )
        assert expected == issued


@pytest.mark.skipif(FIXED_TERM is True, reason="FIXED_TERM is true")
def test_calculate_issuance_virtual_step_yellow_paper():
    for virtual_step_issuance_info in VIRTUAL_STEP_ISSUANCE_TABLE_FROM_YELLOW_PAPER:
        expected_issuance = _get_expected_issuance(
            virtual_step_issuance_info.deposit_icx, virtual_step_issuance_info.rate
        )
        icx_amount_in_loop = virtual_step_issuance_info.deposit_icx * 10 ** 18
        term = virtual_step_issuance_info.term
        result = VirtualStepCalculator.calculate_virtual_step(icx_amount_in_loop, term)
        error_rate = abs((expected_issuance - result) / result)
        assert error_rate <= 100, 0.1


@pytest.mark.skipif(FIXED_TERM is True, reason="FIXED_TERM is true")
def test_calculate_penalty_yellow_paper():
    # case when remaining-virtual-step is 0
    deposit_info_pair1 = (
        VIRTUAL_STEP_ISSUANCE_TABLE_FROM_YELLOW_PAPER[3],
        VIRTUAL_STEP_ISSUANCE_TABLE_FROM_YELLOW_PAPER[0],
    )
    deposit_icx1 = deposit_info_pair1[0].deposit_icx
    deposit_rate1 = deposit_info_pair1[0].rate
    current_rate1 = deposit_info_pair1[1].rate
    remaining_virtual_step1 = _get_expected_issuance(
        deposit_icx1, deposit_rate1
    ) - _get_expected_issuance(deposit_icx1, current_rate1)

    deposit_info_pair2 = (
        VIRTUAL_STEP_ISSUANCE_TABLE_FROM_YELLOW_PAPER[11],
        VIRTUAL_STEP_ISSUANCE_TABLE_FROM_YELLOW_PAPER[2],
    )
    deposit_icx2 = deposit_info_pair2[0].deposit_icx
    deposit_rate2 = deposit_info_pair2[0].rate
    current_rate2 = deposit_info_pair2[1].rate
    remaining_virtual_step2 = _get_expected_issuance(
        deposit_icx2, deposit_rate2
    ) - _get_expected_issuance(deposit_icx2, current_rate2)

    deposit_info_pair3 = (
        VIRTUAL_STEP_ISSUANCE_TABLE_FROM_YELLOW_PAPER[10],
        VIRTUAL_STEP_ISSUANCE_TABLE_FROM_YELLOW_PAPER[4],
    )
    deposit_icx3 = deposit_info_pair3[0].deposit_icx
    deposit_rate3 = deposit_info_pair3[0].rate
    current_rate3 = deposit_info_pair3[1].rate
    remaining_virtual_step3 = _get_expected_issuance(
        deposit_icx3, deposit_rate3
    ) - _get_expected_issuance(deposit_icx3, current_rate3)

    # case when remaining_virtual_step is 0
    _assert_penalty(*deposit_info_pair1)
    _assert_penalty(*deposit_info_pair2)
    _assert_penalty(*deposit_info_pair3)

    # case when remaining_virtual_step == agreement_virtual_step - current_virtual_step
    _assert_penalty(
        deposit_info_pair1[0], deposit_info_pair1[1], remaining_virtual_step1
    )
    _assert_penalty(
        deposit_info_pair2[0], deposit_info_pair2[1], remaining_virtual_step2
    )
    _assert_penalty(
        deposit_info_pair3[0], deposit_info_pair3[1], remaining_virtual_step3
    )

    # case when remaining_virtual_step < agreement_virtual_step - current_virtual_step
    _assert_penalty(
        deposit_info_pair1[0],
        deposit_info_pair1[1],
        remaining_virtual_step1 * Decimal(0.9),
    )
    _assert_penalty(
        deposit_info_pair2[0],
        deposit_info_pair2[1],
        remaining_virtual_step2 * Decimal(0.9),
    )
    _assert_penalty(
        deposit_info_pair3[0],
        deposit_info_pair3[1],
        remaining_virtual_step3 * Decimal(0.9),
    )

    # case when remaining_virtual_step > agreement_virtual_step - current_virtual_step
    _assert_penalty(
        deposit_info_pair1[0],
        deposit_info_pair1[1],
        remaining_virtual_step1 * Decimal(1.1),
    )
    _assert_penalty(
        deposit_info_pair2[0],
        deposit_info_pair2[1],
        remaining_virtual_step2 * Decimal(1.1),
    )
    _assert_penalty(
        deposit_info_pair3[0],
        deposit_info_pair3[1],
        remaining_virtual_step3 * Decimal(1.1),
    )


def _assert_penalty(agreement_info, current_agreement_info, remaining_virtual_step=0):
    deposit_amount = agreement_info.deposit_icx * 10 ** 18
    agreement_term = agreement_info.term
    elapsed_term = current_agreement_info.term

    expected_agreement_issuance_virtual_step = _get_expected_issuance(
        agreement_info.deposit_icx, agreement_info[2]
    )
    expected_withdraw_issuance_virtual_step = _get_expected_issuance(
        current_agreement_info.deposit_icx, current_agreement_info.rate
    )
    breach_penalty = Decimal(agreement_info.deposit_icx * 0.01 * 10 ** 18)
    remaining_virtual_step = remaining_virtual_step - remaining_virtual_step
    expected_penalty = (
        expected_agreement_issuance_virtual_step
        - expected_withdraw_issuance_virtual_step
        - remaining_virtual_step
    ) * STEP_PRICE + breach_penalty

    virtual_step_issued: int = VirtualStepCalculator.calculate_virtual_step(
        deposit_amount, agreement_term
    )

    result = VirtualStepCalculator.calculate_penalty(
        deposit_amount,
        remaining_virtual_step,
        virtual_step_issued,
        elapsed_term,
        STEP_PRICE,
    )
    error_rate = abs((expected_penalty - result) / result)
    assert error_rate <= 100, 0.1
