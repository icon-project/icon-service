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
from enum import IntEnum
from typing import List, Dict, Optional

from .deposit import Deposit
from .fee_storage import Fee, FeeStorage
from ..base.address import ZERO_SCORE_ADDRESS
from ..base.exception import InvalidRequestException, InvalidParamsException
from ..base.type_converter import TypeConverter
from ..base.type_converter_templates import ParamType
from ..iconscore.icon_score_event_log import EventLogEmitter
from ..icx.icx_engine import IcxEngine
from ..utils import to_camel_case

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
        # available virtual STEPs to use
        self.available_virtual_step: int = 0
        # available deposits to use
        self.available_deposit: int = 0

    def to_dict(self, casing: Optional = None) -> dict:
        """
        Returns properties as `dict`
        :return: a dict
        """
        new_dict = {}
        for key, value in self.__dict__.items():
            if value is None:
                # Excludes properties which have `None` value
                continue

            new_dict[casing(key) if casing else key] = value

        return new_dict


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

    # The minimum remaining amount of a single deposit
    _MIN_REMAINING_AMOUNT = 500 * 10 ** 18

    def __init__(self,
                 deploy_storage: 'IconScoreDeployStorage',
                 fee_storage: 'FeeStorage',
                 icx_storage: 'IcxStorage',
                 icx_engine: 'IcxEngine'):

        self._deploy_storage = deploy_storage
        self._fee_storage = fee_storage
        self._icx_storage = icx_storage
        self._icx_engine = icx_engine

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

        # Appends all deposits
        for deposit in self._deposit_generator(context, score_fee_info_from_storage.head_id):
            score_fee_info.deposits.append(deposit)

            # Retrieves available virtual STEPs and deposits
            if block_number < deposit.expires:
                score_fee_info.available_virtual_step += deposit.remaining_virtual_step
                score_fee_info.available_deposit += \
                    max(deposit.remaining_deposit - self._MIN_REMAINING_AMOUNT, 0)

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

    def _insert_deposit(self, context, deposit):
        """
        Inserts deposit information to storage
        """

        score_fee_info = self._get_or_create_score_fee(context, deposit.score_address)

        deposit.prev_id = score_fee_info.tail_id
        self._fee_storage.put_deposit(context, deposit.id, deposit)

        # Link to old last item
        if score_fee_info.tail_id is not None:
            prev_deposit = self._fee_storage.get_deposit(context, score_fee_info.tail_id)
            prev_deposit.next_id = deposit.id
            self._fee_storage.put_deposit(context, prev_deposit.id, prev_deposit)

        # Update head info
        if score_fee_info.head_id is None:
            score_fee_info.head_id = deposit.id

        if score_fee_info.available_head_id_of_virtual_step is None:
            score_fee_info.available_head_id_of_virtual_step = deposit.id

        if score_fee_info.available_head_id_of_deposit is None:
            score_fee_info.available_head_id_of_deposit = deposit.id

        if score_fee_info.expires_of_virtual_step < deposit.expires:
            score_fee_info.expires_of_virtual_step = deposit.expires

        if score_fee_info.expires_of_deposit < deposit.expires:
            score_fee_info.expires_of_deposit = deposit.expires

        score_fee_info.tail_id = deposit.id
        self._fee_storage.put_score_fee(context, deposit.score_address, score_fee_info)

    def withdraw_fee(self,
                     context: 'IconScoreContext',
                     sender: 'Address',
                     deposit_id: bytes,
                     block_number: int) -> ('Address', int, int):
        """
        Withdraws deposited ICXs from given id.
        It may be paid the penalty if the expiry has not been met.

        :param context: IconScoreContext
        :param sender: msg sender address
        :param deposit_id: deposit id, should be tx hash of deposit transaction
        :param block_number: current block height
        :return: score_address, returning amount of icx, penalty amount of icx
        """
        # [Sub Task]
        # - Checks if the contract period is finished
        # - If the period is not finished, it calculates and applies to a penalty
        # - Update ICX

        self._check_deposit_id(deposit_id)

        deposit = self._fee_storage.get_deposit(context, deposit_id)

        if deposit is None:
            raise InvalidRequestException('Deposit info not found')

        if deposit.sender != sender:
            raise InvalidRequestException('Invalid sender')

        self._delete_deposit(context, deposit, block_number)

        # Deposits to sender's account
        penalty = self._calculate_penalty(
            deposit.deposit_amount, deposit.created, deposit.expires, block_number)

        if penalty > 0:
            treasury_account = self._icx_engine.get_treasury_account(context)
            treasury_account.deposit(penalty)
            self._icx_storage.put_account(context, treasury_account.address, treasury_account)

        return_amount = deposit.deposit_amount - deposit.deposit_used - penalty
        if return_amount > 0:
            sender_account = self._icx_storage.get_account(context, sender)
            sender_account.deposit(return_amount)
            self._icx_storage.put_account(context, sender, sender_account)

        return deposit.score_address, return_amount, penalty

    def _delete_deposit(self, context: 'IconScoreContext', deposit: 'Deposit', block_number: int) -> None:
        """
        Deletes deposit information from storage
        """
        # Updates the previous link
        if deposit.prev_id is not None:
            prev_deposit = self._fee_storage.get_deposit(context, deposit.prev_id)
            prev_deposit.next_id = deposit.next_id
            self._fee_storage.put_deposit(context, prev_deposit.id, prev_deposit)

        # Updates the next link
        if deposit.next_id is not None:
            next_deposit = self._fee_storage.get_deposit(context, deposit.next_id)
            next_deposit.prev_id = deposit.prev_id
            self._fee_storage.put_deposit(context, next_deposit.id, next_deposit)

        # Update index info
        score_fee_info = self._fee_storage.get_score_fee(context, deposit.score_address)
        fee_info_changed = False

        if score_fee_info.head_id == deposit.id:
            score_fee_info.head_id = deposit.next_id
            fee_info_changed = True

        if score_fee_info.available_head_id_of_virtual_step == deposit.id:
            # Search for next deposit id which is available to use virtual step
            gen = self._deposit_generator(context, deposit.next_id)
            next_available_deposit = next(filter(lambda d: block_number < d.expires, gen), None)
            next_deposit_id = next_available_deposit.id if next_available_deposit is not None else None
            score_fee_info.available_head_id_of_virtual_step = next_deposit_id
            fee_info_changed = True

        if score_fee_info.available_head_id_of_deposit == deposit.id:
            # Search for next deposit id which is available to use the deposited ICX
            gen = self._deposit_generator(context, deposit.next_id)
            next_available_deposit = next(filter(lambda d: block_number < d.expires, gen), None)
            next_deposit_id = next_available_deposit.id if next_available_deposit is not None else None
            score_fee_info.available_head_id_of_deposit = next_deposit_id
            fee_info_changed = True

        if score_fee_info.expires_of_virtual_step == deposit.expires:
            gen = self._deposit_generator(context, score_fee_info.available_head_id_of_virtual_step)
            max_expires = max(map(lambda d: d.expires, gen), default=-1)
            score_fee_info.expires_of_virtual_step = max_expires if max_expires > block_number else -1
            fee_info_changed = True

        if score_fee_info.expires_of_deposit == deposit.expires:
            gen = self._deposit_generator(context, score_fee_info.available_head_id_of_deposit)
            max_expires = max(map(lambda d: d.expires, gen), default=-1)
            score_fee_info.expires_of_deposit = max_expires if max_expires > block_number else -1
            fee_info_changed = True

        if score_fee_info.tail_id == deposit.id:
            score_fee_info.available_head_id_of_deposit = deposit.prev_id
            fee_info_changed = True

        if fee_info_changed:
            # Updates if the information has been changed
            self._fee_storage.put_score_fee(context, deposit.score_address, score_fee_info)

        # Deletes deposit info
        self._fee_storage.delete_deposit(context, deposit.id)

    def get_deposit_info_by_id(self,
                               context: 'IconScoreContext',
                               deposit_id: bytes) -> Deposit:
        """
        Gets the deposit information.
        Raise an exception if the deposit from the given id does not exist.

        :param context: IconScoreContext
        :param deposit_id: deposit id, should be tx hash of deposit transaction
        :return: deposit information
        """

        self._check_deposit_id(deposit_id)

        deposit = self._fee_storage.get_deposit(context, deposit_id)

        if deposit is None:
            raise InvalidRequestException('Deposit info not found')

        return deposit

    def check_score_available(
            self, context: 'IconScoreContext', score_address: 'Address', block_number: int):
        """
        Check if the SCORE is available.
        If the SCORE is sharing fee, SCORE should be able to pay the fee,
        otherwise, the SCORE is not available.

        :param context: IconScoreContext
        :param score_address: SCORE address
        :param block_number: current block height
        """
        fee_info: 'Fee' = self._get_or_create_score_fee(context, score_address)

        if self._is_score_sharing_fee(fee_info):
            virtual_step_available = \
                block_number < fee_info.expires_of_virtual_step \
                and fee_info.available_head_id_of_virtual_step is not None

            deposit_available = \
                block_number < fee_info.expires_of_deposit \
                and fee_info.available_head_id_of_deposit is not None

            if not virtual_step_available and not deposit_available:
                raise InvalidRequestException('SCORE can not share fee')

    @staticmethod
    def _is_score_sharing_fee(score_fee_info: 'Fee') -> bool:
        return score_fee_info is not None and score_fee_info.head_id is not None

    def _get_fee_sharing_ratio(self, context: 'IconScoreContext', score_fee_info: 'Fee'):

        if not self._is_score_sharing_fee(score_fee_info):
            # If there are no deposits, ignores the fee sharing ratio that the SCORE set.
            return 0

        return context.fee_sharing_ratio

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

        detail_step_used = {}

        if sender_step > 0:
            detail_step_used[sender] = sender_step

        if receiver_step > 0:
            detail_step_used[to] = receiver_step

        return detail_step_used

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

        score_fee_info = self._fee_storage.get_score_fee(context, score_address)

        # Amount of STEPs that SCORE will pay
        receiver_step = used_step * self._get_fee_sharing_ratio(context, score_fee_info) // 100

        if receiver_step > 0:
            charged_step, virtual_step_indices_changed = self._charge_fee_by_virtual_step(
                context, score_fee_info, receiver_step, block_number)

            icx_required = (receiver_step - charged_step) * step_price
            charged_icx, deposit_indices_changed = self._charge_fee_by_deposit(
                context, score_fee_info, icx_required, block_number)

            if icx_required != charged_icx:
                raise InvalidParamsException('Out of deposit balance')

            if virtual_step_indices_changed or deposit_indices_changed:
                # Updates if the information has been changed
                self._fee_storage.put_score_fee(context, score_address, score_fee_info)

        return receiver_step

    def _charge_fee_by_virtual_step(self,
                                    context: 'IconScoreContext',
                                    score_fee_info: 'Fee',
                                    step_required: int,
                                    block_number: int) -> (int, bytes):
        """
        Charges fees by available virtual STEPs
        Returns total charged amount and whether the properties of 'score_fee_info' are changed
        """

        remaining_required_step = step_required
        should_update_expire = False
        last_paid_deposit = None

        gen = self._deposit_generator(context, score_fee_info.available_head_id_of_virtual_step)
        for deposit in filter(lambda d: block_number < d.expires, gen):
            available_virtual_step = deposit.remaining_virtual_step

            if remaining_required_step < available_virtual_step:
                charged_step = remaining_required_step
            else:
                charged_step = available_virtual_step

                # All virtual steps are consumed in this loop.
                # So if this `expires` is the `max expires`, should find the next `max expires`.
                if deposit.expires == score_fee_info.expires_of_virtual_step:
                    should_update_expire = True

            if charged_step > 0:
                deposit.virtual_step_used += charged_step
                self._fee_storage.put_deposit(context, deposit.id, deposit)
                last_paid_deposit = deposit

                remaining_required_step -= charged_step
                if remaining_required_step == 0:
                    break

        indices_changed = self._update_virtual_step_indices(
            context, score_fee_info, last_paid_deposit, should_update_expire, block_number)

        return step_required - remaining_required_step, indices_changed

    def _update_virtual_step_indices(self,
                                     context: 'IconScoreContext',
                                     score_fee_info: 'Fee',
                                     last_paid_deposit: Deposit,
                                     should_update_expire: bool,
                                     block_number: int) -> bool:
        """
        Updates indices of virtual steps to fee info and returns whether there exist changes.
        """

        next_available_deposit = last_paid_deposit

        if last_paid_deposit is not None and last_paid_deposit.remaining_virtual_step == 0:
            # All virtual steps have been consumed in the current deposit
            # so should find the next available virtual steps
            gen = self._deposit_generator(context, last_paid_deposit.next_id)
            next_available_deposit = next(filter(lambda d: block_number < d.expires, gen), None)

        next_available_deposit_id = next_available_deposit.id \
            if next_available_deposit is not None else None
        next_expires = score_fee_info.expires_of_virtual_step

        if next_available_deposit_id is None:
            # This means that there are no available virtual steps in all deposits.
            next_expires = -1
        elif should_update_expire:
            # Finds next max expires. Sets to -1 if not exist.
            gen = self._deposit_generator(context, next_available_deposit_id)
            next_expires = max(map(lambda d: d.expires, gen), default=-1)

        if score_fee_info.available_head_id_of_virtual_step != next_available_deposit_id \
                or score_fee_info.expires_of_virtual_step != next_expires:
            # Updates and return True if changes are exist
            score_fee_info.available_head_id_of_virtual_step = next_available_deposit_id
            score_fee_info.expires_of_virtual_step = next_expires
            return True

        return False

    def _charge_fee_by_deposit(self,
                               context: 'IconScoreContext',
                               score_fee_info: 'Fee',
                               icx_required: int,
                               block_number: int) -> (int, bytes):
        """
        Charges fees by available deposit ICXs
        Returns total charged amount and whether the properties of 'score_fee_info' are changed
        """

        remaining_required_icx = icx_required
        should_update_expire = False
        last_paid_deposit = None

        # Search for next available deposit id
        gen = self._deposit_generator(context, score_fee_info.available_head_id_of_deposit)
        for deposit in filter(lambda d: block_number < d.expires, gen):
            available_deposit = deposit.remaining_deposit - self._MIN_REMAINING_AMOUNT

            if remaining_required_icx < available_deposit:
                charged_icx = remaining_required_icx
            else:
                charged_icx = available_deposit

                # All available deposits are consumed in this loop.
                # So if this `expires` is the `max expires`, should find the next `max expires`.
                if deposit.expires == score_fee_info.expires_of_deposit:
                    should_update_expire = True

            deposit.deposit_used += charged_icx
            self._fee_storage.put_deposit(context, deposit.id, deposit)
            last_paid_deposit = deposit

            remaining_required_icx -= charged_icx
            if remaining_required_icx == 0:
                break

        if remaining_required_icx > 0 and last_paid_deposit is not None:
            # This is the last chargeable deposit
            # so, charges all remaining fee regardless minimum remaining amount.
            available_deposit = last_paid_deposit.deposit_amount - last_paid_deposit.deposit_used
            charged_icx = min(available_deposit, remaining_required_icx)
            last_paid_deposit.deposit_used += charged_icx
            self._fee_storage.put_deposit(context, last_paid_deposit.id, last_paid_deposit)
            remaining_required_icx -= charged_icx

        indices_changed = self._update_deposit_indices(
            context, score_fee_info, last_paid_deposit, should_update_expire, block_number)

        return icx_required - remaining_required_icx, indices_changed

    def _update_deposit_indices(self,
                                context: 'IconScoreContext',
                                score_fee_info: 'Fee',
                                last_paid_deposit: Deposit,
                                should_update_expire: bool,
                                block_number: int) -> bool:
        """
        Updates indices of deposit to fee info and returns whether there exist changes.
        """

        next_available_deposit = last_paid_deposit

        if last_paid_deposit.remaining_deposit <= self._MIN_REMAINING_AMOUNT:
            # All available deposits have been consumed in the current deposit
            # so should find the next available deposits
            gen = self._deposit_generator(context, last_paid_deposit.next_id)
            next_available_deposit = next(filter(lambda d: block_number < d.expires, gen), None)

        next_available_deposit_id = next_available_deposit.id if next_available_deposit else None
        next_expires = score_fee_info.expires_of_deposit

        if next_available_deposit_id is None:
            # This means that there are no available deposits.
            next_expires = -1
        elif should_update_expire:
            # Finds next max expires. Sets to -1 if not exist.
            gen = self._deposit_generator(context, next_available_deposit_id)
            next_expires = max(map(lambda d: d.expires, gen), default=-1)

        if score_fee_info.available_head_id_of_deposit != next_available_deposit_id \
                or score_fee_info.expires_of_deposit != next_expires:
            # Updates and return True if changes are exist
            score_fee_info.available_head_id_of_deposit = next_available_deposit_id
            score_fee_info.expires_of_deposit = next_expires
            return True

        return False

    def _deposit_generator(self, context: 'IconScoreContext', start_id: Optional[bytes]):
        next_id = start_id
        while next_id is not None:
            deposit = self._fee_storage.get_deposit(context, next_id)
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
        score_fee_info = self._fee_storage.get_score_fee(context, score_address)
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


