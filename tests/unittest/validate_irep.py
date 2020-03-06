#!/usr/bin/env python3
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

import unittest

from iconservice.base.exception import InvalidParamsException
from iconservice.icon_constant import IISS_MIN_IREP, ICX_IN_LOOP, PERCENTAGE_FOR_BETA_2
from iconservice.prep.validator import _validate_irep

MAIN_PREP_COUNT: int = 4


class TestValidateIRep(unittest.TestCase):
    def test_validate_minimum_irep(self):
        irep: int = IISS_MIN_IREP - 1
        prev_irep: int = IISS_MIN_IREP

        with self.assertRaises(InvalidParamsException) as e:
            _validate_irep(irep=irep,
                           prev_irep=prev_irep,
                           prev_irep_block_height=1,
                           term_start_block_height=2,
                           term_total_supply=(8 * 10 ** 8) * ICX_IN_LOOP,
                           main_prep_count=MAIN_PREP_COUNT)
        self.assertEqual(e.exception.args[0], f"Irep out of range: {irep}, {prev_irep}")

    def test_validate_prev_irep_over(self):
        prev_irep: int = IISS_MIN_IREP
        irep: int = prev_irep * 12 // 10 + 1

        with self.assertRaises(InvalidParamsException) as e:
            _validate_irep(irep=irep,
                           prev_irep=prev_irep,
                           prev_irep_block_height=1,
                           term_start_block_height=2,
                           term_total_supply=(8 * 10 ** 8) * ICX_IN_LOOP,
                           main_prep_count=MAIN_PREP_COUNT)
        self.assertEqual(e.exception.args[0], f"Irep out of range: {irep}, {prev_irep}")

    def test_validate_prev_irep_below(self):
        prev_irep: int = IISS_MIN_IREP * 2 * 12 // 10
        irep: int = prev_irep * 8 // 10 - 1

        with self.assertRaises(InvalidParamsException) as e:
            _validate_irep(irep=irep,
                           prev_irep=prev_irep,
                           prev_irep_block_height=1,
                           term_start_block_height=2,
                           term_total_supply=(8 * 10 ** 8) * ICX_IN_LOOP,
                           main_prep_count=MAIN_PREP_COUNT)
        self.assertEqual(e.exception.args[0], f"Irep out of range: {irep}, {prev_irep}")

    def test_validate_irep_total_supply_over(self):
        total_supply: int = (8 * 10 ** 8) * ICX_IN_LOOP

        prev_irep: int = total_supply * 14 // (600 * (MAIN_PREP_COUNT + PERCENTAGE_FOR_BETA_2))
        irep: int = prev_irep + 1

        with self.assertRaises(InvalidParamsException) as e:
            _validate_irep(irep=irep,
                           prev_irep=prev_irep,
                           prev_irep_block_height=1,
                           term_start_block_height=2,
                           term_total_supply=total_supply,
                           main_prep_count=MAIN_PREP_COUNT)
        self.assertEqual(e.exception.args[0], f"Irep out of range: {irep}, {prev_irep}")


if __name__ == '__main__':
    unittest.main()
