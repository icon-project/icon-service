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
from typing import TYPE_CHECKING

from iconcommons import Logger
from . import DeployType
from .icon_score_deployer import IconScoreDeployer
from .utils import remove_path, get_score_deploy_path, get_score_path
from ..base.address import Address
from ..base.address import ZERO_SCORE_ADDRESS
from ..base.exception import InvalidParamsException
from ..base.message import Message
from ..base.type_converter import TypeConverter
from ..icon_constant import IconServiceFlag, ICON_DEPLOY_LOG_TAG, REVISION_2, REVISION_3
from ..iconscore.icon_score_api_generator import ScoreApiGenerator
from ..iconscore.icon_score_context_util import IconScoreContextUtil
from ..iconscore.icon_score_mapper_object import IconScoreInfo
from ..utils import is_builtin_score

if TYPE_CHECKING:
    from .icon_score_deploy_storage import IconScoreDeployInfo
    from .icon_score_deploy_storage import IconScoreDeployStorage
    from .icon_score_deploy_storage import IconScoreDeployTXParams
    from ..iconscore.icon_score_context import IconScoreContext
    from ..iconscore.icon_score_mapper import IconScoreMapper
    from ..iconscore.icon_score_base import IconScoreBase


class IconScoreDeployEngine(object):
    """It handles transactions to install, update and audit a SCORE
    """

    def __init__(self) -> None:
        """Constructor
        """
        self._score_deploy_storage: 'IconScoreDeployStorage' = None

    def open(self, score_deploy_storage: 'IconScoreDeployStorage') -> None:
        """open
        :param score_deploy_storage:
        """
        self._score_deploy_storage = score_deploy_storage

    @property
    def icon_deploy_storage(self) -> 'IconScoreDeployStorage':
        return self._score_deploy_storage

    def invoke(self,
               context: 'IconScoreContext',
               to: 'Address',
               icon_score_address: 'Address',
               data: dict) -> None:
        """Handle data contained in icx_sendTransaction message
        :param context:
        :param to:
        :param icon_score_address:
            cx0000000000000000000000000000000000000000 on install
            otherwise score address to update
        :param data: SCORE deploy data
        """
        assert icon_score_address is not None
        assert icon_score_address != ZERO_SCORE_ADDRESS
        assert icon_score_address.is_contract

        if icon_score_address in (None, ZERO_SCORE_ADDRESS):
            raise InvalidParamsException(f'Invalid SCORE address: {icon_score_address}')

        try:
            IconScoreContextUtil.validate_score_blacklist(context, icon_score_address)
            IconScoreContextUtil.validate_deployer(context, context.tx.origin)

            deploy_type: 'DeployType' = \
                DeployType.INSTALL if to == ZERO_SCORE_ADDRESS else DeployType.UPDATE

            self._score_deploy_storage.put_deploy_info_and_tx_params(
                context, icon_score_address, deploy_type,
                context.tx.origin, context.tx.hash, data)

            if not self._is_audit_needed(context, icon_score_address):
                self.deploy(context, context.tx.hash)

        except BaseException as e:
            Logger.warning('Failed to write deploy info and tx params', ICON_DEPLOY_LOG_TAG)
            raise e

    @staticmethod
    def _is_audit_needed(context: 'IconScoreContext', score_address: Address) -> bool:
        """Check whether audit process is needed or not
        :param context:
        :param score_address:
        :return: True(needed) False(not needed)
        """
        if context.revision >= REVISION_2:
            is_system_score = is_builtin_score(str(score_address))
        else:
            is_system_score = False

        # FiXME: SCORE owner check should be done before calling self._is_audit_needed().
        is_owner: bool = context.tx.origin == IconScoreContextUtil.get_owner(context, score_address)
        is_audit_enabled: bool = IconScoreContextUtil.is_service_flag_on(context, IconServiceFlag.AUDIT)

        return is_audit_enabled and not (is_system_score and is_owner)

    def deploy(self, context: 'IconScoreContext', tx_hash: bytes) -> None:
        """
        1. Convert a content from hex string to bytes
        2. Decompress zipped SCORE code and write it to filesystem
        3. Import the decompressed SCORE code
        4. Create a SCORE instance from the code
        5. Run on_install() or on_update() method in the SCORE
        6. Update the deployed SCORE info to stateDB
        :param context:
        :param tx_hash:
        """

        tx_params: 'IconScoreDeployTXParams' =\
            self._score_deploy_storage.get_deploy_tx_params(context, tx_hash)
        if tx_params is None:
            raise InvalidParamsException(f'tx_params is None: 0x{tx_hash.hex()}')

        score_address: 'Address' = tx_params.score_address
        self._score_deploy(context, tx_params)
        self._score_deploy_storage.update_score_info(context, score_address, tx_hash)

    def _score_deploy(self, context: 'IconScoreContext', tx_params: 'IconScoreDeployTXParams'):
        """
        :param tx_params: use deploy_data from IconScoreDeployTxParams info
        :return:
        """

        data: dict = tx_params.deploy_data
        content_type: str = data.get('contentType')

        if content_type == 'application/tbears':
            if not context.legacy_tbears_mode:
                raise InvalidParamsException(f'Invalid contentType: application/tbears')
        elif content_type == 'application/zip':
            data['content'] = bytes.fromhex(data['content'][2:])
        else:
            raise InvalidParamsException(
                f'Invalid contentType: {content_type}')

        self._on_deploy(context, tx_params)

    def _on_deploy(self,
                   context: 'IconScoreContext',
                   tx_params: 'IconScoreDeployTXParams') -> None:
        """
        Decompress a SCORE zip file and write them to file system
        Create a SCORE instance from SCORE class
        Call a SCORE initialization function (on_install or on_update)
        :param tx_params: use deploy_data, score_address, tx_hash, deploy_type from IconScoreDeployTxParams
        :return:
        """

        data = tx_params.deploy_data
        score_address = tx_params.score_address
        params: dict = data.get('params', {})

        deploy_info: 'IconScoreDeployInfo' =\
            self.icon_deploy_storage.get_deploy_info(context, tx_params.score_address)
        next_tx_hash: bytes = deploy_info.next_tx_hash

        self._write_score_to_filesystem(context, score_address, next_tx_hash, data)

        backup_msg = context.msg
        backup_tx = context.tx
        new_score_mapper: 'IconScoreMapper' = context.new_icon_score_mapper

        try:
            IconScoreContextUtil.validate_score_package(context, score_address, next_tx_hash)

            score_info: 'IconScoreInfo' =\
                self._create_score_info(context, score_address, next_tx_hash)
            # score_info.get_score() returns a cached or created score instance
            # according to context.revision.
            score: 'IconScoreBase' = score_info.get_score(context.revision)
            ScoreApiGenerator.check_on_deploy(context, score)

            # owner is set in IconScoreBase.__init__()
            context.msg = Message(sender=score.owner)
            context.tx = None

            self._initialize_score(tx_params.deploy_type, score, params)
            new_score_mapper[score_address] = score_info
        except BaseException as e:
            Logger.warning(f'Failed to deploy a SCORE: {score_address}', ICON_DEPLOY_LOG_TAG)
            raise e
        finally:
            context.msg = backup_msg
            context.tx = backup_tx

    def _write_score_to_filesystem(self, context: 'IconScoreContext',
                                   score_address: 'Address', tx_hash: bytes, deploy_data: dict):

        content_type: str = deploy_data.get('contentType')
        content = deploy_data.get('content')

        if content_type == 'application/tbears':
            write_score_to_score_deploy_path: callable =\
                self._write_score_to_score_deploy_path_on_tbears_mode
        else:
            write_score_to_score_deploy_path: callable =\
                self._write_score_to_score_deploy_path

        write_score_to_score_deploy_path(context, score_address, tx_hash, content)

    @staticmethod
    def _create_score_info(context: 'IconScoreContext',
                           score_address: 'Address', tx_hash: bytes) -> 'IconScoreInfo':
        """Create the score_info instance associated with the SCORE to deploy
        :param context:
        :param score_address:
        :param tx_hash:
        :return:
        """
        current_score_info: 'IconScoreInfo' =\
            IconScoreContextUtil.get_score_info(context, score_address)

        # Reuse score_db if it has already existed.
        score_db = None
        if current_score_info is not None:
            score_db = current_score_info.score_db

        return IconScoreContextUtil.create_score_info(context, score_address, tx_hash, score_db)

    @staticmethod
    def _write_score_to_score_deploy_path_on_tbears_mode(
            context: 'IconScoreContext', score_address: 'Address', tx_hash: bytes, content: bytes):
        score_root_path: str = context.score_root_path
        score_path: str = get_score_path(score_root_path, score_address)
        os.makedirs(score_path, exist_ok=True)

        score_deploy_path: str = get_score_deploy_path(score_root_path, score_address, tx_hash)
        try:
            os.symlink(content, score_deploy_path, target_is_directory=True)
        except FileExistsError:
            pass

    @staticmethod
    def _write_score_to_score_deploy_path(context: 'IconScoreContext',
                                          score_address: 'Address', tx_hash: bytes, content: bytes):
        """Write SCORE code to file system

        :param context: IconScoreContext instance
        :param score_address: score address
        :param tx_hash: transaction hash
        :param content: zipped SCORE code data
        :return:
        """
        revision: int = context.revision

        # score_root_path is the directory which contains all deployed scores.
        score_root_path: str = context.score_root_path
        score_deploy_path: str = get_score_deploy_path(score_root_path, score_address, tx_hash)

        if revision >= REVISION_3:
            # If the path to deploy a score has been present, remove it before deploying.
            score_root_path: str = context.score_root_path
            score_path: str =\
                os.path.join(score_root_path, score_address.to_bytes().hex(), f'0x{tx_hash.hex()}')
            remove_path(score_path)

        if revision >= REVISION_2:
            IconScoreDeployer.deploy(score_deploy_path, content, revision)
        else:
            IconScoreDeployer.deploy_legacy(score_deploy_path, content)

    @staticmethod
    def _initialize_score(deploy_type: DeployType, score: 'IconScoreBase', params: dict):
        """Call on_install() or on_update() of a SCORE
        only once when installing or updating it
        :param deploy_type: DeployType.INSTALL or DeployType.UPDATE
        :param score: SCORE to install or update
        :param params: parameters passed to on_install or on_update()
        """
        if deploy_type == DeployType.INSTALL:
            on_init = score.on_install
        elif deploy_type == DeployType.UPDATE:
            on_init = score.on_update
        else:
            raise InvalidParamsException(f'Invalid deployType: {deploy_type}')

        annotations = TypeConverter.make_annotations_from_method(on_init)
        TypeConverter.convert_data_params(annotations, params)
        on_init(**params)

