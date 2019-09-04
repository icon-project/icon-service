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
from unittest.mock import Mock

import pytest

from iconservice.iconscore.icon_score_context import IconScoreContext
from iconservice.icx.storage import Storage
from iconservice.iiss import _split_float_to_numerator_and_denominator, get_minimum_delegate_for_bottom_prep
from iconservice.utils import ContextStorage


# just for test (float range)
def range_positive(start, stop=None, step=None):
    if stop == None:
        stop = start + 0.0
        start = 0.0
    if step == None:
        step = 1.0
    while start < stop:
        yield start
        start += step


def test__split_float_to_numerator_and_denominator():
    test_step = 0.0000001
    for i, float_data in enumerate(range_positive(0, 1, 0.00003)):
        numerator, denominator = \
            _split_float_to_numerator_and_denominator(float_data)
        assert float_data == numerator / denominator


def test_get_minimum_delegate_for_bottom_prep():
    total_supply: int = 1_000_000_000

    IconScoreContext.storage = Mock(spec=ContextStorage)
    IconScoreContext.storage.icx = Mock(spec=Storage)

    IconScoreContext.storage.icx.get_total_supply = Mock(return_value=total_supply)

    context = IconScoreContext()
    context.decentralize_trigger = 0.1
    get_minimum_delegate_for_bottom_prep(context)

    # failure case: input value equal or upper than 1
    with pytest.raises(AssertionError):
        context.decentralize_trigger = 1
        get_minimum_delegate_for_bottom_prep(context)

    with pytest.raises(AssertionError):
        context.decentralize_trigger = 2
        get_minimum_delegate_for_bottom_prep(context)

    # failure case: input value under 0
    with pytest.raises(AssertionError):
        context.decentralize_trigger = -1
        get_minimum_delegate_for_bottom_prep(context)

    # success case: trigger == 0
    context.decentralize_trigger = 0
    actual_value = get_minimum_delegate_for_bottom_prep(context)
    assert 0 == actual_value

    for x in range(1, 10):
        denominator = 10 ** x
        trigger = 1 / denominator
        context.decentralize_trigger = trigger
        assert get_minimum_delegate_for_bottom_prep(context) == int(total_supply * trigger)

    # success case: main net trigger
    main_net_supply: int = 800374000000000000000000000
    IconScoreContext.storage.icx.get_total_supply = Mock(return_value=main_net_supply)
    context.decentralize_trigger = 0.002
    actual_value = get_minimum_delegate_for_bottom_prep(context)
    expected_value = 1600748000000000000000000
    assert actual_value == expected_value
