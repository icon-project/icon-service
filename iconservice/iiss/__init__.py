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
from ..icon_constant import PREP_MAIN_PREPS, MINIMUM_DELEGATE_OF_BOTTOM_PREP

if TYPE_CHECKING:
    from ..iconscore.icon_score_context import IconScoreContext
    from ..prep.data.prep import PRep


def check_decentralization_condition(context: 'IconScoreContext') -> bool:
    if len(context.engine.prep.preps) >= PREP_MAIN_PREPS:
        bottom_prep: 'PRep' = context.engine.prep.preps[PREP_MAIN_PREPS - 1]
        return bottom_prep.delegated >= MINIMUM_DELEGATE_OF_BOTTOM_PREP

    return False
