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

from collections import namedtuple
from os import path, symlink, makedirs
from typing import TYPE_CHECKING, Callable

from . import DeployType, make_score_id
from .icon_builtin_score_loader import IconBuiltinScoreLoader
from .icon_score_deploy_storage import IconScoreDeployStorage, IconScoreDeployTXParams
from .icon_score_deployer import IconScoreDeployer
from ..base.address import Address
from ..base.address import ZERO_SCORE_ADDRESS
from ..base.exception import InvalidParamsException
from ..base.type_converter import TypeConverter
from ..icon_constant import IconDeployFlag
from iconcommons import Logger

if TYPE_CHECKING:
    from ..iconscore.icon_score_context import IconScoreContext
    from ..iconscore.icon_score_info_mapper import IconScoreInfoMapper


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
        self._icon_score_mapper = None
        self._icon_score_deployer = None
        self._icon_builtin_score_loader = None
        self._icon_score_manager = None

    def open(self,
             score_root_path: str,
             flag: int,
             icon_score_mapper: 'IconScoreInfoMapper',
             icon_deploy_storage: 'IconScoreDeployStorage') -> None:
        """open

        :param score_root_path:
        :param flag: flags composed by IconScoreDeployEngine
        :param icon_score_mapper:
        :param icon_deploy_storage:
        """
        self._flag = flag
        self._icon_score_deploy_storage = icon_deploy_storage
        self._icon_score_mapper = icon_score_mapper
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
            Logger.exception(e)
            raise e

    def _check_audit_ignore(self, context: 'IconScoreContext', icon_score_address: Address):
        is_built_score = IconBuiltinScoreLoader.is_builtin_score(icon_score_address)
        is_owner = context.tx.origin == self._icon_score_deploy_storage.get_score_owner(context, icon_score_address)
        is_audit_enabled = self._is_flag_on(IconDeployFlag.ENABLE_DEPLOY_AUDIT)
        return not is_audit_enabled or all((is_built_score, is_owner))

    def deploy(self,
               context: 'IconScoreContext', # audit
               tx_hash: bytes) -> None:

        tx_params = self._icon_score_deploy_storage.get_deploy_tx_params(context, tx_hash)
        if tx_params is None:
            raise InvalidParamsException(f'tx_params is None : {tx_hash}')
        score_address = tx_params.score_address
        self._score_deploy(context, tx_params)

        self._icon_score_deploy_storage.update_score_info(
            context, score_address, tx_hash)
        deploy_info = self._icon_score_deploy_storage.get_deploy_info(context, score_address)
        if deploy_info is None:
            raise InvalidParamsException(f'deploy_info is None : {score_address}')

    def deploy_for_builtin(self, score_address: 'Address', src_score_path: str):
        self._score_deploy_for_builtin(score_address, src_score_path)

    def _score_deploy(self,
                      context: 'IconScoreContext',
                      tx_params: 'IconScoreDeployTXParams'):

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

    def _score_deploy_for_builtin(self, icon_score_address: 'Address',
                                  src_score_path: str):
        self._on_deploy_for_builtin(icon_score_address, src_score_path)

    def commit(self, context: 'IconScoreContext') -> None:
        pass

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
                                                    icon_score_address: 'Address',
                                                    owner_address: 'Address') -> None:
        """Write score deploy info to context db for builtin
        """
        self._icon_score_deploy_storage.put_deploy_info_and_tx_params_for_builtin(icon_score_address, owner_address)

    def _on_deploy_for_builtin(self,
                               icon_score_address: 'Address',
                               src_score_path: str) -> None:
        """Install an icon score for builtin
        """

        score_root_path = self._icon_score_mapper.score_root_path
        target_path = path.join(score_root_path,
                                icon_score_address.to_bytes().hex())
        makedirs(target_path, exist_ok=True)
        score_id = make_score_id(0, 0)
        target_path = path.join(
            target_path, score_id)
        try:
            symlink(src_score_path, target_path, target_is_directory=True)
        except FileExistsError:
            pass

        score = self._icon_score_mapper.load_wait_icon_score(icon_score_address, score_id)
        if score is None:
            raise InvalidParamsException(f'score is None : {icon_score_address}')

        self._initialize_score(
            on_deploy=score.on_install,
            params={})

    def _on_deploy(self,
                   context: 'IconScoreContext',
                   tx_params: 'IconScoreDeployTXParams') -> None:
        """Install an icon score on commit

                Owner check has already been done in IconServiceEngine
                - Install IconScore package file to file system

                """
        data = tx_params.deploy_data
        score_address = tx_params.score_address
        content_type: str = data.get('contentType')
        content: bytes = data.get('content')
        params: dict = data.get('params', {})

        if content_type == 'application/tbears':
            score_root_path = self._icon_score_mapper.score_root_path
            target_path = path.join(score_root_path,
                                    score_address.to_bytes().hex())
            makedirs(target_path, exist_ok=True)
            score_id = tx_params.score_id
            target_path = path.join(target_path, score_id)
            try:
                symlink(content, target_path, target_is_directory=True)
            except FileExistsError:
                pass
        else:
            self._icon_score_deployer.deploy(
                address=score_address,
                data=content,
                block_height=context.block.height,
                transaction_index=context.tx.index)

        score_id = tx_params.score_id
        score = self._icon_score_mapper.load_wait_icon_score(score_address, score_id)
        if score is None:
            raise InvalidParamsException(f'score is None : {score_address}')

        deploy_type = tx_params.deploy_type
        on_deploy = None
        if deploy_type == DeployType.INSTALL:
            on_deploy = score.on_install
        elif deploy_type == DeployType.UPDATE:
            on_deploy = score.on_update

        self._initialize_score(
            on_deploy=on_deploy,
            params=params)

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

    def rollback(self) -> None:
        """It is called when the previous block has been canceled

        Rollback install, update or remove tasks cached in the previous block
        """
        pass
