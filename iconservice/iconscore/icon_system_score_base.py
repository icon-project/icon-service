# -*- coding: utf-8 -*-

# Copyright 2018 ICON Foundation
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

from abc import abstractmethod
from typing import TYPE_CHECKING, Optional, Tuple, Any, Dict

from .icon_score_context_util import IconScoreContextUtil
from .icon_score_step import StepType
from ..base.exception import AccessDeniedException, IconServiceBaseException
from ..icon_constant import SystemValueType, IconScoreContextType
from ..iconscore.icon_score_base import IconScoreBase
from ..system.value import SystemValueConverter
from ..utils import is_builtin_score as util_is_builtin_score

if TYPE_CHECKING:
    from ..base.address import Address
    from ..database.db import IconScoreDatabase
    from ..deploy.storage import IconScoreDeployInfo, IconScoreDeployTXParams


class IconSystemScoreBase(IconScoreBase):

    @abstractmethod
    def on_install(self, **kwargs) -> None:
        """DB initialization on score install
        """
        super().on_install(**kwargs)

    @abstractmethod
    def on_update(self, **kwargs) -> None:
        """DB initialization on score update
        """
        super().on_update(**kwargs)

    @abstractmethod
    def __init__(self, db: 'IconScoreDatabase') -> None:
        super().__init__(db)
        if not util_is_builtin_score(str(self.address)):
            raise AccessDeniedException(f"Not a system SCORE ({self.address})")

    def is_builtin_score(self, score_address: 'Address') -> bool:
        return util_is_builtin_score(str(score_address))

    # TODO remove after Update 0.0.6
    def get_icon_service_flag(self) -> int:
        return self._context.icon_service_flag

    # TODO remove after Update 0.0.6
    def deploy(self, tx_hash: bytes) -> None:
        return IconScoreContextUtil.deploy(self._context, tx_hash)

    def get_deploy_tx_params(self, tx_hash: bytes) -> Optional['IconScoreDeployTXParams']:
        return IconScoreContextUtil.get_deploy_tx_params(self._context, tx_hash)

    def get_deploy_info(self, address: 'Address') -> Optional['IconScoreDeployInfo']:
        return IconScoreContextUtil.get_deploy_info(self._context, address)

    def is_score_active(self, score_address: 'Address') -> bool:
        return IconScoreContextUtil.is_score_active(self._context, score_address)

    def get_owner(self, score_address: Optional['Address']) -> Optional['Address']:
        return IconScoreContextUtil.get_owner(self._context, score_address)

    def migrate_system_value(self, data: Dict['SystemValueType', Any]):
        converted_data: dict = {}
        for type_, value in data.items():
            converted_data[type_] = SystemValueConverter.convert_for_icon_service(type_, value)
        self._context.system_value.migrate(self._context, converted_data)

    def get_system_value(self, type_: 'SystemValueType') -> Any:
        if type_ == SystemValueType.REVISION_CODE:
            value = self._context.system_value.revision_code
        elif type_ == SystemValueType.REVISION_NAME:
            value = self._context.system_value.revision_name
        elif type_ == SystemValueType.SCORE_BLACK_LIST:
            value = self._context.system_value.score_black_list
        elif type_ == SystemValueType.STEP_PRICE:
            value = self._context.system_value.step_price
        elif type_ == SystemValueType.STEP_COSTS:
            value = self._context.system_value.step_costs
        elif type_ == SystemValueType.MAX_STEP_LIMITS:
            value = self._context.system_value.max_step_limits
        elif type_ == SystemValueType.SERVICE_CONFIG:
            value = self._context.system_value.service_config
        elif type_ == SystemValueType.IMPORT_WHITE_LIST:
            value = self._context.system_value.service_config
        else:
            raise ValueError(f"Invalid value type: {type_.name}")
        converted_value: Any = SystemValueConverter.convert_for_governance_score(type_, value)
        return converted_value

    def set_system_value(self, type_: 'SystemValueType', value: Any):
        converted_value: Any = SystemValueConverter.convert_for_icon_service(type_, value)
        self._context.system_value.set_by_governance_score(self._context, type_, converted_value)

    def disqualify_prep(self, address: 'Address') -> Tuple[bool, str]:
        success: bool = True
        reason: str = ""
        try:
            self._context.engine.prep.impose_prep_disqualified_penalty(self._context, address)
        except IconServiceBaseException as e:
            success = False
            reason = str(e)
        finally:
            return success, reason
