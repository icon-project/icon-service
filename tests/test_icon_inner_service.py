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

import unittest

from iconservice.base.type_converter_templates import ConstantKeys
from iconservice.icon_inner_service import IconScoreInnerTask
from tests import create_block_hash


class TestIconInnerService(unittest.TestCase):
    def test_get_block_info_for_precommit_state(self):
        block_height = 10
        instant_block_hash = create_block_hash()
        block_hash = create_block_hash()

        # success case: when input prev write pre-commit data format, block_hash should be None
        prev_precommit_data_format = {
            ConstantKeys.BLOCK_HEIGHT: block_height,
            ConstantKeys.BLOCK_HASH: instant_block_hash
        }
        actual_block_height, actual_instant_block_hash, actual_block_hash = \
            IconScoreInnerTask._get_block_info_for_precommit_state(prev_precommit_data_format)

        self.assertEqual(block_height, actual_block_height)
        self.assertEqual(instant_block_hash, actual_instant_block_hash)
        self.assertEqual(None, actual_block_hash)

        # success case: when input new write-pre-commit data format, block_hash should be hash
        new_precommit_data_format = {
            ConstantKeys.BLOCK_HEIGHT: block_height,
            ConstantKeys.OLD_BLOCK_HASH: instant_block_hash,
            ConstantKeys.NEW_BLOCK_HASH: block_hash
        }
        actual_block_height, actual_instant_block_hash, actual_block_hash = \
            IconScoreInnerTask._get_block_info_for_precommit_state(new_precommit_data_format)

        self.assertEqual(block_height, actual_block_height)
        self.assertEqual(instant_block_hash, actual_instant_block_hash)
        self.assertEqual(block_hash, actual_block_hash)

        # failure case: when input invalid data format, should raise key error
        invalid_precommit_data_format = {
            ConstantKeys.BLOCK_HEIGHT: block_height,
            ConstantKeys.OLD_BLOCK_HASH: instant_block_hash,
        }
        self.assertRaises(KeyError, IconScoreInnerTask._get_block_info_for_precommit_state, invalid_precommit_data_format)
