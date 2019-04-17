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

from unittest import TestCase

from iconservice.fee.score_deposit_info import ScoreDepositInfo
from tests import create_tx_hash


class TestFee(TestCase):

    def test_score_deposit_info_from_bytes_to_bytes(self):
        score_deposit_info = ScoreDepositInfo()
        score_deposit_info.head_id = create_tx_hash()
        score_deposit_info.tail_id = create_tx_hash()
        score_deposit_info.available_head_id_of_deposit = create_tx_hash()
        score_deposit_info.available_head_id_of_virtual_step = create_tx_hash()
        score_deposit_info.expires_of_deposit = 1
        score_deposit_info.expires_of_virtual_step = 200
        score_deposit_info.version = 3

        score_deposit_info_in_bytes = score_deposit_info.to_bytes()
        self.assertIsInstance(score_deposit_info_in_bytes, bytes)

        score_deposit_info_2 = ScoreDepositInfo.from_bytes(score_deposit_info_in_bytes)
        self.assertIsInstance(score_deposit_info_2, ScoreDepositInfo)
        self.assertEqual(score_deposit_info, score_deposit_info_2)

    def test_score_deposit_info_to_bytes_from_bytes_with_none_type(self):
        score_deposit_info = ScoreDepositInfo()
        score_deposit_info_in_bytes = score_deposit_info.to_bytes()
        self.assertIsInstance(score_deposit_info_in_bytes, bytes)

        score_deposit_info_2 = ScoreDepositInfo.from_bytes(score_deposit_info_in_bytes)
        self.assertIsInstance(score_deposit_info_2, ScoreDepositInfo)
        self.assertEqual(score_deposit_info, score_deposit_info_2)

