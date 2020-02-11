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


from typing import Optional, TYPE_CHECKING

from iconservice.base.ComponentBase import EngineBase
from iconservice.system.value import SystemValue
from iconservice.system import SystemStorage
from ..precommit_data_manager import PrecommitData

if TYPE_CHECKING:
    from ..iconscore.icon_score_context import IconScoreContext


class Engine(EngineBase):
    TAG = "SYSTEM"

    def __init__(self):
        super().__init__()
        self._system_value: Optional['SystemValue'] = None

    def open(self, context: 'IconScoreContext'):
        self._system_value = self._load_system_value(context)

    @classmethod
    def _load_system_value(cls, context: 'IconScoreContext') -> 'SystemValue':
        # Todo: set storage to context
        system_value: Optional['SystemValue'] = SystemStorage.load_system_value(context)
        if system_value is None:
            # Initiate GV from Governance Score
            pass
        return system_value

    def commit(self, _context: 'IconScoreContext', precommit_data: 'PrecommitData'):
        # Set updated system value
        pass
