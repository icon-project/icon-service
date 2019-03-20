# -*- coding: utf-8 -*-

# Copyright 2019 ICON Foundation
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

import typing
from typing import List, Dict, Optional

from ..base.exception import InvalidRequestException
from ..icx.icx_engine import IcxEngine
from ..icx.icx_storage import IcxStorage

if typing.TYPE_CHECKING:
    from ..base.address import Address
    from ..deploy.icon_score_deploy_storage import IconScoreDeployInfo
    from ..deploy.icon_score_deploy_storage import IconScoreDeployStorage
    from ..iconscore.icon_score_context import IconScoreContext


class Deposit:
    """
    Deposit information
    """

    def __init__(self, deposit_id: bytes, sender: 'Address', score_address: 'Address'):
        # deposit id, should be tx hash of deposit transaction
        self.id: bytes = deposit_id
        # sender address
        self.sender: 'Address' = sender
        # target SCORE address
        self.score_address: 'Address' = score_address
        # amount of ICXs in loop
        self.amount: int = 0
        # created time in block
        self.created: int = 0
        # expires time in block
        self.expires: int = 0
        # issued amount of virtual STEPs
        self.virtual_step_issued: int = 0
        # used amount of virtual STEPs
        self.virtual_step_used: int = 0


class ScoreFeeInfo:
    """
    Fee information of a SCORE
    """

    def __init__(self, score_address: 'Address'):
        # SCORE address
        self.score_address: 'Address' = score_address
        # List of deposits
        self.deposits: List[Deposit] = []
        # fee sharing ratio that SCORE pays
        self.sharing_ratio: int = 0
        # available virtual STEPs to use
        self.virtual_step: int = 0


class FeeManager:
    """
    Presenter of the fee operation.

    [Role]
    - State DB CRUD
    - Business logic (inc. Calculation)
    """

    def __init__(self,
                 deploy_storage: 'IconScoreDeployStorage',
                 icx_storage: 'IcxStorage',
                 icx_engine: 'IcxEngine'):

        self._deploy_storage = deploy_storage
        self._icx_storage = icx_storage
        self._icx_engine = icx_engine

    def set_fee_sharing_ratio(self,
                              context: 'IconScoreContext',
                              sender: 'Address',
                              score_address: 'Address',
                              ratio: int) -> None:
        """
        Sets fee sharing ratio that SCORE pays.

        :param context: IconScoreContext
        :param sender: msg sender address
        :param score_address: SCORE address
        :param ratio: sharing ratio in percent (0-100)
        """

        deploy_info: 'IconScoreDeployInfo' = \
            self._deploy_storage.get_deploy_info(context, score_address)

        if deploy_info is None:
            raise InvalidRequestException('Invalid SCORE')

        if deploy_info.owner != sender:
            raise InvalidRequestException('Invalid SCORE owner')

        if not (0 <= ratio <= 100):
            raise InvalidRequestException('Invalid ratio')

        # TODO set information to storage
        # self._icx_storage.

    def get_score_fee_info(self,
                           context: 'IconScoreContext',
                           score_address: 'Address') -> ScoreFeeInfo:
        """
        Gets SCORE information

        :param context: IconScoreContext
        :param score_address: SCORE address
        :return: score information in dict
                - SCORE Address
                - Amount of issued total virtual step
                - Amount of Used total virtual step
                - contracts in list
        """

        return ScoreFeeInfo(score_address)

    # TODO : naming (term or period)
    def deposit_fee(self,
                    context: 'IconScoreContext',
                    tx_hash: bytes,
                    sender: 'Address',
                    score_address: 'Address',
                    amount: int,
                    block_number: int,
                    period: int) -> None:
        """
        Deposits ICXs for the SCORE.
        It may be issued the virtual STEPs for the SCORE to be able to pay share fees.

        :param context: IconScoreContext
        :param tx_hash: tx hash of the deposit transaction
        :param sender: ICX sender
        :param score_address: SCORE
        :param amount: amount of ICXs in loop
        :param block_number: current block height
        :param period: deposit period in blocks
        """
        # [Sub Task]
        # - Deposits ICX
        # - Calculates Virtual Step
        # - Updates Deposit Data
        pass

    def withdraw_fee(self,
                     context: 'IconScoreContext',
                     sender: 'Address',
                     deposit_id: bytes,
                     block_number: int) -> None:
        """
        Withdraws deposited ICXs from given id.
        It may be paid the penalty if the expiry has not been met.

        :param context: IconScoreContext
        :param sender: msg sender address
        :param deposit_id: deposit id, should be tx hash of deposit transaction
        :param block_number: current block height
        """
        # [Sub Task]
        # - Checks if the contract period is finished
        # - if the period is not finished, calculates and apply a penalty
        # - Update ICX
        pass

    def get_deposit_info_by_id(self,
                               context: 'IconScoreContext',
                               deposit_id: bytes) -> Optional[Deposit]:
        """
        Gets the deposit information. Returns None if the deposit from the given id does not exist.

        :param context: IconScoreContext
        :param deposit_id: deposit id, should be tx hash of deposit transaction
        :return: deposit information
        """

        return None

    # TODO : get_score_info_by_EOA

    def get_available_step(self,
                           context: 'IconScoreContext',
                           sender: 'Address',
                           to: 'Address',
                           sender_step_limit: int) -> Dict['Address', int]:
        """
        Gets the usable STEPs for the given step_limit from the sender.
        The return value is a dict of the sender's one and receiver's one.

        :param context: IconScoreContext
        :param sender: msg sender
        :param to: msg receiver
        :param sender_step_limit: step_limit from sender
        :return: Address-available_step dict
        """

        # Get the SCORE's ratio
        # Calculate ratio * SCORE and (1-ratio) * msg sender
        # Checks msg sender account
        # Checks SCORE owner account
        return {}

    def charge_transaction_fee(self,
                               context: 'IconScoreContext',
                               sender: 'Address',
                               to: 'Address',
                               step_price: int,
                               used_step: int) -> Dict['Address', int]:
        """
        Charges fees for the used STEPs.
        It can pay by shared if the msg receiver set to share fees.

        :param context: IconScoreContext
        :param sender: msg sender
        :param to: msg receiver
        :param step_price: current STEP price
        :param used_step: used STEPs
        :return Address-used_step dict
        """
        pass
