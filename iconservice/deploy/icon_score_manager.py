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

from typing import TYPE_CHECKING, Optional, Tuple

from ..base.address import Address
from ..base.address import GOVERNANCE_SCORE_ADDRESS
from ..base.exception import ServerErrorException

if TYPE_CHECKING:
    from ..iconscore.icon_score_context import IconScoreContext
    from ..deploy.icon_score_deploy_engine import IconScoreDeployEngine


class IconScoreManager(object):
    def __init__(self, deploy_engine: 'IconScoreDeployEngine') -> None:
        self.__deploy_engine = deploy_engine

    def deploy(self,
               context: Optional['IconScoreContext'],
               from_score: 'Address',
               tx_hash: bytes) -> None:

        if from_score == GOVERNANCE_SCORE_ADDRESS:
            # switch
            score_addr = self.get_score_address_by_tx_hash(context, tx_hash)
            owner = self.get_owner(context, score_addr)
            tmp_sender = context.msg.sender
            context.msg.sender = owner
            try:
                self.__deploy_engine.deploy(context, tx_hash)
            finally:
                context.msg = tmp_sender
        else:
            raise ServerErrorException('Permission Error')

    def is_score_active(self,
                        context: Optional['IconScoreContext'],
                        icon_score_address: 'Address') -> bool:

        return self.__deploy_engine.icon_deploy_storage.is_score_active(context, icon_score_address)

    def get_owner(self,
                  context: Optional['IconScoreContext'],
                  icon_score_address: 'Address') -> Optional['Address']:
        return self.__deploy_engine.icon_deploy_storage.get_score_owner(context, icon_score_address)

    def get_tx_hashes_by_score_address(self,
                                       context: 'IconScoreContext',
                                       score_address: 'Address') -> Tuple[Optional[bytes], Optional[bytes]]:
        return self.__deploy_engine.icon_deploy_storage.get_tx_hashes_by_score_address(context, score_address)

    def get_score_address_by_tx_hash(self,
                                     context: 'IconScoreContext',
                                     tx_hash: bytes) -> Optional['Address']:
        return self.__deploy_engine.icon_deploy_storage.get_score_address_by_tx_hash(context, tx_hash)

