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

import os
from shutil import copytree
from typing import TYPE_CHECKING

from iconcommons.logger import Logger
from iconservice.base.address import Address
from iconservice.base.exception import AccessDeniedException
from iconservice.deploy.storage import IconScoreDeployInfo, DeployState
from iconservice.deploy.utils import remove_path
from iconservice.icon_constant import BUILTIN_SCORE_ADDRESS_MAPPER, ZERO_TX_HASH, ICON_DEPLOY_LOG_TAG
from iconservice.iconscore.icon_score_context_util import IconScoreContextUtil

if TYPE_CHECKING:
    from iconservice.iconscore.icon_score_base import IconScoreBase
    from iconservice.iconscore.icon_score_context import IconScoreContext
    from iconservice.iconscore.icon_score_mapper_object import IconScoreInfo


class IconBuiltinScoreLoader(object):
    """Before activating icon_service_engine, deploy builtin scores which has never been deployed.
    """

    @staticmethod
    def _pre_builtin_score_root_path():
        root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../'))
        return os.path.join(root_path, 'builtin_scores')

    @staticmethod
    def load_builtin_scores(context: 'IconScoreContext', builtin_score_owner: 'Address'):
        for score_name, value in BUILTIN_SCORE_ADDRESS_MAPPER.items():
            score_address = Address.from_string(value)

            # If builtin score has been already deployed, exit.
            if IconScoreContextUtil.is_score_active(context, score_address):
                IconBuiltinScoreLoader._load_score(context, score_address, builtin_score_owner)
            else:
                IconBuiltinScoreLoader._deploy_score(
                    context, score_name, score_address, builtin_score_owner)

    @staticmethod
    def _load_score(context: 'IconScoreContext',
                    score_address: 'Address', builtin_score_owner: 'Address'):
        score: 'IconScoreBase' = IconScoreContextUtil.get_icon_score(context, score_address)
        assert score is not None

        if score.owner != builtin_score_owner:
            raise AccessDeniedException(
                f'score.owner({score.owner}) != builtin_score_owner({builtin_score_owner})')

    @staticmethod
    def _deploy_score(context: 'IconScoreContext',
                      score_name: str,
                      score_address: 'Address',
                      builtin_score_owner: 'Address'):

        score_source_path_in_iconservice: str = os.path.join(
            IconBuiltinScoreLoader._pre_builtin_score_root_path(), score_name)

        # Save deploy_info for a builtin score to storage.
        deploy_info = IconScoreDeployInfo(
            score_address=score_address,
            deploy_state=DeployState.ACTIVE,
            owner=builtin_score_owner,
            current_tx_hash=ZERO_TX_HASH,
            next_tx_hash=ZERO_TX_HASH)
        context.storage.deploy.put_deploy_info(context, deploy_info)

        tx_hash: bytes = deploy_info.current_tx_hash

        # score_path is score_root_path/score_address/ directory.
        score_path: str = os.path.join(
            context.score_root_path, score_address.to_bytes().hex())

        # Make a directory for a builtin score with a given score_address.
        os.makedirs(score_path, exist_ok=True)

        try:
            score_deploy_path: str = os.path.join(score_path, f'0x{tx_hash.hex()}')

            # remove_path() supports directory as well as file.
            remove_path(score_deploy_path)
            # Copy builtin score source files from iconservice package to score_deploy_path.
            copytree(score_source_path_in_iconservice, score_deploy_path)
        except FileExistsError:
            pass

        try:
            # Import score class from deployed builtin score sources
            score_info: 'IconScoreInfo' =\
                IconScoreContextUtil.create_score_info(context, score_address, tx_hash)

            # Create a score instance from the imported score class.
            score = score_info.create_score()

            # Call on_install() to initialize the score database of the builtin score.
            score.on_install()
        except BaseException as e:
            Logger.exception(
                f'Failed to deploy a builtin score: {score_address}\n{str(e)}',
                ICON_DEPLOY_LOG_TAG)
            raise e
