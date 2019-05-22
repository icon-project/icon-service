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

from typing import TYPE_CHECKING, Optional, Tuple

from .icon_score_context_util import IconScoreContextUtil
from ..base.exception import AccessDeniedException
from ..iconscore.icon_score_base import IconScoreBase
from ..utils import is_builtin_score as util_is_builtin_score

if TYPE_CHECKING:
    from ..database.db import IconScoreDatabase
    from ..base.address import Address
    from ..deploy.icon_score_deploy_storage import IconScoreDeployTXParams
    from ..deploy.icon_score_deploy_storage import IconScoreDeployInfo


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
