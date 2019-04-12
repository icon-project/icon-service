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

from typing import TYPE_CHECKING, Optional

from ...icon_constant import ConfigKey
from .prep_variable_storage import GovernanceVariable, PRepVariableStorage

if TYPE_CHECKING:
    from ...iconscore.icon_score_context import IconScoreContext
    from ...database.db import ContextDatabase
    from .prep_variable_storage import PReps
    from iconcommons import IconConfig


class PRepVariable(object):

    def __init__(self, db: 'ContextDatabase'):
        self._storage: 'PRepVariableStorage' = PRepVariableStorage(db)

    def init_config(self, context: 'IconScoreContext', conf: 'IconConfig'):
        if self._storage.get_gv(context) is None:
            gv: 'GovernanceVariable' = GovernanceVariable.from_config_data(conf[ConfigKey.GOVERNANCE_VARIABLE])
            self._storage.put_gv(context, gv)

    def put_gv(self, context: 'IconScoreContext', gv: 'GovernanceVariable'):
        self._storage.put_gv(context, gv)

    def get_gv(self, context: 'IconScoreContext') -> 'GovernanceVariable':
        value: Optional['GovernanceVariable'] = self._storage.get_gv(context)
        if value is None:
            return GovernanceVariable()
        return value

    def put_preps(self, context: 'IconScoreContext', preps: 'PReps'):
        self._storage.put_preps(context, preps)

    def get_preps(self, context: 'IconScoreContext') -> list:
        value: Optional['PReps'] = self._storage.get_preps(context)
        if value is None:
            return []
        return value.preps
