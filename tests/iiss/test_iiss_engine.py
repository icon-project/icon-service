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
from typing import TYPE_CHECKING

from iconservice.icon_constant import IISS_DAY_BLOCK, IconScoreContextType
from iconservice.iconscore.icon_score_context import IconScoreContext
from iconservice.iiss import IISSEngine

if TYPE_CHECKING:
    pass


EXPECTED_LOCK_PERIOD_PRE_STAKE_PERCENT = [
    864000, 845618, 827500, 809647, 792059,
    774735, 757675, 740880, 724349, 708083,
    692082, 676344, 660872, 645664, 630720,
    616041, 601626, 587476, 573590, 559969,
    546612, 533520, 520692, 508129, 495830,
    483796, 472026, 460521, 449280, 438304,
    427592, 417144, 406962, 397043, 387389,
    378000, 368875, 360015, 351419, 343087,
    335020, 327218, 319680, 312407, 305398,
    298653, 292173, 285958, 280007, 274320,
    268898, 263740, 258847, 254219, 249855,
    245755, 241920, 238349, 235043, 232002,
    229224, 226712, 224464, 222480, 220761,
    219306, 218116, 217190, 216529, 216132,
    216000, 216000, 216000, 216000, 216000,
    216000, 216000, 216000, 216000, 216000,
    216000, 216000, 216000, 216000, 216000,
    216000, 216000, 216000, 216000, 216000,
    216000, 216000, 216000, 216000, 216000,
    216000, 216000, 216000, 216000, 216000
]


class TestIissEngine(unittest.TestCase):
    def test_calculate_unstake_lock_period(self):
        lmin = IISS_DAY_BLOCK * 5
        lmax = IISS_DAY_BLOCK * 20
        rpoint = 7000
        for x in range(0, 100):
            ret = IISSEngine._calculate_unstake_lock_period(lmin, lmax, rpoint, x, 100)
            diff = abs(ret - EXPECTED_LOCK_PERIOD_PRE_STAKE_PERCENT[x])
            assert diff <= 1

    def test_handle_set_delegation(self):
        context = IconScoreContext(IconScoreContextType.INVOKE)

        engine = IISSEngine()
        engine.handle_set_delegation(context)


if __name__ == '__main__':
    unittest.main()
