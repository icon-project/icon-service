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
from ..icon_constant import PREP_COUNT, MINIMUM_DELEGATE_OF_BOTTOM_PREP
from .engine import Engine as IISSEngine
from .storage import Storage as IISSStorage


def check_decentralization_condition(context):
    if len(context.engine.prep.preps) >= PREP_COUNT:
        bottom_prep = context.engine.prep.preps[PREP_COUNT - 1]
        bottom_prep_delegated = bottom_prep.delegated
        if bottom_prep_delegated >= MINIMUM_DELEGATE_OF_BOTTOM_PREP:
            return True
    return False