class FeeHandler:
    """
    Fee Handler
    """

    # For eventlog emitting
    class EventType(IntEnum):
        DEPOSIT = 0
        WITHDRAW = 1

    SIGNATURE_AND_INDEX = [
        ('DepositCreated(bytes,Address,Address,int,int)', 3),
        ('DepositDestroyed(bytes,Address,Address,int,int)', 3)
    ]

    @staticmethod
    def get_signature_and_index_count(event_type: EventType):
        return FeeHandler.SIGNATURE_AND_INDEX[event_type]

    def __init__(self, fee_engine: 'FeeEngine'):
        self.fee_engine = fee_engine

        self.fee_handler = {
            'createDeposit': self._deposit_fee,
            'destroyDeposit': self._withdraw_fee,
            'getDeposit': self._get_deposit_info_by_id,
            'getScoreInfo': self._get_score_fee_info
        }

    def handle_fee_request(self, context: 'IconScoreContext', data: dict):
        """
        Handles fee request(querying or invoking)

        :param context: IconScoreContext
        :param data: data field
        :return:
        """
        converted_data = TypeConverter.convert(data, ParamType.FEE2_PARAMS_DATA)
        method = converted_data['method']

        try:
            handler = self.fee_handler[method]
            params = converted_data.get('params', {})
            return handler(context, **params)
        except KeyError:
            # Case of invoking handler functions with unknown method name
            raise InvalidRequestException(f"Invalid method: {method}")
        except TypeError:
            # Case of invoking handler functions with invalid parameter
            # e.g. 'missing required params' or 'unknown params'
            raise InvalidRequestException(f"Invalid request: parameter error")

    def _deposit_fee(
            self, context: 'IconScoreContext', _score: 'Address', _amount: int, _period: int):

        self.fee_engine.deposit_fee(context, context.tx.hash, context.msg.sender, _score,
                                    _amount, context.block.height, _period)

        event_log_args = [context.tx.hash, _score, context.msg.sender, _amount, _period]
        self._emit_event(context, FeeHandler.EventType.DEPOSIT, event_log_args)

    def _withdraw_fee(self, context: 'IconScoreContext', _id: bytes):
        # return deposit_id, (score_address), context.msg.sender, (return_icx, penalty)
        score_address, return_icx, penalty = self.fee_engine.withdraw_fee(
            context, context.msg.sender, _id, context.block.height)

        event_log_args = [_id, score_address, context.msg.sender, return_icx, penalty]
        self._emit_event(context, FeeHandler.EventType.WITHDRAW, event_log_args)

    def _get_deposit_info_by_id(self, context: 'IconScoreContext', _id: bytes):
        deposit = self.fee_engine.get_deposit_info_by_id(context, _id)
        return deposit.to_dict(to_camel_case)

    def _get_score_fee_info(self, context: 'IconScoreContext', _score: 'Address'):
        score_info = self.fee_engine.get_score_fee_info(context, _score, context.block.height)
        return score_info.to_dict(to_camel_case)

    @staticmethod
    def _emit_event(
            context: 'IconScoreContext', event_type: 'FeeHandler.EventType', event_log_args: list):

        signature, index_count = FeeHandler.get_signature_and_index_count(event_type)

        EventLogEmitter.emit_event_log(
            context, ZERO_SCORE_ADDRESS, signature, event_log_args, index_count)
