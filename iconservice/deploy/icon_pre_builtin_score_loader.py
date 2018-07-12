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

from ..base.address import GOVERNANCE_SCORE_ADDRESS, ADMIN_SCORE_ADDRESS

if TYPE_CHECKING:
    from .icon_score_deploy_engine import IconScoreDeployEngine
    from ..base.address import Address
    from ..iconscore.icon_score_context import IconScoreContext

ROOT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../'))
PRE_BUILTIN_SCORE_ROOT_PATH = os.path.join(ROOT_PATH, 'prebuiltin_score')


class IconPreBuiltinScoreLoader(object):
    _PRE_BUILTIN_SCORE_ADDRESS_MAPPER = {'governance': GOVERNANCE_SCORE_ADDRESS}

    def __init__(self, deploy_engine: 'IconScoreDeployEngine') -> None:
        """Constructor
        """

        self._deploy_engine = deploy_engine

    def load_builtin_scores(self, context: 'IconScoreContext'):
        for key, value in self._PRE_BUILTIN_SCORE_ADDRESS_MAPPER.items():
            self._load_builtin_score(context, key, value)

    def _load_builtin_score(self, context: 'IconScoreContext', score_name: str, icon_score_address: 'Address'):
        if self._deploy_engine.icon_deploy_storage.is_score_deployed(context, icon_score_address):
            return

        score_path = os.path.join(PRE_BUILTIN_SCORE_ROOT_PATH, score_name)
        self._deploy_engine.write_total_deploy_info_for_prebuiltin(icon_score_address, ADMIN_SCORE_ADDRESS)
        self._deploy_engine.deploy_for_prebuiltin(context, icon_score_address, score_path)
