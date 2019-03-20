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
from collections import namedtuple
from typing import List, Optional

from ..icx.icx_engine import IcxEngine
from ..icx.icx_storage import IcxStorage

if typing.TYPE_CHECKING:
    from ..base.address import Address

# Represents a number of available STEPs.
AvailableStep = namedtuple('AvailableStep', 'sender_step receiver_step')


class Deposit:
    """
    Deposit information
    """

    def __init__(self, deposit_id: bytes, score_address: 'Address', sender_address: 'Address'):
        # deposit id, should be tx hash of deposit transaction
        self.id: bytes = deposit_id
        # target SCORE address
        self.score_address: 'Address' = score_address
        # sender address
        self.sender_address: 'Address' = sender_address
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

    def __init__(self, icx_storage: 'IcxStorage', icx_engine: 'IcxEngine'):
        pass

    def set_fee_sharing_ratio(self, score_address: 'Address', ratio: int) -> None:
        """
        Sets fee sharing ratio that SCORE pays.


        :param score_address: SCORE address
        :param ratio: sharing ratio in percent (0-100)
        """
        pass

    def get_score_fee_info(self, score_address: 'Address') -> ScoreFeeInfo:
        """
        Gets SCORE information

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
                    tx_hash: bytes,
                    score_address: 'Address',
                    from_: 'Address',
                    amount: int,
                    block_number: int,
                    period: int) -> None:
        """
        Deposits ICXs for the SCORE.
        It may be issued the virtual STEPs for the SCORE to be able to pay share fees.

        :param tx_hash: tx hash of the deposit transaction
        :param score_address: SCORE
        :param from_: ICX sender
        :param amount: amount of ICXs in loop
        :param block_number: current block height
        :param period: deposit period in blocks
        """
        # [Sub Task]
        # - Deposits ICX
        # - Calculates Virtual Step
        # - Updates Deposit Data
        pass

    def withdraw_fee(self, deposit_id: bytes, block_number: int) -> None:
        """
        Withdraws deposited ICXs from given id.
        It may be paid the penalty if the expiry has not been met.

        :param deposit_id: deposit id, should be tx hash of deposit transaction
        :param block_number: current block height
        """
        # [Sub Task]
        # - Checks if the contract period is finished
        # - if the period is not finished, calculates and apply a penalty
        # - Update ICX
        pass

    def get_deposit_info_by_id(self, deposit_id: bytes) -> Optional[Deposit]:
        """
        Gets the deposit information. Returns None if the deposit from the given id does not exist.

        :param deposit_id: deposit id, should be tx hash of deposit transaction
        :return: deposit information
        """

        return None

    # TODO : get_score_info_by_EOA

    def get_available_step(self, to: 'Address', sender_step_limit: int) -> AvailableStep:
        """
        Gets the usable STEPs for the given step_limit from the sender.
        The return value is a tuple of the sender's one and receiver's one.

        :param to: msg receiver
        :param sender_step_limit: step_limit from sender
        :return: (sender_step, receiver_step)
        """

        # Get the SCORE's ratio
        # Calculate ratio * SCORE and (1-ratio) * msg sender
        # Checks msg sender account
        # Checks SCORE owner account
        return 0, 0

    def charge_transaction_fee(
            self, from_: 'Address', to: 'Address', step_price: int, used_step: int) -> None:
        """
        Charges fees for the used STEPs.
        It can pay by shared if the msg receiver set to share fees.

        :param from_: msg sender
        :param to: msg receiver
        :param step_price: current STEP price
        :param used_step: used STEPs
        """
        pass
