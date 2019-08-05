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
from .engine import EngineListener as IISSEngineListener
from .storage import Storage as IISSStorage
from ..icon_constant import REV_DECENTRALIZATION

if TYPE_CHECKING:
    from ..iconscore.icon_score_context import IconScoreContext
    from ..prep.data.prep import PRep


def check_decentralization_condition(context: 'IconScoreContext') -> bool:
    if context.revision < REV_DECENTRALIZATION:
        return False

    """ICON network decentralize when the last prep of main prep count ( default: 22th )
    get delegation more than some value( default: total-supply * 0.002icx )"""
    preps = context.preps
    if preps.size(active_prep_only=True) >= context.main_prep_count:
        minimum_delegate = get_minimum_delegate_for_bottom_prep(context)
        bottom_prep: 'PRep' = preps.get_by_index(context.main_prep_count - 1)
        bottom_prep_delegated = bottom_prep.delegated
        return bottom_prep_delegated >= minimum_delegate
    return False


def get_minimum_delegate_for_bottom_prep(context: 'IconScoreContext') -> int:
    """Minimum delegate default value = total_supply * 0.002 ICX"""
    assert 1.0 > context.decentralize_trigger >= 0

    str_float: str = str(context.decentralize_trigger)
    decimal: str = str_float[str_float.find('.') + 1:]
    numerator = int(decimal)
    denominator = 10 ** len(decimal)

    total_supply: int = context.storage.icx.get_total_supply(context)

    minimum_delegate: int = total_supply * numerator // denominator
    return minimum_delegate
