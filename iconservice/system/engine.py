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


from typing import Optional, TYPE_CHECKING, Any

from ..base.ComponentBase import EngineBase
from .value import SystemValue
from ..system import SystemStorage
from ..base.address import GOVERNANCE_SCORE_ADDRESS
from ..base.exception import ScoreNotFoundException
from ..builtin_scores.governance.governance import Governance
from ..icon_constant import SystemValueType
from ..iconscore.icon_score_context_util import IconScoreContextUtil
from ..precommit_data_manager import PrecommitData

if TYPE_CHECKING:
    from ..iconscore.icon_score_context import IconScoreContext, ContextContainer


class Engine(EngineBase, ContextContainer):
    TAG = "SYSTEM"

    def __init__(self):
        super().__init__()
        self._system_value: Optional['SystemValue'] = None

        # Warning: This mapper must be used only before migration
        # 'gs' means governance score
        self._get_gs_data_mapper: dict = {
            SystemValueType.REVISION_CODE: self._get_revision_from_governance_score
        }

    def open(self, context: 'IconScoreContext'):
        self._system_value: 'SystemValue' = self._load_system_value(context)

    def _load_system_value(self, context: 'IconScoreContext') -> 'SystemValue':
        # Todo: set storage to context
        system_value: Optional['SystemValue'] = SystemStorage.load_system_value(context)
        if system_value is None:
            system_value: 'SystemValue' = SystemValue(is_migrated=False)
            self.sync_system_value_with_governance(context, system_value)
            pass
        return system_value

    def sync_system_value_with_governance(self,
                                          context: 'IconScoreContext',
                                          system_value: 'SystemValue'):
        # Todo: context만 있어도 되지 않을까 -> 확인결과 load 부분에서도 공동으로 쓰기위해서는 system_value를 받을 필요 있음
        """
        Syncronize system value with governance value.
        :param context:
        :param system_value:
        :return:
        """
        assert not system_value.is_migrated
        try:
            self._push_context(context)
            governance_score = self._get_governance_score(context)
            for type_ in SystemValueType:
                value: Any = self._get_gs_data_mapper[type_](governance_score)
                system_value.set_from_icon_service(type_, value)

        finally:
            self._pop_context()

    @staticmethod
    def _get_revision_from_governance_score(governance_score: 'Governance'):
        # Check if revision has been changed by comparing with system engine's system value
        revision: int = 0
        if hasattr(governance_score, 'revision_code'):
            revision: int = governance_score.revision_code
        return revision

    @staticmethod
    def _get_governance_score(context: 'IconScoreContext') -> 'Governance':
        governance_score = \
            IconScoreContextUtil.get_icon_score(context, GOVERNANCE_SCORE_ADDRESS)
        if governance_score is None:
            raise ScoreNotFoundException('Governance SCORE not found')
        return governance_score

    def commit(self, _context: 'IconScoreContext', precommit_data: 'PrecommitData'):
        # Set updated system value
        pass
