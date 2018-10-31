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

from os import path, symlink, makedirs, rename
from shutil import copytree
from time import time
from typing import TYPE_CHECKING, Callable

from iconcommons import Logger
from . import DeployType
from .icon_score_deploy_storage import IconScoreDeployStorage
from .icon_score_deployer import IconScoreDeployer
from ..base.address import Address
from ..base.address import ZERO_SCORE_ADDRESS
from ..base.exception import InvalidParamsException, ServerErrorException
from ..base.message import Message
from ..base.type_converter import TypeConverter
from ..icon_constant import IconServiceFlag, ICON_DEPLOY_LOG_TAG, DEFAULT_BYTE_SIZE, REVISION_2, REVISION_3
from ..iconscore.icon_score_context_util import IconScoreContextUtil
from ..utils import is_builtin_score

if TYPE_CHECKING:
    from ..iconscore.icon_score_context import IconScoreContext
    from .icon_score_deploy_storage import IconScoreDeployTXParams


class IconScoreDeployEngine(object):
    """It handles transactions to install, update and audit a SCORE
    """

    def __init__(self) -> None:
        """Constructor
        """
        self._icon_score_deploy_storage: 'IconScoreDeployStorage' = None
        self._icon_score_deployer = None
        self._icon_builtin_score_loader = None

    def open(self,
             score_root_path: str,
             icon_deploy_storage: 'IconScoreDeployStorage') -> None:
        """open

        :param score_root_path:
        :param icon_deploy_storage:
        """
        self._icon_score_deploy_storage = icon_deploy_storage
        self._icon_score_deployer: IconScoreDeployer = IconScoreDeployer(score_root_path)

    @property
    def icon_deploy_storage(self) -> 'IconScoreDeployStorage':
        return self._icon_score_deploy_storage

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
        assert icon_score_address is not None
        assert icon_score_address != ZERO_SCORE_ADDRESS
        assert icon_score_address.is_contract

        if icon_score_address in (None, ZERO_SCORE_ADDRESS):
            raise ServerErrorException(f'Invalid SCORE address: {icon_score_address}')

        deploy_type: 'DeployType' = \
            DeployType.INSTALL if to == ZERO_SCORE_ADDRESS else DeployType.UPDATE

        try:
            IconScoreContextUtil.validate_score_blacklist(context, icon_score_address)

            if IconScoreContextUtil.is_service_flag_on(context, IconServiceFlag.DEPLOYER_WHITE_LIST):
                IconScoreContextUtil.validate_deployer(context, context.tx.origin)

            self.write_deploy_info_and_tx_params(context, deploy_type, icon_score_address, data)

            if self._check_audit_ignore(context, icon_score_address):
                self.deploy(context, context.tx.hash)
        except BaseException as e:
            Logger.warning('Failed to write deploy info and tx params', ICON_DEPLOY_LOG_TAG)
            raise e

    @staticmethod
    def _check_audit_ignore(context: 'IconScoreContext', icon_score_address: Address):
        """Skip audit process for SystemSCORE update

        :param context:
        :param icon_score_address:
        :return:
        """
        if IconScoreContextUtil.get_revision(context) >= REVISION_2:
            is_system_score = is_builtin_score(str(icon_score_address))
        else:
            is_system_score = False

        is_owner = context.tx.origin == IconScoreContextUtil.get_owner(context, icon_score_address)
        is_audit_enabled = IconScoreContextUtil.is_service_flag_on(context, IconServiceFlag.AUDIT)
        return not is_audit_enabled or all((is_system_score, is_owner))

    def deploy(self, context: 'IconScoreContext', tx_hash: bytes) -> None:
        """
        included audit deploy
        :param context:
        :param tx_hash:
        :return:
        """

        tx_params = IconScoreContextUtil.get_deploy_tx_params(context, tx_hash)
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
            if not context.legacy_tbears_mode:
                raise InvalidParamsException(f"can't symlink deploy")
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

        score_root_path = IconScoreContextUtil.get_score_root_path(context)
        target_path = path.join(score_root_path,
                                score_address.to_bytes().hex())
        makedirs(target_path, exist_ok=True)

        deploy_info = IconScoreContextUtil.get_deploy_info(context, score_address)
        if deploy_info is None:
            next_tx_hash = None
        else:
            next_tx_hash = deploy_info.next_tx_hash
        if next_tx_hash is None:
            next_tx_hash = bytes(DEFAULT_BYTE_SIZE)

        converted_tx_hash: str = f'0x{bytes.hex(next_tx_hash)}'
        score_path = path.join(target_path, converted_tx_hash)

        DirectoryNameChanger.rename_directory(score_path)

        try:
            copytree(src_score_path, score_path)
        except FileExistsError:
            pass

        try:
            score = IconScoreContextUtil.load_score(context, score_address, next_tx_hash)
            if score is None:
                raise InvalidParamsException(f'score is None : {score_address}')

            self._initialize_score(on_deploy=score.on_install, params={})
        except BaseException as e:
            Logger.warning(f'load wait icon score fail!! address: {score_address}', ICON_DEPLOY_LOG_TAG)
            Logger.warning('revert to add wait icon score', ICON_DEPLOY_LOG_TAG)
            raise e

        IconScoreContextUtil.put_score_info(context, score_address, score, next_tx_hash)

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

        deploy_info = IconScoreContextUtil.get_deploy_info(context, tx_params.score_address)
        if deploy_info is None:
            next_tx_hash = None
        else:
            next_tx_hash = deploy_info.next_tx_hash
        if next_tx_hash is None:
            next_tx_hash = bytes(DEFAULT_BYTE_SIZE)

        if content_type == 'application/tbears':
            score_root_path = IconScoreContextUtil.get_score_root_path(context)
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
            revision = IconScoreContextUtil.get_revision(context)

            if revision >= REVISION_3:
                install_path = DirectoryNameChanger.get_score_path_by_address_and_tx_hash(
                    self._icon_score_deployer.score_root_path, score_address, next_tx_hash)
                DirectoryNameChanger.rename_directory(install_path)
                self._icon_score_deployer.deploy(
                    address=score_address,
                    data=content,
                    tx_hash=next_tx_hash)
            elif revision == REVISION_2:
                self._icon_score_deployer.deploy(
                    address=score_address,
                    data=content,
                    tx_hash=next_tx_hash)
            else:
                self._icon_score_deployer.deploy_legacy(
                    address=score_address,
                    data=content,
                    tx_hash=next_tx_hash)

        backup_msg = context.msg
        backup_tx = context.tx

        try:
            if IconScoreContextUtil.is_service_flag_on(context, IconServiceFlag.SCORE_PACKAGE_VALIDATOR):
                IconScoreContextUtil.try_score_package_validate(context, score_address, next_tx_hash)
            score = IconScoreContextUtil.load_score(context, score_address, next_tx_hash)
            if score is None:
                raise InvalidParamsException(f'score is None : {score_address}')

            deploy_type = tx_params.deploy_type
            if deploy_type == DeployType.INSTALL:
                on_deploy = score.on_install
            elif deploy_type == DeployType.UPDATE:
                on_deploy = score.on_update
            else:
                on_deploy = None

            context.msg = Message(sender=score.owner)
            context.tx = None

            self._initialize_score(on_deploy=on_deploy, params=params)
        except BaseException as e:
            Logger.warning(f'load wait icon score fail!! address: {score_address}', ICON_DEPLOY_LOG_TAG)
            Logger.warning('revert to add wait icon score', ICON_DEPLOY_LOG_TAG)
            raise e
        finally:
            context.msg = backup_msg
            context.tx = backup_tx

        IconScoreContextUtil.put_score_info(context, score_address, score, next_tx_hash)

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


class DirectoryNameChanger:
    """Rename file/directory existent in a path where SCORE will be deployed"""
    counter = 0

    @classmethod
    def rename_directory(cls, score_path: str):
        """Rename file/directory

        :param score_path: Path where SCORE will be deployed
        """
        if path.exists(score_path):
            cls.counter += 1
            rename(score_path, f"{score_path}{int(time()*10**6)}{cls.counter}_garbage_score")

    @staticmethod
    def get_score_path_by_address_and_tx_hash(score_root: str, address: 'Address', tx_hash: bytes) -> str:
        """Get SCORE's path by given parameters

        :param score_root: The path where all SCOREs will be deployed
        :param address: Address of SCORE
        :param tx_hash: Hash value of the transaction that deploy SCORE
        :return: The path where SCORE will be deployed
        """
        score_root_path = path.join(score_root, address.to_bytes().hex())
        converted_tx_hash = f'0x{bytes.hex(tx_hash)}'
        install_path = path.join(score_root_path, converted_tx_hash)
        return install_path
