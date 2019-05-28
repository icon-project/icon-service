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

from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from .candidate_engine import CandidateEngine
    from .variable.variable_storage import PRep
    from ..base.address import Address
    from ..iconscore.icon_score_context import IconScoreContext


class CandidateEngineInterface(object):
    def __init__(self, engine: 'CandidateEngine'):
        self._engine: 'CandidateEngine' = engine

    # interface
    def update_preps_to_variable(self, context: 'IconScoreContext'):
        self._engine.update_preps_to_variable(context)

    def get_gv(self, context: 'IconScoreContext'):
        return self._engine.get_gv(context)

    def is_candidate(self, context: 'IconScoreContext', address: 'Address') -> bool:
        return self._engine.is_candidate(context, address)

    def get_preps(self, context: 'IconScoreContext') -> List['PRep']:
        return self._engine.get_preps(context)

    def update_sorted_candidates(self,
                                 context: 'IconScoreContext',
                                 address: 'Address',
                                 total_delegated: int):
        self._engine.update_sorted_candidates(context, address, total_delegated)
