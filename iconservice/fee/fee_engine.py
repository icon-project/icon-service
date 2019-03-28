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
from ..base.exception import InvalidRequestException, InvalidParamsException
from ..icx.icx_engine import IcxEngine
from ..icx.icx_storage import Fee

if typing.TYPE_CHECKING:
    from ..base.address import Address
    from ..deploy.icon_score_deploy_storage import IconScoreDeployInfo
    from ..deploy.icon_score_deploy_storage import IconScoreDeployStorage
    from ..iconscore.icon_score_context import IconScoreContext
    from ..icx.icx_storage import IcxStorage


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
        self.available_virtual_step: int = 0
        # available deposits to use
        self.available_deposit: int = 0


class FeeEngine:
    """
    Presenter of the fee operation.

    [Role]
    - State DB CRUD
    - Business logic (inc. Calculation)
    """

    _MAX_DEPOSIT_AMOUNT = 100_000 * 10 ** 18

    _MIN_DEPOSIT_AMOUNT = 5_000 * 10 ** 18

    _MAX_DEPOSIT_PERIOD = 31_104_000

    _MIN_DEPOSIT_PERIOD = 1_296_000

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

        score_fee_info = self._get_or_create_score_fee(context, score_address)
        score_fee_info.ratio = ratio

        self._icx_storage.put_score_fee(context, score_address, score_fee_info)

        # return ratio

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
        return score_fee_info.ratio if score_fee_info is not None else 0

    def get_score_fee_info(self,
                           context: 'IconScoreContext',
                           score_address: 'Address',
                           block_number: int) -> ScoreFeeInfo:
        """
        Gets the SCORE information

        :param context: IconScoreContext
        :param score_address: SCORE address
        :param block_number: current block number
        :return: score information in dict
                - SCORE Address
                - Amount of issued total virtual step
                - Amount of Used total virtual step
                - contracts in list
        """

        self._check_score_valid(context, score_address)

        score_fee_info_from_storage = self._get_or_create_score_fee(context, score_address)

        score_fee_info = ScoreFeeInfo(score_address)
        score_fee_info.sharing_ratio = score_fee_info_from_storage.ratio

        # Appends all deposits
        for deposit in self._deposit_generator(context, score_fee_info_from_storage.head_id):
            score_fee_info.deposits.append(deposit)

            # Retrieves available virtual STEPs and deposits
            if block_number < deposit.expires:
                score_fee_info.available_virtual_step += deposit.available_virtual_step
                score_fee_info.available_deposit += deposit.available_deposit

        return score_fee_info

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

        if not (self._MIN_DEPOSIT_AMOUNT <= amount <= self._MAX_DEPOSIT_AMOUNT):
            raise InvalidRequestException('Invalid deposit amount')

        if not (self._MIN_DEPOSIT_PERIOD <= period <= self._MAX_DEPOSIT_PERIOD):
            raise InvalidRequestException('Invalid deposit period')

        self._check_score_ownership(context, sender, score_address)

        score_fee_info = self._get_or_create_score_fee(context, score_address)

        # Withdraws from sender's account
        sender_account = self._icx_storage.get_account(context, sender)
        sender_account.withdraw(amount)
        self._icx_storage.put_account(context, sender, sender_account)

        deposit = Deposit(tx_hash, score_address, sender, amount)
        deposit.created = block_number
        deposit.expires = block_number + period
        deposit.virtual_step_issued = \
            self._calculate_virtual_step_issuance(amount, deposit.created, deposit.expires)
        deposit.prev_id = score_fee_info.tail_id

        self._insert_deposit(context, deposit)

        # return (id, SCORE address, sender, amount, period)

    def _insert_deposit(self, context, deposit):
        """
        Inserts deposit information to storage
        """

        score_fee_info = self._get_or_create_score_fee(context, deposit.score_address)

        deposit.prev_id = score_fee_info.tail_id
        self._icx_storage.put_deposit(context, deposit.id, deposit)

        # Link to old last item
        if score_fee_info.tail_id is not None:
            prev_deposit = self._icx_storage.get_deposit(context, score_fee_info.tail_id)
            prev_deposit.next_id = deposit.id
            self._icx_storage.put_deposit(context, prev_deposit.id, prev_deposit)

        # Update head info
        if score_fee_info.head_id is None:
            score_fee_info.head_id = deposit.id

        if score_fee_info.available_head_id_of_virtual_step is None:
            score_fee_info.available_head_id_of_virtual_step = deposit.id

        if score_fee_info.available_head_id_of_deposit is None:
            score_fee_info.available_head_id_of_deposit = deposit.id

        score_fee_info.tail_id = deposit.id
        self._icx_storage.put_score_fee(context, deposit.score_address, score_fee_info)

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

        deposit = self._icx_storage.get_deposit(context, deposit_id)

        if deposit is None:
            raise InvalidRequestException('Deposit info not found')

        if deposit.sender != sender:
            raise InvalidRequestException('Invalid sender')

        self._delete_deposit(context, deposit)

        # Deposits to sender's account
        penalty = self._calculate_penalty(
            deposit.deposit_amount, deposit.created, deposit.expires, block_number)

        return_amount = deposit.deposit_amount - deposit.deposit_used - penalty
        if return_amount > 0:
            sender_account = self._icx_storage.get_account(context, sender)
            sender_account.deposit(return_amount)
            self._icx_storage.put_account(context, sender, sender_account)

        # return (deposit.score_address, sender, return_amount, penalty)

    def _delete_deposit(self, context: 'IconScoreContext', deposit: 'Deposit'):
        """
        Deletes deposit information from storage
        """

        # Updates the previous link
        if deposit.prev_id is not None:
            prev_deposit = self._icx_storage.get_deposit(context, deposit.prev_id)
            prev_deposit.next_id = deposit.next_id
            self._icx_storage.put_deposit(context, prev_deposit.id, prev_deposit)

        # Updates the next link
        if deposit.next_id is not None:
            next_deposit = self._icx_storage.get_deposit(context, deposit.next_id)
            next_deposit.prev_id = deposit.prev_id
            self._icx_storage.put_deposit(context, next_deposit.id, next_deposit)

        # Update index info
        score_fee_info = self._icx_storage.get_score_fee(context, deposit.score_address)
        fee_info_changed = False

        if score_fee_info.head_id == deposit.id:
            score_fee_info.head_id = deposit.next_id
            fee_info_changed = True

        if score_fee_info.available_head_id_of_virtual_step == deposit.id:
            score_fee_info.available_head_id_of_virtual_step = deposit.next_id
            fee_info_changed = True

        if score_fee_info.available_head_id_of_deposit == deposit.id:
            score_fee_info.available_head_id_of_deposit = deposit.next_id
            fee_info_changed = True

        if score_fee_info.tail_id == deposit.id:
            score_fee_info.available_head_id_of_deposit = deposit.prev_id
            fee_info_changed = True

        if fee_info_changed:
            # Updates if the information has been changed
            self._icx_storage.put_score_fee(context, deposit.score_address, score_fee_info)

        # Deletes deposit info
        self._icx_storage.delete_deposit(context, deposit.id)

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

    def get_total_available_step(self,
                                 context: 'IconScoreContext',
                                 sender: 'Address',
                                 to: 'Address',
                                 sender_step_limit: int,
                                 step_price: int,
                                 block_number: int,
                                 max_step_limit: int) -> Dict['Address', int]:
        """
        Gets the usable STEPs for the given step_limit from the sender.
        The return value is a dict of the sender's one and receiver's one.

        :param context: IconScoreContext
        :param sender: msg sender
        :param to: msg receiver
        :param sender_step_limit: step_limit from sender
        :param step_price: current step price
        :param block_number: current block height
        :param max_step_limit: Maximum step limit per one transaction. (system(governance) defined)
        :return: Address-available_step dict
        """

        receiver_step = 0

        if to.is_contract:
            score_fee_info = self._icx_storage.get_score_fee(context, to)

            if score_fee_info is not None and score_fee_info.ratio > 0:
                if score_fee_info.ratio == 100:
                    # Retrieves how much STEPs SCORE can pay

                    gen = self._deposit_generator(context, score_fee_info.head_id)
                    for deposit in filter(lambda d: block_number < d.expires, gen):
                        receiver_step += deposit.available_virtual_step
                        receiver_step += deposit.available_deposit // step_price

                        if receiver_step >= max_step_limit:
                            receiver_step = max_step_limit
                            break
                else:
                    total_step = sender_step_limit * 100 // (100 - score_fee_info.ratio)
                    receiver_step = total_step - sender_step_limit

        return {sender: sender_step_limit, to: receiver_step}

    # TODO
    # def can_charge_fee(self,
    #                    context: 'IconScoreContext',
    #                    sender: 'Address',
    #                    to: 'Address',
    #                    step_limit: int,
    #                    step_price: int,
    #                    block_number: int):
    #
    #     if to.is_contract:

    def can_charge_fee_from_score(self,
                                  context: 'IconScoreContext',
                                  score_address: 'Address',
                                  step_required: int,
                                  step_price: int,
                                  block_number: int) -> bool:
        """
        Returns whether the SCORE can pay fees.

        :param context: IconScoreContext
        :param score_address: SCORE address
        :param step_required: Amount of STEPs that SCORE will pay
        :param step_price: current step price
        :param block_number: current block height
        :return: True if the SCORE can pay fees otherwise False
        """

        score_fee_info = self._icx_storage.get_score_fee(context, score_address)

        if score_fee_info is None:
            return False

        chargeable_virtual_step = self._get_chargeable_virtual_step_for_fee(
            context, score_fee_info, step_required, block_number)

        icx_required = (step_required - chargeable_virtual_step) * step_price

        chargeable_deposit = self._get_chargeable_deposit_for_fee(
            context, score_fee_info, icx_required, block_number)

        return icx_required == chargeable_deposit

    def _get_chargeable_virtual_step_for_fee(self,
                                             context: 'IconScoreContext',
                                             score_fee_info: 'Fee',
                                             step_required: int,
                                             block_number: int) -> int:
        """
        Calculates the amount of virtual STEPs that SCORE can pay for the required STEPs
        """

        total_chargeable_virtual_step = 0

        gen = self._deposit_generator(context, score_fee_info.available_head_id_of_virtual_step)
        for deposit in filter(lambda d: block_number < d.expires, gen):
            # The virtual STEPs are not available when expired
            total_chargeable_virtual_step += deposit.available_virtual_step

            if total_chargeable_virtual_step >= step_required:
                total_chargeable_virtual_step = step_required
                break

        return total_chargeable_virtual_step

    def _get_chargeable_deposit_for_fee(self,
                                        context: 'IconScoreContext',
                                        score_fee_info: 'Fee',
                                        icx_required: int,
                                        block_number: int) -> int:
        """
        Calculates the amount of ICXs that SCORE can pay for the required fees
        """

        total_chargeable_deposit = 0

        gen = self._deposit_generator(context, score_fee_info.available_head_id_of_deposit)
        for deposit in filter(lambda d: block_number < d.expires, gen):
            total_chargeable_deposit += deposit.available_deposit

            if total_chargeable_deposit >= icx_required:
                total_chargeable_deposit = icx_required
                break

        return total_chargeable_deposit

    def charge_transaction_fee(self,
                               context: 'IconScoreContext',
                               sender: 'Address',
                               to: 'Address',
                               step_price: int,
                               used_step: int,
                               block_number: int) -> Dict['Address', int]:
        """
        Charges fees for the used STEPs.
        It can pay by shared if the msg receiver set to share fees.

        :param context: IconScoreContext
        :param sender: msg sender
        :param to: msg receiver
        :param step_price: current STEP price
        :param used_step: used STEPs
        :param block_number: current block height
        :return Address-used_step dict
        """

        receiver_step = 0

        if to.is_contract:
            receiver_step = self._charge_fee_from_score(
                context, to, step_price, used_step, block_number)

        sender_step = used_step - receiver_step
        self._icx_engine.charge_fee(context, sender, sender_step * step_price)

        return {sender: sender_step, to: receiver_step}

    def _charge_fee_from_score(self,
                               context: 'IconScoreContext',
                               score_address: 'Address',
                               step_price: int,
                               used_step: int,
                               block_number: int) -> int:
        """
        Charges fees from SCORE
        Returns total STEPs SCORE paid
        """

        score_fee_info = self._icx_storage.get_score_fee(context, score_address)
        fee_ratio = score_fee_info.ratio if score_fee_info is not None else 0

        # Amount of STEPs that SCORE will pay
        receiver_step = used_step * fee_ratio // 100

        if receiver_step > 0:
            charged_step, next_head_id_for_virtual_step = self._charge_fee_by_virtual_step(
                context, score_fee_info, receiver_step, block_number)

            icx_required = (receiver_step - charged_step) * step_price
            charged_icx, next_head_id_for_deposit = self._charge_fee_by_deposit(
                context, score_fee_info, icx_required, block_number)

            if icx_required != charged_icx:
                raise InvalidParamsException('Out of deposit balance')

            if score_fee_info.available_head_id_of_virtual_step != next_head_id_for_virtual_step \
                    or score_fee_info.available_head_id_of_deposit != next_head_id_for_deposit:
                # Updates if the information has been changed
                self._icx_storage.put_score_fee(context, score_address, score_fee_info)

        return receiver_step

    def _charge_fee_by_virtual_step(self,
                                    context: 'IconScoreContext',
                                    score_fee_info: 'Fee',
                                    step_required: int,
                                    block_number: int) -> (int, int):
        """
        Charges fees by available virtual STEPs
        Returns total charged amount and next available deposit id
        """

        remaining_required_step = step_required
        last_deposit_id = None

        gen = self._deposit_generator(context, score_fee_info.available_head_id_of_virtual_step)
        for deposit in filter(lambda d: block_number < d.expires, gen):
            available_virtual_step = deposit.available_virtual_step

            if available_virtual_step > 0:
                if remaining_required_step < available_virtual_step:
                    charged_step = remaining_required_step
                else:
                    charged_step = available_virtual_step
                    last_deposit_id = deposit.next_id

                deposit.virtual_step_used += charged_step
                self._icx_storage.put_deposit(context, deposit.id, deposit)

                remaining_required_step -= charged_step

                if remaining_required_step == 0:
                    break

        return step_required - remaining_required_step, last_deposit_id

    def _charge_fee_by_deposit(self,
                               context: 'IconScoreContext',
                               score_fee_info: 'Fee',
                               icx_required: int,
                               block_number: int) -> (int, int):
        """
        Charges fees by available deposit ICXs
        Returns total charged amount and next available deposit id
        """

        remaining_required_icx = icx_required
        last_deposit_id = None

        gen = self._deposit_generator(context, score_fee_info.available_head_id_of_deposit)
        for deposit in filter(lambda d: block_number < d.expires, gen):
            available_deposit = deposit.available_deposit

            if available_deposit > 0:
                if remaining_required_icx < available_deposit:
                    charged_icx = remaining_required_icx
                else:
                    charged_icx = available_deposit
                    last_deposit_id = deposit.next_id

                deposit.deposit_used += charged_icx
                self._icx_storage.put_deposit(context, deposit.id, deposit)

                remaining_required_icx -= charged_icx

                if remaining_required_icx == 0:
                    break

        return icx_required - remaining_required_icx, last_deposit_id

    def _deposit_generator(self, context: 'IconScoreContext', start_id: bytes):
        next_id = start_id
        while next_id is not None:
            deposit = self._icx_storage.get_deposit(context, next_id)
            if deposit is not None:
                next_id = deposit.next_id

                yield deposit
            else:
                break

    def _get_score_deploy_info(self, context, score_address) -> 'IconScoreDeployInfo':
        deploy_info: 'IconScoreDeployInfo' = \
            self._deploy_storage.get_deploy_info(context, score_address)

        if deploy_info is None:
            raise InvalidRequestException('Invalid SCORE')

        return deploy_info

    def _check_score_valid(self, context, score_address) -> None:
        deploy_info = self._get_score_deploy_info(context, score_address)

        assert deploy_info is not None

    def _check_score_ownership(self, context, sender, score_address) -> None:
        deploy_info = self._get_score_deploy_info(context, score_address)

        if deploy_info.owner != sender:
            raise InvalidRequestException('Invalid SCORE owner')

    @staticmethod
    def _check_deposit_id(deposit_id) -> None:
        if deposit_id is None or not isinstance(deposit_id, bytes) or len(deposit_id) != 32:
            raise InvalidRequestException('Invalid deposit ID')

    def _get_or_create_score_fee(
            self, context: 'IconScoreContext', score_address: 'Address') -> 'Fee':
        score_fee_info = self._icx_storage.get_score_fee(context, score_address)
        if score_fee_info is None:
            score_fee_info = Fee()
        return score_fee_info

    @staticmethod
    def _calculate_virtual_step_issuance(deposit_amount: int,
                                         created_at: int,
                                         expires_in: int) -> int:
        assert deposit_amount is not None
        assert created_at is not None
        assert expires_in is not None

        # TODO implement functionality
        return 0

    @staticmethod
    def _calculate_penalty(deposit_amount: int,
                           created_at: int,
                           expires_in: int,
                           block_number: int) -> int:
        assert deposit_amount is not None
        assert created_at is not None
        assert expires_in is not None
        assert block_number is not None

        # TODO implement functionality
        return 0
