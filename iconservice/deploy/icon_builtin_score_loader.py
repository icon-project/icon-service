# -*- coding: utf-8 -*-
# Copyright 2018 theloop Inc.
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

import os
from typing import TYPE_CHECKING

from ..base.address import Address, AddressPrefix
from ..base.address import GOVERNANCE_SCORE_ADDRESS

if TYPE_CHECKING:
    from .icon_score_deploy_engine import IconScoreDeployEngine
    from ..iconscore.icon_score_context import IconScoreContext

ROOT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../'))
PRE_BUILTIN_SCORE_ROOT_PATH = os.path.join(ROOT_PATH, 'builtin_scores')


class IconBuiltinScoreLoader(object):
    _BUILTIN_SCORE_ADDRESS_MAPPER = {'governance': GOVERNANCE_SCORE_ADDRESS}

    def __init__(self,
                 deploy_engine: 'IconScoreDeployEngine') -> None:
        """Constructor
        """

        self._deploy_engine = deploy_engine

    def load_builtin_scores(self, context: 'IconScoreContext', admin_addr_str: str):
        admin_owner = Address.from_string(admin_addr_str)
        for key, value in self._BUILTIN_SCORE_ADDRESS_MAPPER.items():
            self._load_builtin_score(context, key, value, admin_owner)

    def _load_builtin_score(self, context: 'IconScoreContext',
                            score_name: str,
                            icon_score_address: 'Address',
                            builtin_score_owner: 'Address'):
        if self._deploy_engine.icon_deploy_storage.is_score_active(context, icon_score_address):
            return

        score_path = os.path.join(PRE_BUILTIN_SCORE_ROOT_PATH, score_name)
        self._deploy_engine.write_deploy_info_and_tx_params_for_builtin(icon_score_address, builtin_score_owner)
        self._deploy_engine.deploy_for_builtin(icon_score_address, score_path)

    @classmethod
    def is_builtin_score(cls, score_address: 'Address') -> bool:
        return score_address in cls._BUILTIN_SCORE_ADDRESS_MAPPER
