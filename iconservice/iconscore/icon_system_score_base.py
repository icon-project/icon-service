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
from ..base.exception import AccessDeniedException, IconServiceBaseException,\
    InvalidParamsException, InvalidRequestException
from ..icon_constant import IconNetworkValueType, Revision
from ..inv.container import ValueConverter as INVConverter
from ..inv.data.value import Value
from ..iconscore.icon_score_base import IconScoreBase
from ..prep.validator import validate_np_irep
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

    def migrate_icon_network_value(self, data: Dict['IconNetworkValueType', Any]):
        converted_data: list = []
        for type_, value in data.items():
            converted_data.append(INVConverter.convert_for_icon_service(type_, value))
        self._context.inv_container.migrate(converted_data)
        self._context.storage.inv.migrate(self._context, converted_data)

    def validate_irep(self, irep: int):
        if self._context.revision < Revision.SET_IREP_VIA_NETWORK_PROPOSAL.value:
            raise InvalidRequestException(f"Can't register I-Rep proposal. Revision must be larger than "
                                          f"{Revision.SET_IREP_VIA_NETWORK_PROPOSAL.value - 1}")

        validate_np_irep(self._context, irep)

    @classmethod
    def _check_inv_type(cls, type_: 'IconNetworkValueType'):
        if type_ not in IconNetworkValueType:
            raise InvalidParamsException(f"Invalid INV type: {type_}")

    def get_icon_network_value(self, type_: 'IconNetworkValueType') -> Any:
        self._check_inv_type(type_)

        value: Any = self._context.inv_container.get_by_type(type_)
        converted_value: Any = INVConverter.convert_for_governance(type_, value)
        return converted_value

    def set_icon_network_value(self, type_: 'IconNetworkValueType', value: Any):
        self._check_inv_type(type_)

        converted_value: 'Value' = INVConverter.convert_for_icon_service(type_, value)
        self._context.inv_container.set_inv_to_tx_batch(converted_value)
        self._context.storage.inv.put_value(self._context, converted_value)

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

    def apply_revision_change(self, revision):
        # CAUTION
        # Please follow the instructions below to apply the change. revision may not be set sequentially
        #   1. add an 'if' statement for every revision and compare revision with '>=' operator
        #   2. Check if the change has already been applied and apply the change

        if revision >= Revision.SET_IREP_VIA_NETWORK_PROPOSAL.value:
            # I-Rep is managed by INV. copy Term.irep to INV.irep
            if self.get_icon_network_value(IconNetworkValueType.IREP) is None:
                self.set_icon_network_value(IconNetworkValueType.IREP, self._context.term.irep)
