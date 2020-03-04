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

from .container import Container, ValueConverter
from .. import Address
from ..base.ComponentBase import EngineBase
from ..base.address import GOVERNANCE_SCORE_ADDRESS
from ..base.exception import ScoreNotFoundException
from ..icon_constant import IconNetworkValueType, IconServiceFlag
from ..iconscore.context.context import ContextContainer
from ..iconscore.icon_score_context_util import IconScoreContextUtil
from ..iconscore.icon_score_result import TransactionResult

if TYPE_CHECKING:
    from ..iconscore.icon_score_context import IconScoreContext
    from ..builtin_scores.governance.governance import Governance
    from ..precommit_data_manager import PrecommitData


class Engine(EngineBase, ContextContainer):
    TAG = "INV"

    def __init__(self):
        super().__init__()
        self._inv_container: Optional['Container'] = None

        # Warning: This mapper must be used only before migration
        # 'gs' means governance SCORE
        self._get_gs_data_mapper: dict = {
            IconNetworkValueType.SERVICE_CONFIG: self._get_service_flag,
            IconNetworkValueType.STEP_PRICE: self._get_step_price_from_governance,
            IconNetworkValueType.STEP_COSTS: self._get_step_costs_from_governance,
            IconNetworkValueType.MAX_STEP_LIMITS: self._get_step_max_limits_from_governance,
            IconNetworkValueType.REVISION_CODE: self._get_revision_from_governance_score,
            IconNetworkValueType.REVISION_NAME: self._get_revision_name_from_governance_score,
            IconNetworkValueType.SCORE_BLACK_LIST: self._get_score_black_list,
            IconNetworkValueType.IMPORT_WHITE_LIST: self._get_import_whitelist
        }

    @property
    def inv_container(self) -> 'Container':
        return self._inv_container

    def load_inv_container(self, context: 'IconScoreContext'):
        container: Optional['Container'] = context.storage.inv.get_container(context)
        if container is None:
            container: 'Container' = Container(is_migrated=False)
            self._sync_inv_container_with_governance(context, container)
        self._inv_container = container

    def update_inv_container_by_result(self,
                                       context: 'IconScoreContext',
                                       tx_result: 'TransactionResult'):
        if tx_result.status == TransactionResult.SUCCESS:
            if context.inv_container.is_migrated:
                context.inv_container.update_batch()
            elif tx_result.to == GOVERNANCE_SCORE_ADDRESS:
                context.inv_container.update_migration_if_succeed()
                self._sync_inv_container_with_governance(context, context.inv_container)
        context.inv_container.clear_batch()

    def _sync_inv_container_with_governance(self,
                                            context: 'IconScoreContext',
                                            container: 'Container'):
        """
        Syncronize ICON Network value.
        :param context:
        :param container:
        :return:
        """
        if container.is_migrated:
            return

        try:
            self._push_context(context)
            governance_score = self._get_governance_score(context)
            for type_ in IconNetworkValueType:
                value: Any = self._get_gs_data_mapper[type_](context, governance_score)
                container.set_by_icon_service(ValueConverter.convert_for_icon_service(type_, value))
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
    def _get_step_max_limits_from_governance(_, governance_score: 'Governance') -> Dict[str, int]:
        # Gets the max step limit
        return {"invoke": governance_score.getMaxStepLimit("invoke"),
                "query": governance_score.getMaxStepLimit("query")}

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
        return ""

    @staticmethod
    def _get_revision_from_governance_score(_, governance_score: 'Governance') -> int:
        # Check if revision has been changed by comparing with INV engine's ICON Network value
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
        # Set updated INVContainer
        self._inv_container: 'Container' = precommit_data.inv_container
