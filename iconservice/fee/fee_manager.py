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
from typing import List, Dict

from .deposit import Deposit
from ..base.exception import InvalidRequestException
from ..icx.icx_engine import IcxEngine

if typing.TYPE_CHECKING:
    from ..base.address import Address
    from ..deploy.icon_score_deploy_storage import IconScoreDeployInfo
    from ..deploy.icon_score_deploy_storage import IconScoreDeployStorage
    from ..iconscore.icon_score_context import IconScoreContext
    from ..icx.icx_storage import IcxStorage, Fee


class ScoreInfo:
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
        Sets the fee sharing ratio that SCORE pays.

        :param context: IconScoreContext
        :param sender: msg sender address
        :param score_address: SCORE address
        :param ratio: sharing ratio in percent (0-100)
        """

        self._check_score_ownership(context, sender, score_address)

        if not (0 <= ratio <= 100):
            raise InvalidRequestException('Invalid ratio')

        score_fee_info = self._icx_storage.get_score_fee(context, score_address)
        score_fee_info.ratio = ratio

        self._icx_storage.put_score_fee(context, score_address, score_fee_info)

    def get_fee_sharing_ratio(self,
                              context: 'IconScoreContext',
                              score_address: 'Address') -> int:
        """
        Gets the fee sharing ratio from score info

        :param context: IconScoreContext
        :param score_address: SCORE address
        :return: sharing ratio in percent (0-100)
        """

        self._check_score_valid(context, score_address)

        score_fee_info = self._icx_storage.get_score_fee(context, score_address)
        return score_fee_info.ratio

    def get_score_fee_info(self,
                           context: 'IconScoreContext',
                           score_address: 'Address') -> ScoreInfo:
        """
        Gets the SCORE information

        :param context: IconScoreContext
        :param score_address: SCORE address
        :return: score information in dict
                - SCORE Address
                - Amount of issued total virtual step
                - Amount of Used total virtual step
                - contracts in list
        """

        self._check_score_valid(context, score_address)

        score_fee_info_from_storage = self._icx_storage.get_score_fee(context, score_address)

        score_fee_info = ScoreInfo(score_address)
        score_fee_info.sharing_ratio = score_fee_info_from_storage.ratio
        deposit_id = score_fee_info_from_storage.head_id

        # Appends all deposits
        while deposit_id is not None:
            deposit = self._icx_storage.get_deposit(context, deposit_id)
            score_fee_info.deposits.append(deposit)
            deposit_id = deposit.next_id

        return score_fee_info

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

        self._check_score_ownership(context, sender, score_address)

        score_fee_info = self._icx_storage.get_score_fee(context, score_address)

        # Withdraws from sender's account
        sender_account = self._icx_storage.get_account(context, sender)
        sender_account.withdraw(amount)

        deposit = Deposit(tx_hash, score_address, sender)
        deposit.deposit_amount = amount
        deposit.created = block_number
        deposit.expires = block_number + period
        deposit.virtual_step_issued = \
            self._calculate_virtual_step_issuance(amount, deposit.created, deposit.expires)
        deposit.prev_id = score_fee_info.tail_id
        self._icx_storage.put_deposit(context, tx_hash, deposit)

        # Link to old last item
        prev_deposit = self._icx_storage.get_deposit(context, tx_hash)
        prev_deposit.next = tx_hash
        self._icx_storage.put_deposit(context, prev_deposit.id, prev_deposit)

        # Update last info
        if score_fee_info.head_id is None:
            score_fee_info.head_id = tx_hash

        if score_fee_info.available_head_id is None:
            score_fee_info.available_head_id = tx_hash

        score_fee_info.tail_id = tx_hash
        self._icx_storage.put_score_fee(context, score_address, score_fee_info)

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

        self._check_deposit_id(deposit_id)

    def get_deposit_info_by_id(self,
                               context: 'IconScoreContext',
                               deposit_id: bytes) -> Deposit:
        """
        Gets the deposit information. Returns None if the deposit from the given id does not exist.

        :param context: IconScoreContext
        :param deposit_id: deposit id, should be tx hash of deposit transaction
        :return: deposit information
        """
        self._check_deposit_id(deposit_id)

        deposit = self._icx_storage.get_deposit(context, deposit_id)

        if deposit is None:
            raise InvalidRequestException('Deposit info not found')

        return deposit

    # TODO : get_score_info_by_EOA

    def get_available_step(self,
                           context: 'IconScoreContext',
                           sender: 'Address',
                           to: 'Address',
                           sender_step_limit: int,
                           block_number: int) -> Dict['Address', int]:
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

        receiver_step = 0

        if to.is_contract:
            score_fee_info = self._icx_storage.get_score_fee(context, to)

            if score_fee_info is not None:
                total_step = sender_step_limit * 100 // (100 - score_fee_info.ratio)
                receiver_step = total_step - sender_step_limit

        return {sender: sender_step_limit, to: receiver_step}

    def can_charge_fee_from_score(self):
        pass

    def _can_charge_fee_from_score_by_virtual_step(self,
                                                   context: 'IconScoreContext',
                                                   score_fee_info: 'Fee',
                                                   step_required: int,
                                                   block_number: int):

        deposit_id = score_fee_info.available_head_id

        while deposit_id is not None:
            deposit = self._icx_storage.get_deposit(context, deposit_id)

            if block_number < deposit.expires:
                remains = deposit.virtual_step_issued - deposit.virtual_step_used
                step_required -= remains
                if step_required <= 0:
                    return True

        return False

    def _can_charge_fee_from_score_by_deposit(self,
                                              context: 'IconScoreContext',
                                              score_fee_info: 'Fee',
                                              step_required: int,
                                              block_number: int):

        deposit_id = score_fee_info.available_head_id

        while deposit_id is not None:
            deposit = self._icx_storage.get_deposit(context, deposit_id)

            if block_number < deposit.expires:
                remains = deposit.virtual_step_issued - deposit.virtual_step_used
                step_required -= remains
                if step_required <= 0:
                    return True

        return False

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

    def _get_score_deploy_info(self, context, score_address) -> 'IconScoreDeployInfo':
        deploy_info: 'IconScoreDeployInfo' = \
            self._deploy_storage.get_deploy_info(context, score_address)

        if deploy_info is None:
            raise InvalidRequestException('Invalid SCORE')

        return deploy_info

    def _check_score_valid(self, context, score_address):
        deploy_info = self._get_score_deploy_info(context, score_address)

        assert deploy_info is not None

    def _check_score_ownership(self, context, sender, score_address) -> None:
        deploy_info = self._get_score_deploy_info(context, score_address)

        if deploy_info.owner != sender:
            raise InvalidRequestException('Invalid SCORE owner')

    @staticmethod
    def _check_deposit_id(deposit_id):
        if deposit_id is None or not isinstance(deposit_id, bytes) or len(deposit_id) != 32:
            raise InvalidRequestException('Invalid deposit ID')

    @staticmethod
    def _calculate_virtual_step_issuance(deposit_amount: int,
                                         created_at: int,
                                         expires_in: int, ):
        # TODO implement functionality
        return 0

    @staticmethod
    def _calculate_penalty(deposit_amount: int,
                           created_at: int,
                           expires_in: int,
                           block_number: int):
        # TODO implement functionality
        return 0
