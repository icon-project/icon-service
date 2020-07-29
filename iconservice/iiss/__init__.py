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

import decimal
from typing import TYPE_CHECKING

from .engine import Engine as IISSEngine
from .engine import Method as IISSMethod
from .storage import Storage as IISSStorage
from ..icon_constant import Revision

if TYPE_CHECKING:
    from ..iconscore.icon_score_context import IconScoreContext
    from ..prep.data.prep import PRep


def check_decentralization_condition(context: 'IconScoreContext') -> bool:
    if context.revision < Revision.DECENTRALIZATION.value or context.is_decentralized():
        # If revision is less than REV_DECENTRALIZATION or
        # network has been already decentralized
        return False

    context.update_dirty_prep_batch()

    """ICON network decentralize when the last prep of main prep count ( default: 22th )
    get delegation more than some value( default: total-supply * 0.002icx )"""
    if context.preps.size(active_prep_only=True) >= context.main_prep_count:
        minimum_delegate = get_minimum_delegate_for_bottom_prep(context)
        bottom_prep: 'PRep' = context.preps.get_by_index(context.main_prep_count - 1)
        return bottom_prep.delegated >= minimum_delegate
    return False


def get_minimum_delegate_for_bottom_prep(context: 'IconScoreContext') -> int:
    """Minimum delegate default value = total_supply * 0.002 ICX"""
    assert 1.0 > context.decentralize_trigger >= 0
    numerator, denominator = _split_float_to_numerator_and_denominator(context.decentralize_trigger)
    if numerator == 0:
        return 0

    total_supply: int = context.storage.icx.get_total_supply(context)
    minimum_delegate: int = total_supply * numerator // denominator
    return minimum_delegate


def _split_float_to_numerator_and_denominator(float_data: float) -> tuple:
    assert 1.0 > float_data >= 0
    str_float: str = format(decimal.Decimal(str(float_data)), 'f')
    str_decimal: str = str_float[str_float.find('.') + 1:]
    numerator = int(str_decimal)
    denominator = 10 ** len(str_decimal)
    return numerator, denominator
