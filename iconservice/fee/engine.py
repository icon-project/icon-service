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
from decimal import Decimal
from enum import IntEnum
from typing import List, Dict, Optional

from .deposit import Deposit
from .deposit_meta import DepositMeta
from ..base.ComponentBase import EngineBase
from ..base.exception import InvalidRequestException, InvalidParamsException
from ..base.type_converter import TypeConverter
from ..base.type_converter_templates import ParamType
from ..icon_constant import ICX_IN_LOOP, Revision
from ..iconscore.icon_score_event_log import EventLogEmitter

if typing.TYPE_CHECKING:
    from ..base.address import Address
    from ..deploy.storage import IconScoreDeployInfo
    from ..iconscore.icon_score_context import IconScoreContext

FIXED_TERM = True
FIXED_RATIO_PER_MONTH = '0.08'
BLOCKS_IN_ONE_MONTH = 1_296_000


class DepositInfo:
    """
    Deposit information of a SCORE
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

            new_key = casing(key) if casing else key
            if isinstance(value, list):
                new_dict[new_key] = [v.to_dict(casing) for v in value if isinstance(v, Deposit)]
            else:
                new_dict[new_key] = value

        return new_dict


class Engine(EngineBase):
    """
    Presenter of the fee operation.

    [Role]
    - State DB CRUD
    - Business logic (inc. Calculation)
    """

    _MIN_DEPOSIT_AMOUNT = 5_000 * ICX_IN_LOOP
    _MAX_DEPOSIT_AMOUNT = 100_000 * ICX_IN_LOOP
    _MIN_DEPOSIT_TERM = BLOCKS_IN_ONE_MONTH
    _MAX_DEPOSIT_TERM = _MIN_DEPOSIT_TERM if FIXED_TERM else BLOCKS_IN_ONE_MONTH * 24

    def get_deposit_info(self,
                         context: 'IconScoreContext',
                         score_address: 'Address',
                         block_height: int) -> 'DepositInfo':
        """
        Gets the SCORE deposit information

        :param context: IconScoreContext
        :param score_address: SCORE address
        :param block_height: current block height
        :return: score deposit information in dict
                - SCORE Address
                - Amount of issued total virtual step
                - Amount of Used total virtual step
                - deposits in list
        """

        self._check_score_valid(context, score_address)

        deposit_meta = self._get_or_create_deposit_meta(context, score_address)

        deposit_info = DepositInfo(score_address)

        # Appends all deposits
        for deposit in self._deposit_generator(context, deposit_meta.head_id):
            deposit_info.deposits.append(deposit)

            # Retrieves available virtual STEPs and deposits
            if block_height < deposit.expires:
                deposit_info.available_virtual_step += deposit.remaining_virtual_step
                deposit_info.available_deposit += \
                    max(deposit.remaining_deposit - deposit.min_remaining_deposit, 0)

        return deposit_info if len(deposit_info.deposits) > 0 else None

    def add_deposit(self,
                    context: 'IconScoreContext',
                    tx_hash: bytes,
                    sender: 'Address',
                    score_address: 'Address',
                    amount: int,
                    block_height: int,
                    term: int):
        """
        Deposits ICXs for the SCORE.
        It may be issued the virtual STEPs for the SCORE to be able to pay share fees.

        :param context: IconScoreContext
        :param tx_hash: tx hash of the deposit transaction
        :param sender: ICX sender
        :param score_address: SCORE
        :param amount: amount of ICXs in loop
        :param block_height: current block height
        :param term: deposit term in blocks
        """
        # [Sub Task]
        # - Deposits ICX
        # - Calculates Virtual Step
        # - Updates Deposit Data

        if (FIXED_TERM and amount < self._MIN_DEPOSIT_AMOUNT) \
                or not (self._MIN_DEPOSIT_AMOUNT <= amount <= self._MAX_DEPOSIT_AMOUNT):
            raise InvalidRequestException('Invalid deposit amount')

        if not (self._MIN_DEPOSIT_TERM <= term <= self._MAX_DEPOSIT_TERM):
            raise InvalidRequestException('Invalid deposit term')

        self._check_score_ownership(context, sender, score_address)

        # Withdraws from sender's account
        sender_account = context.storage.icx.get_account(context, sender)
        sender_account.withdraw(amount)
        context.storage.icx.put_account(context, sender_account)

        deposit = Deposit(tx_hash, score_address, sender, amount)
        deposit.created = block_height
        deposit.expires = block_height + term

        step_price = context.step_counter.step_price
        deposit.virtual_step_issued = \
            VirtualStepCalculator.calculate_virtual_step(amount, term, step_price)

        self._append_deposit(context, deposit)

    def _append_deposit(self, context: 'IconScoreContext', deposit: 'Deposit'):
        """
        Append deposit data to storage
        """

        deposit_meta = self._get_or_create_deposit_meta(context, deposit.score_address)

        deposit.prev_id = deposit_meta.tail_id
        context.storage.fee.put_deposit(context, deposit)

        # Link to previous item
        if deposit.prev_id is not None:
            prev_deposit = context.storage.fee.get_deposit(context, deposit.prev_id)
            prev_deposit.next_id = deposit.id
            context.storage.fee.put_deposit(context, prev_deposit)

        # Update head info
        if deposit_meta.head_id is None:
            deposit_meta.head_id = deposit.id

        if deposit_meta.available_head_id_of_virtual_step is None:
            deposit_meta.available_head_id_of_virtual_step = deposit.id

        if deposit_meta.available_head_id_of_deposit is None:
            deposit_meta.available_head_id_of_deposit = deposit.id

        if deposit_meta.expires_of_virtual_step < deposit.expires:
            deposit_meta.expires_of_virtual_step = deposit.expires

        if deposit_meta.expires_of_deposit < deposit.expires:
            deposit_meta.expires_of_deposit = deposit.expires

        deposit_meta.tail_id = deposit.id
        context.storage.fee.put_deposit_meta(context, deposit.score_address, deposit_meta)

    def withdraw_deposit(self,
                         context: 'IconScoreContext',
                         sender: 'Address',
                         deposit_id: bytes,
                         block_height: int) -> (int, int):
        """
        Withdraws deposited ICXs from given id.
        It may be paid the penalty if the expiry has not been met.

        :param context: IconScoreContext
        :param sender: msg sender address
        :param deposit_id: deposit id, should be tx hash of deposit transaction
        :param block_height: current block height
        :return: returning amount of icx, penalty amount of icx
        """
        # [Sub Task]
        # - Checks if the contract term has expired
        # - If the term has not finished, it calculates and applies to a penalty
        # - Update ICX

        deposit = self.get_deposit(context, deposit_id)

        if deposit.sender != sender:
            raise InvalidRequestException('Invalid sender')
        if deposit.score_address != context.tx.to:
            raise InvalidRequestException('Invalid SCORE address')

        step_price = context.step_counter.step_price
        penalty = self._calculate_penalty(deposit, block_height, step_price)

        withdrawal_amount = deposit.remaining_deposit - penalty

        if withdrawal_amount < 0:
            raise InvalidRequestException("Failed to withdraw deposit")

        if penalty > 0:
            # Move the penalty amount to the treasury account
            treasury_account = context.storage.icx.get_treasury_account(context)
            treasury_account.deposit(penalty)
            context.storage.icx.put_account(context, treasury_account)

        if withdrawal_amount > 0:
            # Send the withdrawal amount of ICX to sender account
            sender_account = context.storage.icx.get_account(context, sender)
            sender_account.deposit(withdrawal_amount)
            context.storage.icx.put_account(context, sender_account)

        self._delete_deposit(context, deposit, block_height)

        return withdrawal_amount, penalty

    def _delete_deposit(self, context: 'IconScoreContext', deposit: 'Deposit', block_height: int) -> None:
        """
        Deletes deposit information from storage
        """
        # Updates the previous link
        if deposit.prev_id is not None:
            prev_deposit = context.storage.fee.get_deposit(context, deposit.prev_id)
            prev_deposit.next_id = deposit.next_id
            context.storage.fee.put_deposit(context, prev_deposit)

        # Updates the next link
        if deposit.next_id is not None:
            next_deposit = context.storage.fee.get_deposit(context, deposit.next_id)
            next_deposit.prev_id = deposit.prev_id
            context.storage.fee.put_deposit(context, next_deposit)

        # Update index info
        deposit_meta = context.storage.fee.get_deposit_meta(context, deposit.score_address)
        deposit_meta_changed = False

        if deposit_meta.head_id == deposit.id:
            deposit_meta.head_id = deposit.next_id
            deposit_meta_changed = True

        if deposit.id in (deposit_meta.available_head_id_of_virtual_step, deposit_meta.available_head_id_of_deposit):
            gen = self._deposit_generator(context, deposit.next_id)
            next_available_deposit = \
                next(filter(lambda d: block_height < d.expires, gen), None)
            next_deposit_id = \
                next_available_deposit.id if next_available_deposit is not None else None

            if deposit_meta.available_head_id_of_virtual_step == deposit.id:
                # Search for next deposit id which is available to use virtual step
                deposit_meta.available_head_id_of_virtual_step = next_deposit_id

            if deposit_meta.available_head_id_of_deposit == deposit.id:
                # Search for next deposit id which is available to use the deposited ICX
                deposit_meta.available_head_id_of_deposit = next_deposit_id

            deposit_meta_changed = True

        if deposit_meta.expires_of_virtual_step == deposit.expires:
            gen = self._deposit_generator(context, deposit_meta.available_head_id_of_virtual_step)
            max_expires = max(map(lambda d: d.expires, gen), default=-1)
            deposit_meta.expires_of_virtual_step = max_expires if max_expires > block_height else -1
            deposit_meta_changed = True

        if deposit_meta.expires_of_deposit == deposit.expires:
            gen = self._deposit_generator(context, deposit_meta.available_head_id_of_deposit)
            max_expires = max(map(lambda d: d.expires, gen), default=-1)
            deposit_meta.expires_of_deposit = max_expires if max_expires > block_height else -1
            deposit_meta_changed = True

        if deposit_meta.tail_id == deposit.id:
            deposit_meta.tail_id = deposit.prev_id
            deposit_meta_changed = True

        if deposit_meta_changed:
            # Updates if the information has been changed
            context.storage.fee.put_deposit_meta(context, deposit.score_address, deposit_meta)

        # Deletes deposit info
        context.storage.fee.delete_deposit(context, deposit.id)

    def get_deposit(self, context: 'IconScoreContext', deposit_id: bytes) -> Deposit:
        """
        Gets the deposit data.
        Raise an exception if the deposit from the given id does not exist.

        :param context: IconScoreContext
        :param deposit_id: deposit id, should be tx hash of deposit transaction
        :return: deposit data
        """

        self._check_deposit_id(deposit_id)

        deposit = context.storage.fee.get_deposit(context, deposit_id)
        if deposit is None:
            raise InvalidRequestException('Deposit not found')

        return deposit

    def check_score_available(self, context: 'IconScoreContext', score_address: 'Address', block_height: int):
        """
        Check if the SCORE is available.
        If the SCORE is sharing fee, SCORE should be able to pay the fee,
        otherwise, the SCORE is not available.

        :param context: IconScoreContext
        :param score_address: SCORE address
        :param block_height: current block height
        """
        deposit_meta: 'DepositMeta' = self._get_or_create_deposit_meta(context, score_address)

        if self._is_score_sharing_fee(deposit_meta):
            virtual_step_available = \
                block_height < deposit_meta.expires_of_virtual_step \
                and deposit_meta.available_head_id_of_virtual_step is not None

            deposit_available = \
                block_height < deposit_meta.expires_of_deposit \
                and deposit_meta.available_head_id_of_deposit is not None

            if not virtual_step_available and not deposit_available:
                raise InvalidRequestException('Out of deposit balance')

    @staticmethod
    def _is_score_sharing_fee(deposit_meta: 'DepositMeta') -> bool:
        return deposit_meta is not None and deposit_meta.head_id is not None

    def _get_fee_sharing_proportion(self, context: 'IconScoreContext', deposit_meta: 'DepositMeta'):

        if not self._is_score_sharing_fee(deposit_meta):
            # If there are no deposits, ignores the fee sharing ratio that the SCORE set.
            return 0

        return context.fee_sharing_proportion

    def charge_transaction_fee(self,
                               context: 'IconScoreContext',
                               sender: 'Address',
                               to: 'Address',
                               step_price: int,
                               used_step: int,
                               block_height: int) -> Dict['Address', int]:
        """
        Charges fees for the used STEPs.
        It can pay by shared if the msg recipient set to share fees.

        :param context: IconScoreContext
        :param sender: msg sender
        :param to: msg recipient
        :param step_price: current STEP price
        :param used_step: used STEPs
        :param block_height: current block height
        :return Address-used_step dict
        """

        recipient_step = 0

        if to.is_contract:
            recipient_step = self._charge_fee_from_score(
                context, to, step_price, used_step, block_height)

        sender_step = used_step - recipient_step
        context.engine.icx.charge_fee(context, sender, sender_step * step_price)

        step_used_details = {}

        if sender_step > 0:
            step_used_details[sender] = sender_step

        if recipient_step > 0:
            step_used_details[to] = recipient_step

        return step_used_details

    def _charge_fee_from_score(self,
                               context: 'IconScoreContext',
                               score_address: 'Address',
                               step_price: int,
                               used_step: int,
                               block_height: int) -> int:
        """
        Charges fees from SCORE
        Returns total STEPs SCORE paid
        """

        deposit_meta = context.storage.fee.get_deposit_meta(context, score_address)

        # Amount of STEPs that SCORE will pay
        required_step = used_step * self._get_fee_sharing_proportion(context, deposit_meta) // 100
        score_used_step = 0

        if required_step > 0:
            score_used_step, deposit_meta_changed = self._charge_fee_from_virtual_step(
                context, deposit_meta, required_step, block_height)

            if score_used_step < required_step:
                required_icx = (required_step - score_used_step) * step_price
                charged_icx, deposit_indices_changed = self._charge_fee_from_deposit(
                    context, deposit_meta, required_icx, block_height)

                score_used_step += charged_icx // step_price
                deposit_meta_changed: bool = deposit_meta_changed or deposit_indices_changed

            if deposit_meta_changed:
                # Updates if the information has been changed
                context.storage.fee.put_deposit_meta(context, score_address, deposit_meta)

        return score_used_step

    def _charge_fee_from_virtual_step(self,
                                      context: 'IconScoreContext',
                                      deposit_meta: 'DepositMeta',
                                      required_step: int,
                                      block_height: int) -> (int, bytes):
        """
        Charges fees from available virtual STEPs
        Returns total charged amount and whether the properties of 'deposit_meta' are changed
        """
        charged_step = 0
        should_update_expire = False
        last_paid_deposit = None

        gen = self._deposit_generator(context, deposit_meta.available_head_id_of_virtual_step)
        for deposit in filter(lambda d: block_height < d.expires, gen):
            available_virtual_step = deposit.remaining_virtual_step

            if required_step < available_virtual_step:
                step = required_step
            else:
                step = available_virtual_step

                # All virtual steps are consumed in this loop.
                # So if this `expires` is the `max expires`, should find the next `max expires`.
                if deposit.expires == deposit_meta.expires_of_virtual_step:
                    should_update_expire = True

            if step > 0:
                deposit.consume_virtual_step(step)
                context.storage.fee.put_deposit(context, deposit)
                last_paid_deposit = deposit

                charged_step += step
                required_step -= step

                if required_step == 0:
                    break

        indices_changed = self._update_virtual_step_indices(
            context, deposit_meta, last_paid_deposit, should_update_expire, block_height)

        return charged_step, indices_changed

    def _update_virtual_step_indices(self,
                                     context: 'IconScoreContext',
                                     deposit_meta: 'DepositMeta',
                                     last_paid_deposit: 'Deposit',
                                     should_update_expire: bool,
                                     block_height: int) -> bool:
        """
        Updates indices of virtual steps to DepositMeta and returns whether there exist changes.
        """
        next_available_deposit = last_paid_deposit

        if last_paid_deposit is not None and last_paid_deposit.remaining_virtual_step == 0:
            # All virtual steps have been consumed in the current deposit
            # so should find the next available virtual steps
            gen = self._deposit_generator(context, last_paid_deposit.next_id)
            next_available_deposit = next(filter(lambda d: block_height < d.expires, gen), None)

        next_available_deposit_id = next_available_deposit.id if next_available_deposit else None
        next_expires = deposit_meta.expires_of_virtual_step

        if next_available_deposit_id is None:
            # This means that there are no available virtual steps in all deposits.
            next_expires = -1
        elif should_update_expire:
            # Finds next max expires. Sets to -1 if not exist.
            gen = self._deposit_generator(context, next_available_deposit_id)
            next_expires = max(map(lambda d: d.expires, gen), default=-1)

        if deposit_meta.available_head_id_of_virtual_step != next_available_deposit_id \
                or deposit_meta.expires_of_virtual_step != next_expires:
            # Updates and return True if some changes exist
            deposit_meta.available_head_id_of_virtual_step = next_available_deposit_id
            deposit_meta.expires_of_virtual_step = next_expires
            return True

        return False

    def _charge_fee_from_deposit(self,
                                 context: 'IconScoreContext',
                                 deposit_meta: 'DepositMeta',
                                 required_icx: int,
                                 block_height: int) -> (int, bool):
        """
        Charges fees from available deposit ICXs
        Returns total charged amount and whether the properties of 'deposit_meta' are changed
        """
        assert required_icx > 0

        if required_icx == 0:
            return 0, False

        remaining_required_icx = required_icx
        should_update_expire = False
        last_paid_deposit = None

        # Search for next available deposit id
        gen = self._deposit_generator(context, deposit_meta.available_head_id_of_deposit)
        for deposit in filter(lambda d: block_height < d.expires, gen):
            available_deposit = deposit.remaining_deposit - deposit.min_remaining_deposit

            if remaining_required_icx < available_deposit:
                charged_icx = remaining_required_icx
            else:
                charged_icx = available_deposit

                # All available deposits are consumed in this loop.
                # So if this `expires` is the `max expires`, should find the next `max expires`.
                if deposit.expires == deposit_meta.expires_of_deposit:
                    should_update_expire = True

            if charged_icx > 0:
                deposit.consume_deposit(charged_icx)
                context.storage.fee.put_deposit(context, deposit)
                last_paid_deposit = deposit

                remaining_required_icx -= charged_icx
                if remaining_required_icx == 0:
                    break

        if remaining_required_icx > 0:
            # Charges all remaining fee regardless of the minimum remaining amount.
            gen = self._deposit_generator(context, deposit_meta.head_id)
            for deposit in filter(lambda d: block_height < d.expires, gen):
                charged_icx = min(remaining_required_icx, deposit.remaining_deposit)

                if charged_icx > 0:
                    deposit.consume_deposit(charged_icx)
                    context.storage.fee.put_deposit(context, deposit)

                    remaining_required_icx -= charged_icx
                    if remaining_required_icx == 0:
                        break

        indices_changed = self._update_deposit_indices(
            context, deposit_meta, last_paid_deposit, should_update_expire, block_height)

        return required_icx - remaining_required_icx, indices_changed

    def _update_deposit_indices(self,
                                context: 'IconScoreContext',
                                deposit_meta: 'DepositMeta',
                                last_paid_deposit: 'Deposit',
                                should_update_expire: bool,
                                block_height: int) -> bool:
        """
        Updates indices of deposit to deposit_meta and returns whether there exist changes.
        """

        next_available_deposit = last_paid_deposit

        if last_paid_deposit.remaining_deposit <= last_paid_deposit.min_remaining_deposit:
            # All available deposits have been consumed in the current deposit
            # so should find the next available deposits
            gen = self._deposit_generator(context, last_paid_deposit.next_id)
            next_available_deposit = next(filter(lambda d: block_height < d.expires, gen), None)

        next_available_deposit_id = next_available_deposit.id if next_available_deposit else None
        next_expires = deposit_meta.expires_of_deposit

        if next_available_deposit_id is None:
            # This means that there are no available deposits.
            next_expires = -1
        elif should_update_expire:
            # Finds next max expires. Sets to -1 if not exist.
            gen = self._deposit_generator(context, next_available_deposit_id)
            next_expires = max(map(lambda d: d.expires, gen), default=-1)

        if deposit_meta.available_head_id_of_deposit != next_available_deposit_id \
                or deposit_meta.expires_of_deposit != next_expires:
            # Updates and return True if changes are exist
            deposit_meta.available_head_id_of_deposit = next_available_deposit_id
            deposit_meta.expires_of_deposit = next_expires
            return True

        return False

    def _deposit_generator(self, context: 'IconScoreContext', start_id: Optional[bytes]):
        next_id = start_id
        while next_id is not None:
            deposit = context.storage.fee.get_deposit(context, next_id)
            if deposit is None:
                break

            yield deposit
            next_id = deposit.next_id

    def _get_score_deploy_info(self, context: 'IconScoreContext', score_address: 'Address') -> 'IconScoreDeployInfo':
        deploy_info: 'IconScoreDeployInfo' = context.storage.deploy.get_deploy_info(context, score_address)

        if deploy_info is None:
            raise InvalidRequestException('Invalid SCORE')

        return deploy_info

    def _check_score_valid(self, context: 'IconScoreContext', score_address: 'Address') -> None:
        deploy_info = self._get_score_deploy_info(context, score_address)
        assert deploy_info is not None

    def _check_score_ownership(self, context: 'IconScoreContext', sender: 'Address', score_address: 'Address') -> None:
        deploy_info = self._get_score_deploy_info(context, score_address)

        if deploy_info.owner != sender:
            raise InvalidRequestException('Invalid SCORE owner')

    @staticmethod
    def _check_deposit_id(deposit_id: bytes) -> None:
        if not (isinstance(deposit_id, bytes) and len(deposit_id) == 32):
            raise InvalidRequestException('Invalid deposit ID')

    def _get_or_create_deposit_meta(
            self, context: 'IconScoreContext', score_address: 'Address') -> 'DepositMeta':
        deposit_meta = context.storage.fee.get_deposit_meta(context, score_address)
        return deposit_meta if deposit_meta else DepositMeta()

    @staticmethod
    def _calculate_penalty(deposit: 'Deposit',
                           block_height: int,
                           step_price: int) -> int:
        assert isinstance(deposit, Deposit)
        assert isinstance(block_height, int)
        assert isinstance(step_price, int)

        if block_height >= deposit.expires:
            return 0

        return VirtualStepCalculator.calculate_penalty(
            deposit.virtual_step_used,
            step_price)


class VirtualStepCalculator:
    """
    Calculator for generating Virtual Step
    """

    @classmethod
    def calculate_virtual_step(cls,
                               deposit_amount: int,
                               term: int,
                               step_price: int) -> int:
        """Returns issuance of virtual-step according to deposit_amount and term

        :param deposit_amount: deposit amount in loop unit
        :param term: deposit term
        :param step_price:
        """
        assert term == BLOCKS_IN_ONE_MONTH
        return int(Decimal(deposit_amount) * Decimal(FIXED_RATIO_PER_MONTH) / Decimal(step_price))

    @classmethod
    def calculate_penalty(cls,
                          virtual_step_used: int,
                          step_price: int) -> int:
        """Returns penalty according to given parameters

        :param virtual_step_used:
        :param step_price:
        """
        return virtual_step_used * step_price


class DepositHandler:
    """
    Deposit Handler
    """

    # For eventlog emitting
    class EventType(IntEnum):
        DEPOSIT = 0
        WITHDRAW = 1

    SIGNATURE_AND_INDEX = (
        # DepositAdded(id: bytes, from_: Address, amount: int, term: int)
        ('DepositAdded(bytes,Address,int,int)', 2),
        # DepositWithdrawn(id: bytes, from_: Address, returnAmount: int, penalty: int)
        ('DepositWithdrawn(bytes,Address,int,int)', 2)
    )

    @staticmethod
    def get_signature_and_index_count(event_type: 'EventType') -> (str, int):
        return DepositHandler.SIGNATURE_AND_INDEX[event_type]

    def __init__(self):
        pass

    def handle_deposit_request(self, context: 'IconScoreContext', data: dict):
        """
        Handles fee request(querying or invoking)

        :param context: IconScoreContext
        :param data: data field
        :return:
        """
        converted_data = TypeConverter.convert(data, ParamType.DEPOSIT_DATA)
        action = converted_data['action']

        try:
            if action == 'add':
                term: int = BLOCKS_IN_ONE_MONTH if FIXED_TERM else converted_data['term']
                self._add_deposit(context, term)
            elif action == 'withdraw':
                self._withdraw_deposit(context, converted_data['id'])
            else:
                raise InvalidRequestException(f"Invalid action: {action}")
        except KeyError:
            # missing required params for the action
            raise InvalidParamsException("Required params not found")

    def _add_deposit(self, context: 'IconScoreContext', term: int):
        context.engine.fee.add_deposit(context, context.tx.hash, context.msg.sender, context.tx.to,
                                       context.msg.value, context.block.height, term)

        event_log_args = [context.tx.hash, context.msg.sender, context.msg.value, term]
        self._emit_event(context, DepositHandler.EventType.DEPOSIT, event_log_args)

    def _withdraw_deposit(self, context: 'IconScoreContext', deposit_id: bytes):
        if context.msg.value != 0:
            raise InvalidRequestException(f'Invalid value: must be zero')
        withdrawal_amount, penalty = context.engine.fee.withdraw_deposit(
            context, context.msg.sender, deposit_id, context.block.height)

        event_log_args = [deposit_id, context.msg.sender, withdrawal_amount, penalty]
        self._emit_event(context, DepositHandler.EventType.WITHDRAW, event_log_args)

    @staticmethod
    def _emit_event(context: 'IconScoreContext', event_type: 'DepositHandler.EventType', event_log_args: list):
        signature, index_count = DepositHandler.get_signature_and_index_count(event_type)

        fee_charge: bool = True if context.revision < Revision.IISS.value else False
        EventLogEmitter.emit_event_log(
            context, context.tx.to, signature, event_log_args, index_count, fee_charge)
