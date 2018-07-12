# -*- coding: utf-8 -*-
# Copyright 2017-2018 theloop Inc.
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

from typing import TYPE_CHECKING, Optional

from ..base.address import Address
from ..base.address import GOVERNANCE_SCORE_ADDRESS
from ..base.exception import InvalidParamsException, ServerErrorException

if TYPE_CHECKING:
    from ..iconscore.icon_score_context import IconScoreContext
    from ..deploy.icon_score_deploy_engine import IconScoreDeployEngine


class IconScoreManager(object):
    def __init__(self, deploy_engine: 'IconScoreDeployEngine') -> None:
        self.__deploy_engine = deploy_engine

    def deploy(self,
               context: Optional['IconScoreContext'],
               from_score: 'Address',
               tx_hash: bytes,
               audit_tx_hash: bytes) -> None:

        if from_score == GOVERNANCE_SCORE_ADDRESS:
            self.__deploy_engine.deploy(context, tx_hash, audit_tx_hash)
        else:
            raise ServerErrorException('Permission Error')

    def is_deployed(self,
                    context: Optional['IconScoreContext'],
                    icon_score_address: 'Address') -> bool:

        return self.__deploy_engine.icon_deploy_storage.is_score_deployed(context, icon_score_address)

    def get_owner(self,
                  context: Optional['IconScoreContext'],
                  icon_score_address: 'Address') -> Optional['Address']:
        return self.__deploy_engine.icon_deploy_storage.get_score_owner(context, icon_score_address)
