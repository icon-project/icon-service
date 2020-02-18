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


from typing import Optional, TYPE_CHECKING, Any, Dict, List

from .value import SystemValue
from .. import Address
from ..base.ComponentBase import EngineBase
from ..base.address import GOVERNANCE_SCORE_ADDRESS
from ..base.exception import ScoreNotFoundException
from ..icon_constant import SystemValueType, IconServiceFlag, IconScoreContextType
from ..iconscore.context.context import ContextContainer
from ..iconscore.icon_score_context_util import IconScoreContextUtil
from ..iconscore.icon_score_result import TransactionResult

if TYPE_CHECKING:
    from ..iconscore.icon_score_context import IconScoreContext
    from ..builtin_scores.governance.governance import Governance
    from ..precommit_data_manager import PrecommitData


class Engine(EngineBase, ContextContainer):
    TAG = "SYSTEM"

    def __init__(self):
        super().__init__()
        self._system_value: Optional['SystemValue'] = None

        # Warning: This mapper must be used only before migration
        # 'gs' means governance score
        self._get_gs_data_mapper: dict = {
            SystemValueType.SERVICE_CONFIG: self._get_service_flag,
            SystemValueType.STEP_PRICE: self._get_step_price_from_governance,
            SystemValueType.STEP_COSTS: self._get_step_costs_from_governance,
            SystemValueType.MAX_STEP_LIMITS: self._get_step_max_limits_from_governance,
            SystemValueType.REVISION_CODE: self._get_revision_from_governance_score,
            SystemValueType.REVISION_NAME: self._get_revision_name_from_governance_score,
            SystemValueType.SCORE_BLACK_LIST: self._get_score_black_list,
            SystemValueType.IMPORT_WHITE_LIST: self._get_import_whitelist
        }

    @property
    def system_value(self) -> 'SystemValue':
        return self._system_value

    def load_system_value(self, context: 'IconScoreContext'):
        system_value: Optional['SystemValue'] = context.storage.system.get_system_value(context)
        if system_value is None:
            system_value: 'SystemValue' = SystemValue(is_migrated=False)
            self._sync_system_value_with_governance(context, system_value)
        self._system_value = system_value

    def legacy_system_value_update(self,
                                   context: 'IconScoreContext',
                                   tx_result: 'TransactionResult'):

        if context.system_value.is_migrated:
            return

        if tx_result.to != GOVERNANCE_SCORE_ADDRESS or tx_result.status != TransactionResult.SUCCESS:
            return

        self._sync_system_value_with_governance(context, context.system_value)

    def _sync_system_value_with_governance(self,
                                           context: 'IconScoreContext',
                                           system_value: 'SystemValue'):
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
                value: Any = self._get_gs_data_mapper[type_](context, governance_score)
                system_value.set_by_icon_service(type_, value)
        except ScoreNotFoundException:
            pass
        finally:
            self._pop_context()

    @staticmethod
    def _get_governance_score(context: 'IconScoreContext') -> 'Governance':
        governance_score = \
            IconScoreContextUtil.get_icon_score(context, GOVERNANCE_SCORE_ADDRESS)
        if governance_score is None:
            raise ScoreNotFoundException('Governance SCORE not found')
        return governance_score

    @staticmethod
    def _get_step_price_from_governance(context: 'IconScoreContext', governance_score: 'Governance') -> int:
        step_price = 0
        # Gets the step price if the fee flag is on
        if IconScoreContextUtil.is_service_flag_on(context, IconServiceFlag.FEE):
            step_price = governance_score.getStepPrice()

        return step_price

    @staticmethod
    def _get_step_costs_from_governance(_, governance_score: 'Governance') -> Dict[str, int]:
        return governance_score.getStepCosts()

    @staticmethod
    def _get_step_max_limits_from_governance(_, governance_score: 'Governance') -> Dict['IconScoreContextType', int]:
        # Gets the max step limit
        return {IconScoreContextType.INVOKE: governance_score.getMaxStepLimit("invoke"),
                IconScoreContextType.QUERY: governance_score.getMaxStepLimit("query")}

    @staticmethod
    def _get_service_flag(context: 'IconScoreContext', governance_score: 'Governance') -> int:
        service_config = context.icon_service_flag
        try:
            service_config = governance_score.service_config
        except AttributeError:
            pass
        return service_config

    @staticmethod
    def _get_revision_name_from_governance_score(_, governance_score: 'Governance') -> str:
        # TBD, but before migration, there is no usecase of revision name. So do not need to implement
        return

    @staticmethod
    def _get_revision_from_governance_score(_, governance_score: 'Governance') -> int:
        # Check if revision has been changed by comparing with system engine's system value
        revision: int = 0
        if hasattr(governance_score, 'revision_code'):
            revision: int = governance_score.revision_code
        return revision

    @staticmethod
    def _get_import_whitelist(_, governance_score: 'Governance') -> Dict[str, list]:
        if hasattr(governance_score, 'import_white_list_cache'):
            return governance_score.import_white_list_cache

        return {"iconservice": ['*']}

    @staticmethod
    def _get_score_black_list(_, governance_score: 'Governance') -> List['Address']:
        score_black_list = []
        if hasattr(governance_score, '_score_black_list'):
            score_black_list = [address for address in governance_score._score_black_list]
        return score_black_list

    def commit(self, _context: 'IconScoreContext', precommit_data: 'PrecommitData'):
        # Set updated system value
        self._system_value: 'SystemValue' = precommit_data.system_value
