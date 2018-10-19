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

from ..base.address import GOVERNANCE_SCORE_ADDRESS
from ..base.exception import ServerErrorException, InvalidParamsException
from ..icon_constant import IconScoreContextType, DEFAULT_BYTE_SIZE, IconServiceFlag

if TYPE_CHECKING:
    from .icon_score_mapper import IconScoreMapper
    from ..deploy.icon_score_deploy_engine import IconScoreDeployEngine
    from .icon_score_base import IconScoreBase
    from ..base.address import Address
    from .icon_score_context import IconScoreContext


class IconScoreContextUtil(object):
    """Contains the useful information to process user's jsonrpc request
    """
    icon_score_mapper: 'IconScoreMapper' = None
    icon_score_deploy_engine: 'IconScoreDeployEngine'
    icon_service_flag: int = 0
    legacy_tbears_mode = False

    @classmethod
    def is_score_active(cls,
                        context: Optional['IconScoreContext'],
                        icon_score_address: 'Address') -> bool:
        return cls.icon_score_deploy_engine.icon_deploy_storage.is_score_active(context, icon_score_address)

    @classmethod
    def get_owner(cls,
                  context: Optional['IconScoreContext'],
                  icon_score_address: 'Address') -> Optional['Address']:
        return cls.icon_score_deploy_engine.icon_deploy_storage.get_score_owner(context, icon_score_address)

    @classmethod
    def deploy(cls, context: 'IconScoreContext', tx_hash: bytes) -> None:
        cls.icon_score_deploy_engine.deploy(context, tx_hash)

    @classmethod
    def get_icon_score(cls, context: 'IconScoreContext', address: 'Address') -> Optional['IconScoreBase']:
        score = None

        if context.type == IconScoreContextType.INVOKE:
            if context.new_icon_score_mapper is not None:
                score = context.new_icon_score_mapper.get(address)
        if score is None:
            score = cls._get_icon_score(context, address)

        return score

    @classmethod
    def _get_icon_score(cls, context: 'IconScoreContext', address: 'Address') -> Optional['IconScoreBase']:
        is_score_active = cls.icon_score_deploy_engine.icon_deploy_storage.is_score_active(context, address)

        if not is_score_active:
            raise InvalidParamsException(f'SCORE is inactive: {address}')

        deploy_info = cls.icon_score_deploy_engine.icon_deploy_storage.get_deploy_info(context, address)
        if deploy_info is None:
            current_tx_hash = None
        else:
            current_tx_hash = deploy_info.current_tx_hash

        if current_tx_hash is None:
            current_tx_hash = bytes(DEFAULT_BYTE_SIZE)

        return cls.icon_score_mapper.get_icon_score(address, current_tx_hash)

    @classmethod
    def try_score_package_validate(cls, address: 'Address', tx_hash: bytes):
        cls.icon_score_mapper.try_score_package_validate(address, tx_hash)

    @classmethod
    def validate_score_blacklist(cls, context: 'IconScoreContext', score_address: 'Address'):
        """Prevent SCOREs in blacklist

        :param context:
        :param score_address:
        """
        if not score_address.is_contract:
            raise ServerErrorException(f'Invalid SCORE address: {score_address}')

        # Gets the governance SCORE
        governance_score = cls.get_icon_score(context, GOVERNANCE_SCORE_ADDRESS)
        if governance_score is None:
            raise ServerErrorException(f'governance_score is None')

        if governance_score.isInScoreBlackList(score_address):
            raise ServerErrorException(f'SCORE in blacklist: {score_address}')

    @classmethod
    def validate_deployer(cls, context: 'IconScoreContext', deployer: 'Address'):
        """Check if a given deployer is allowed to deploy a SCORE

        :param context:
        :param deployer: EOA address to deploy a SCORE
        """
        # Gets the governance SCORE
        governance_score = cls.get_icon_score(context, GOVERNANCE_SCORE_ADDRESS)
        if governance_score is None:
            raise ServerErrorException(f'governance_score is None')

        if not governance_score.isDeployer(deployer):
            raise ServerErrorException(f'Invalid deployer: no permission (address: {deployer})')

    @classmethod
    def is_service_flag_on(cls, context: 'IconScoreContext', flag: 'IconServiceFlag'):
        service_flag = cls._get_service_flag(context)
        return cls._is_flag_on(service_flag, flag)

    @staticmethod
    def _is_flag_on(src_flag: int, dst_flag: int):
        return src_flag & dst_flag == dst_flag

    @classmethod
    def _get_service_flag(cls, context: 'IconScoreContext') -> int:
        governance_score = cls.get_icon_score(context, GOVERNANCE_SCORE_ADDRESS)
        if governance_score is None:
            raise ServerErrorException(f'governance_score is None')

        service_config = cls.icon_service_flag
        try:
            service_config = governance_score.service_config
        except AttributeError:
            pass
        return service_config

    @classmethod
    def get_revision(cls, context: 'IconScoreContext') -> int:
        try:
            governance_score = cls.get_icon_score(context, GOVERNANCE_SCORE_ADDRESS)
            if governance_score is not None:
                if hasattr(governance_score, 'revision_code'):
                    return governance_score.revision_code
        except:
            pass

        return 0

    @classmethod
    def get_tx_hashes_by_score_address(cls,
                                       context: 'IconScoreContext',
                                       score_address: 'Address') -> Tuple[Optional[bytes], Optional[bytes]]:
        warnings.warn("legacy function don't use.", DeprecationWarning, stacklevel=2)
        return cls.icon_score_deploy_engine.icon_deploy_storage.get_tx_hashes_by_score_address(context, score_address)

    @classmethod
    def get_score_address_by_tx_hash(cls,
                                     context: 'IconScoreContext',
                                     tx_hash: bytes) -> Optional['Address']:
        warnings.warn("legacy function don't use.", DeprecationWarning, stacklevel=2)
        return cls.icon_score_deploy_engine.icon_deploy_storage.get_score_address_by_tx_hash(context, tx_hash)

