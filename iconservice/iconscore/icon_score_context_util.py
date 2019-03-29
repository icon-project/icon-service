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

import warnings
from typing import TYPE_CHECKING, Optional, Tuple

from .icon_score_class_loader import IconScoreClassLoader
from .icon_score_mapper_object import IconScoreInfo
from .score_package_validator import ScorePackageValidator
from ..base.address import Address, ZERO_SCORE_ADDRESS
from ..base.address import GOVERNANCE_SCORE_ADDRESS
from ..base.exception import ScoreNotFoundException, AccessDeniedException
from ..database.db import IconScoreDatabase
from ..database.factory import ContextDatabaseFactory
from ..deploy import DeployState
from ..deploy.utils import get_package_name_by_address_and_tx_hash, get_score_deploy_path
from ..icon_constant import IconScoreContextType, IconServiceFlag

if TYPE_CHECKING:
    from .icon_score_context import IconScoreContext
    from .icon_score_base import IconScoreBase
    from .icon_score_mapper import IconScoreMapper
    from ..deploy.icon_score_deploy_storage import IconScoreDeployTXParams, IconScoreDeployInfo


class IconScoreContextUtil(object):
    """Contains the useful information to process user's jsonrpc request
    """

    @staticmethod
    def is_score_active(context: 'IconScoreContext', score_address: 'Address') -> bool:
        if not score_address.is_contract:
            return False
        if score_address == ZERO_SCORE_ADDRESS:
            return True

        deploy_info: 'IconScoreDeployInfo' = \
            context.icon_score_deploy_engine.icon_deploy_storage.get_deploy_info(context, score_address)

        if deploy_info is None:
            return False

        return deploy_info.deploy_state == DeployState.ACTIVE

    @staticmethod
    def get_owner(context: 'IconScoreContext',
                  score_address: 'Address') -> Optional['Address']:
        deploy_info: 'IconScoreDeployInfo' =\
            context.icon_score_deploy_engine.icon_deploy_storage.get_deploy_info(context, score_address)

        if deploy_info is None:
            return None

        return deploy_info.owner

    @staticmethod
    def deploy(context: 'IconScoreContext', tx_hash: bytes) -> None:
        context.icon_score_deploy_engine.deploy(context, tx_hash)

    @staticmethod
    def get_builtin_score(context: 'IconScoreContext', address: 'Address') -> 'IconScoreBase':
        score = IconScoreContextUtil.get_icon_score(context, address)

        if score is None:
            raise ScoreNotFoundException(f'Builtin SCORE not found: {address}')

        return score

    @staticmethod
    def get_icon_score(context: 'IconScoreContext', address: 'Address') -> Optional['IconScoreBase']:
        """Create a SCORE instance from SCORE class and return it

        :param context:
        :param address:
        :return:
        """
        score_info: 'IconScoreInfo' = IconScoreContextUtil.get_score_info(context, address)
        if score_info is None:
            return None

        # Create a SCORE instance every time
        # to prevent consensus failure by using wrong member variables in SCORE
        return score_info.get_score(context.revision)

    @staticmethod
    def get_score_info(context: 'IconScoreContext', address: 'Address') -> Optional['IconScoreInfo']:
        """Returns the score_info associated with the currently active score

        If IconScoreInfo instance is not found,
        create it from SCORE class and current tx_hash of the deployed SCORE

        :param context:
        :param address:
        :return:
        """
        score_mapper: 'IconScoreMapper' = context.icon_score_mapper
        deploy_info: 'IconScoreDeployInfo' = IconScoreContextUtil.get_deploy_info(context, address)

        if deploy_info is None or deploy_info.deploy_state != DeployState.ACTIVE:
            return None

        score_info: 'IconScoreInfo' = None

        if context.type == IconScoreContextType.INVOKE:
            score_info = context.new_icon_score_mapper.get(address)

        if score_info is None:
            score_info = score_mapper.get(address)

        current_tx_hash: bytes = deploy_info.current_tx_hash

        if score_info is None:
            score_info: 'IconScoreInfo' =\
                IconScoreContextUtil.create_score_info(context, address, current_tx_hash)
            score_mapper[address] = score_info
        elif score_info.tx_hash != current_tx_hash:
            raise AssertionError(
                f'scoreInfo.txHash(0x{score_info.tx_hash.hex()}) != txHash(0x{current_tx_hash.hex()})')

        return score_info

    @staticmethod
    def create_score_info(
            context: 'IconScoreContext', score_address: 'Address',
            tx_hash: bytes, score_db: 'IconScoreDatabase' = None) -> 'IconScoreInfo':

        score_class: type = IconScoreClassLoader.run(
            score_address, tx_hash, context.score_root_path)

        if score_db is None:
            context_db = ContextDatabaseFactory.create_by_address(score_address)
            score_db = IconScoreDatabase(score_address, context_db)

        # Cache a new IconScoreInfo instance
        return IconScoreInfo(score_class, score_db, tx_hash)

    @staticmethod
    def validate_score_package(context: 'IconScoreContext', address: 'Address', tx_hash: bytes) -> None:

        if not IconScoreContextUtil.is_service_flag_on(context, IconServiceFlag.SCORE_PACKAGE_VALIDATOR):
            return

        score_deploy_path: str = get_score_deploy_path(context.score_root_path, address, tx_hash)
        score_package_name: str = get_package_name_by_address_and_tx_hash(address, tx_hash)
        import_whitelist: dict = IconScoreContextUtil._get_import_whitelist(context)

        ScorePackageValidator.execute(import_whitelist, score_deploy_path, score_package_name)

    @staticmethod
    def _get_import_whitelist(context: 'IconScoreContext') -> dict:
        governance_score =\
            IconScoreContextUtil.get_builtin_score(context, GOVERNANCE_SCORE_ADDRESS)

        if hasattr(governance_score, 'import_white_list_cache'):
            return governance_score.import_white_list_cache

        return {"iconservice": ['*']}

    @staticmethod
    def validate_score_blacklist(context: 'IconScoreContext', score_address: 'Address') -> None:
        """Prevent SCOREs in blacklist

        :param context:
        :param score_address:
        """
        if not score_address.is_contract:
            return
        if score_address == ZERO_SCORE_ADDRESS:
            return

        # Gets the governance SCORE
        governance_score =\
            IconScoreContextUtil.get_builtin_score(context, GOVERNANCE_SCORE_ADDRESS)

        if governance_score is not None and governance_score.isInScoreBlackList(score_address):
            raise AccessDeniedException(f'SCORE in blacklist: {score_address}')

    @staticmethod
    def validate_deployer(context: 'IconScoreContext', deployer: 'Address') -> None:
        """Check if a given deployer is allowed to deploy a SCORE

        :param context:
        :param deployer: EOA address to deploy a SCORE
        """
        if not IconScoreContextUtil.is_service_flag_on(context, IconServiceFlag.DEPLOYER_WHITE_LIST):
            return

        # Gets the governance SCORE
        governance_score =\
            IconScoreContextUtil.get_builtin_score(context, GOVERNANCE_SCORE_ADDRESS)

        if not governance_score.isDeployer(deployer):
            raise AccessDeniedException(f'Invalid deployer: no permission (address: {deployer})')

    @staticmethod
    def is_service_flag_on(context: 'IconScoreContext', flag: 'IconServiceFlag') -> bool:
        service_flag = IconScoreContextUtil._get_service_flag(context)
        return IconScoreContextUtil._is_flag_on(service_flag, flag)

    @staticmethod
    def _is_flag_on(src_flag: int, dst_flag: int) -> bool:
        return src_flag & dst_flag == dst_flag

    @staticmethod
    def _get_service_flag(context: 'IconScoreContext') -> int:
        governance_score = \
            IconScoreContextUtil.get_builtin_score(context, GOVERNANCE_SCORE_ADDRESS)

        service_config = context.icon_service_flag
        try:
            service_config = governance_score.service_config
        except AttributeError:
            pass
        return service_config

    @staticmethod
    def get_tx_hashes_by_score_address(context: 'IconScoreContext',
                                       score_address: 'Address') -> Tuple[Optional[bytes], Optional[bytes]]:
        warnings.warn("legacy function don't use.", DeprecationWarning, stacklevel=2)
        return context.icon_score_deploy_engine.icon_deploy_storage.get_tx_hashes_by_score_address(
            context, score_address)

    @staticmethod
    def get_score_address_by_tx_hash(context: 'IconScoreContext',
                                     tx_hash: bytes) -> Optional['Address']:
        warnings.warn("legacy function don't use.", DeprecationWarning, stacklevel=2)
        return context.icon_score_deploy_engine.icon_deploy_storage.get_score_address_by_tx_hash(context, tx_hash)

    @staticmethod
    def get_deploy_tx_params(context: 'IconScoreContext', tx_hash: bytes) -> Optional['IconScoreDeployTXParams']:
        return context.icon_score_deploy_engine.icon_deploy_storage.get_deploy_tx_params(context, tx_hash)

    @staticmethod
    def get_deploy_info(context: 'IconScoreContext', address: 'Address') -> Optional['IconScoreDeployInfo']:
        return context.icon_score_deploy_engine.icon_deploy_storage.get_deploy_info(context, address)
