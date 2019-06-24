# -*- coding: utf-8 -*-

# Copyright 2019 ICON Foundation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from typing import TYPE_CHECKING

from .engine import Engine as IISSEngine
from .storage import Storage as IISSStorage
from ..icon_constant import PREP_MAIN_PREPS, ICX_IN_LOOP

if TYPE_CHECKING:
    from ..iconscore.icon_score_context import IconScoreContext
    from ..prep.data.prep import PRep


def check_decentralization_condition(context: 'IconScoreContext'):
    """ICON network decentralize when 22th prep get delegation more than some value(total-supply * 0.002icx)"""
    preps = context.preps
    if len(preps) >= PREP_MAIN_PREPS:
        minimum_delegate = get_minimum_delegate_for_bottom_prep(context)
        bottom_prep: 'PRep' = preps[PREP_MAIN_PREPS - 1]
        bottom_prep_delegated = bottom_prep.delegated
        return bottom_prep_delegated >= minimum_delegate
    return False


def get_minimum_delegate_for_bottom_prep(context: 'IconScoreContext'):
    """Minimum delegate = total_supply * 0.002 ICX"""
    total_supply = context.storage.icx.get_total_supply(context)
    minimum_delegate = total_supply // 1000 * 2
    return minimum_delegate
