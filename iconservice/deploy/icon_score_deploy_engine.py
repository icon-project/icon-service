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

from collections import namedtuple
from os import path, symlink, makedirs
from shutil import copytree
from typing import TYPE_CHECKING, Callable

from iconcommons import Logger
from . import DeployType
from .icon_builtin_score_loader import IconBuiltinScoreLoader
from .icon_score_deploy_storage import IconScoreDeployStorage
from .icon_score_deployer import IconScoreDeployer
from ..base.address import Address
from ..base.address import ZERO_SCORE_ADDRESS
from ..base.exception import InvalidParamsException
from ..base.type_converter import TypeConverter
from ..icon_constant import IconDeployFlag, ICON_DEPLOY_LOG_TAG, DEFAULT_BYTE_SIZE

if TYPE_CHECKING:
    from ..iconscore.icon_score_context import IconScoreContext
    from .icon_score_deploy_storage import IconScoreDeployTXParams


class IconScoreDeployEngine(object):
    """It handles transactions to install, update and audit a SCORE
    """

    # This namedtuple should be used only in IconScoreDeployEngine.
    _Task = namedtuple(
        'Task',
        ('block', 'tx', 'msg', 'deploy_type', 'icon_score_address', 'data'))

    def __init__(self) -> None:
        """Constructor
        """
        self._flag = None
        self._icon_score_deploy_storage = None
        self._icon_score_deployer = None
        self._icon_builtin_score_loader = None
        self._icon_score_manager = None

    def open(self,
             score_root_path: str,
             flag: int,
             icon_deploy_storage: 'IconScoreDeployStorage') -> None:
        """open

        :param score_root_path:
        :param flag: flags composed by IconScoreDeployEngine
        :param icon_deploy_storage:
        """
        self._flag = flag
        self._icon_score_deploy_storage = icon_deploy_storage
        self._icon_score_deployer: IconScoreDeployer = IconScoreDeployer(score_root_path)

    @property
    def icon_deploy_storage(self):
        return self._icon_score_deploy_storage

    def _is_flag_on(self, flag: 'IconDeployFlag') -> bool:
        return (self._flag & flag) == flag

    def invoke(self,
               context: 'IconScoreContext',
               to: 'Address',
               icon_score_address: 'Address',
               data: dict) -> None:
        """Handle calldata contained in icx_sendTransaction message

        :param context:
        :param to:
        :param icon_score_address:
            cx0000000000000000000000000000000000000000 on install
            otherwise score address to update
        :param data: calldata
        """
        deploy_state: 'DeployType' = \
            DeployType.INSTALL if to == ZERO_SCORE_ADDRESS else DeployType.UPDATE

        try:
            self.write_deploy_info_and_tx_params(context, deploy_state, icon_score_address, data)
            if self._check_audit_ignore(context, icon_score_address):
                self.deploy(context, context.tx.hash)
        except BaseException as e:
            Logger.warning('write deploy info and tx params fail!!', ICON_DEPLOY_LOG_TAG)
            raise e

    def _check_audit_ignore(self, context: 'IconScoreContext', icon_score_address: Address):
        is_built_score = IconBuiltinScoreLoader.is_builtin_score(icon_score_address)
        is_owner = context.tx.origin == self._icon_score_deploy_storage.get_score_owner(context, icon_score_address)
        is_audit_enabled = self._is_flag_on(IconDeployFlag.ENABLE_DEPLOY_AUDIT)
        return not is_audit_enabled or all((is_built_score, is_owner))

    def deploy(self, context: 'IconScoreContext', tx_hash: bytes) -> None:
        """
        included audit deploy
        :param context:
        :param tx_hash:
        :return:
        """

        tx_params = self._icon_score_deploy_storage.get_deploy_tx_params(context, tx_hash)
        if tx_params is None:
            raise InvalidParamsException(f'tx_params is None : {tx_hash}')
        score_address = tx_params.score_address
        self._score_deploy(context, tx_params)
        self._icon_score_deploy_storage.update_score_info(context, score_address, tx_hash)

    def deploy_for_builtin(self, context: 'IconScoreContext',
                           score_address: 'Address',
                           src_score_path: str):
        self._score_deploy_for_builtin(context, score_address, src_score_path)

    def _score_deploy(self, context: 'IconScoreContext', tx_params: 'IconScoreDeployTXParams'):
        """
        :param tx_params: use deploy_data from IconScoreDeployTxParams info
        :return:
        """

        data = tx_params.deploy_data
        content_type = data.get('contentType')

        if content_type == 'application/tbears':
            # Install a score which is under development on tbears
            pass
        elif content_type == 'application/zip':
            data['content'] = bytes.fromhex(data['content'][2:])
        else:
            raise InvalidParamsException(
                f'Invalid contentType: {content_type}')

        self._on_deploy(context, tx_params)

    def _score_deploy_for_builtin(self, context: 'IconScoreContext',
                                  icon_score_address: 'Address',
                                  src_score_path: str):
        self._on_deploy_for_builtin(context, icon_score_address, src_score_path)

    def write_deploy_info_and_tx_params(self,
                                        context: 'IconScoreContext',
                                        deploy_type: 'DeployType',
                                        icon_score_address: 'Address',
                                        data: dict) -> None:
        """Write score deploy info to context db
        """

        self._icon_score_deploy_storage.put_deploy_info_and_tx_params(context,
                                                                      icon_score_address,
                                                                      deploy_type,
                                                                      context.tx.origin,
                                                                      context.tx.hash,
                                                                      data)

    def write_deploy_info_and_tx_params_for_builtin(self,
                                                    context: 'IconScoreContext',
                                                    icon_score_address: 'Address',
                                                    owner_address: 'Address') -> None:
        """Write score deploy info to context db for builtin
        """
        self._icon_score_deploy_storage.\
            put_deploy_info_and_tx_params_for_builtin(context, icon_score_address, owner_address)

    def _on_deploy_for_builtin(self,
                               context: 'IconScoreContext',
                               score_address: 'Address',
                               src_score_path: str) -> None:
        """Install an icon score for builtin
        """

        score_root_path = context.icon_score_mapper.score_root_path
        target_path = path.join(score_root_path,
                                score_address.to_bytes().hex())
        makedirs(target_path, exist_ok=True)

        _, next_tx_hash = self._icon_score_deploy_storage.get_tx_hashes_by_score_address(context, score_address)
        if next_tx_hash is None:
            next_tx_hash = bytes(DEFAULT_BYTE_SIZE)

        converted_tx_hash: str = f'0x{bytes.hex(next_tx_hash)}'
        target_path = path.join(target_path, converted_tx_hash)

        try:
            copytree(src_score_path, target_path)
        except FileExistsError:
            pass

        try:
            score = context.icon_score_mapper.load_score(score_address, next_tx_hash)
            if score is None:
                raise InvalidParamsException(f'score is None : {score_address}')

            self._initialize_score(on_deploy=score.on_install, params={})
        except BaseException as e:
            Logger.warning(f'load wait icon score fail!! address: {score_address}', ICON_DEPLOY_LOG_TAG)
            Logger.warning('revert to add wait icon score', ICON_DEPLOY_LOG_TAG)
            raise e

        context.icon_score_mapper.put_icon_info(score_address, score, next_tx_hash)

    def _on_deploy(self,
                   context: 'IconScoreContext',
                   tx_params: 'IconScoreDeployTXParams') -> None:
        """
        load score on memory
        write file system
        call on_deploy(install, update)

        :param tx_params: use deploy_data, score_address, tx_hash, deploy_type from IconScoreDeployTxParams
        :return:
        """

        data = tx_params.deploy_data
        score_address = tx_params.score_address
        content_type: str = data.get('contentType')
        content: bytes = data.get('content')
        params: dict = data.get('params', {})

        _, next_tx_hash =\
            self._icon_score_deploy_storage.get_tx_hashes_by_score_address(context, tx_params.score_address)

        if next_tx_hash is None:
            next_tx_hash = bytes(DEFAULT_BYTE_SIZE)

        if content_type == 'application/tbears':
            score_root_path = context.icon_score_mapper.score_root_path
            target_path = path.join(score_root_path,
                                    score_address.to_bytes().hex())
            makedirs(target_path, exist_ok=True)
            converted_tx_hash: str = f'0x{bytes.hex(next_tx_hash)}'
            target_path = path.join(target_path, converted_tx_hash)
            try:
                symlink(content, target_path, target_is_directory=True)
            except FileExistsError:
                pass
        else:
            self._icon_score_deployer.deploy(
                address=score_address,
                data=content,
                tx_hash=next_tx_hash)
        try:
            score = context.new_icon_score_mapper.load_score(score_address, next_tx_hash)
            if score is None:
                raise InvalidParamsException(f'score is None : {score_address}')

            deploy_type = tx_params.deploy_type
            if deploy_type == DeployType.INSTALL:
                on_deploy = score.on_install
            elif deploy_type == DeployType.UPDATE:
                on_deploy = score.on_update
            else:
                on_deploy = None

            self._initialize_score(on_deploy=on_deploy, params=params)
        except BaseException as e:
            Logger.warning(f'load wait icon score fail!! address: {score_address}', ICON_DEPLOY_LOG_TAG)
            Logger.warning('revert to add wait icon score', ICON_DEPLOY_LOG_TAG)
            raise e

        context.icon_score_mapper.put_icon_info(score_address, score, next_tx_hash)

    @staticmethod
    def _initialize_score(on_deploy: Callable[[dict], None],
                          params: dict) -> None:
        """on_install() or on_update() of score is called
        only once when installed or updated

        :param on_deploy: score.on_install() or score.on_update()
        :param params: paramters passed to on_install or on_update()
        """

        annotations = TypeConverter.make_annotations_from_method(on_deploy)
        TypeConverter.convert_data_params(annotations, params)
        on_deploy(**params)
