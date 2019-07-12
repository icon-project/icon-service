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

from iconservice.icon_constant import IISS_DAY_BLOCK
from iconservice.iiss import IISSEngine

if TYPE_CHECKING:
    pass


EXPECTED_LOCK_PERIOD_PRE_STAKE_PERCENT = \
            [862400,
             844052,
             825968,
             808148,
             790592,
             773300,
             756272,
             739508,
             723008,
             706772,
             690800,
             675092,
             659648,
             644468,
             629552,
             614900,
             600512,
             586388,
             572528,
             558932,
             545600,
             532532,
             519728,
             507188,
             494912,
             482900,
             471152,
             459668,
             448448,
             437492,
             426800,
             416372,
             406208,
             396308,
             386672,
             377300,
             368192,
             359348,
             350768,
             342452,
             334400,
             326612,
             319088,
             311828,
             304832,
             298100,
             291632,
             285428,
             279488,
             273812,
             268400,
             263252,
             258368,
             253748,
             249392,
             245300,
             241472,
             237908,
             234608,
             231572,
             228800,
             226292,
             224048,
             222068,
             220352,
             218900,
             217712,
             216788,
             216128,
             215732,
             215600,
             215600,
             215600,
             215600,
             215600,
             215600,
             215600,
             215600,
             215600,
             215600,
             215600,
             215600,
             215600,
             215600,
             215600,
             215600,
             215600,
             215600,
             215600,
             215600,
             215600,
             215600,
             215600,
             215600,
             215600,
             215600,
             215600,
             215600,
             215600,
             215600,
             215600]


class TestIissEngine(unittest.TestCase):
    def test_calculate_unstake_lock_period(self):
        lmin = IISS_DAY_BLOCK * 5
        lmax = IISS_DAY_BLOCK * 20
        rpoint = 7000
        for x in range(0, 100):
            ret = IISSEngine._calculate_unstake_lock_period(lmin, lmax, rpoint, x, 100)
            diff = abs(ret - EXPECTED_LOCK_PERIOD_PRE_STAKE_PERCENT[x])
            assert diff <= 1


if __name__ == '__main__':
    unittest.main()
