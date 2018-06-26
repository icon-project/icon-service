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


from typing import TYPE_CHECKING

from ..base.address import Address
from . import DeployType

if TYPE_CHECKING:
    from ..database.db import ContextDatabase


class IconScoreDeployInfo(object):

    def __init__(self,
                 deploy_type: 'DeployType',
                 score_address: 'Address'=None,
                 owner: 'Address'=None,
                 tx_hash: str=None,
                 params: dict=None):
        self.score_address = score_address
        self.owner = owner
        self.tx_hash = tx_hash
        self.params = params
        self.type = deploy_type


class IconScoreDeployStorage(object):
    def __init__(self, db: 'ContextDatabase') -> None:
        """Constructor

        :param db:
        """
        super().__init__()
        self._db = db

    def get_score_address_by_tx_hash(self, tx_hash: str):
        """Returns score address with SCORE install txHash

        :param tx_hash: SCORE deploy txHash
        :return: None or Address instance
        """
        pass

    def get_score_deploy_info_by_tx_hash(
            self, tx_hash: str) -> 'IconScoreDeployInfo':
        pass

    def get_score_deploy_info_by_address(
            self, address: 'Address') -> 'IconScoreDeployInfo':
        pass

    def put_score_deploy_info(self, deploy_info: 'IconScoreDeployInfo') -> None:
        """TODO

        :param deploy_info:
        :return:
        """
        pass
