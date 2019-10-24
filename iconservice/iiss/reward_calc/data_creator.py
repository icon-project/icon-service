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

from typing import TYPE_CHECKING, List, Iterable, Tuple

from iconcommons import Logger
from ..reward_calc.msg_data import Header, GovernanceVariable, PRepsData, TxData, \
    DelegationTx, DelegationInfo, PRepRegisterTx, PRepUnregisterTx, BlockProduceInfoData

if TYPE_CHECKING:
    from ...base.address import Address
    from ...prep.data import PRepSnapshot
    from ..reward_calc.msg_data import Tx


class DataCreator:
    TAG = "IISS"

    @staticmethod
    def create_header(version: int, block_height: int, revision: int) -> 'Header':
        data = Header()
        data.version = version
        data.block_height = block_height
        data.revision = revision
        return data

    @staticmethod
    def create_gv_variable(version: int,
                           block_height: int,
                           calculated_irep: int,
                           reward_rep: int,
                           config_main_prep_count: int,
                           config_main_and_sub_prep_count: int) -> 'GovernanceVariable':
        data = GovernanceVariable()
        data.version = version
        data.block_height = block_height
        data.calculated_irep = calculated_irep
        data.reward_rep = reward_rep
        data.config_main_prep_count = config_main_prep_count
        data.config_sub_prep_count = config_main_and_sub_prep_count - config_main_prep_count
        return data

    @staticmethod
    def create_block_produce_info_data(block_height: int,
                                       block_generator: 'Address',
                                       block_votes: List[Tuple['Address', int]]) -> 'BlockProduceInfoData':

        block_validators = [address for address, is_valid in block_votes if is_valid]

        data = BlockProduceInfoData()
        data.block_height = block_height
        data.block_generator = block_generator
        data.block_validator_list = block_validators
        return data

    @classmethod
    def create_prep_data(cls,
                         block_height: int,
                         total_delegation: int,
                         preps: Iterable['PRepSnapshot']) -> 'PRepsData':
        """

        :param block_height:
        :param total_delegation: total delegation of main and sub P-Reps
        :param preps: main and sub P-Reps
        :return:
        """

        converted_preps: List['DelegationInfo'] = []
        for prep_snapshot in preps:
            Logger.debug(tag=cls.TAG, msg=f"create_prep_data: {str(prep_snapshot.address)}")
            info = DataCreator.create_delegation_info(prep_snapshot.address, prep_snapshot.delegated)
            converted_preps.append(info)

        data = PRepsData()
        data.block_height = block_height
        data.total_delegation = total_delegation
        data.prep_list = converted_preps
        return data

    @staticmethod
    def create_tx(address: 'Address', block_height: int, tx_data: 'Tx') -> 'TxData':
        data = TxData()
        data.address = address
        data.block_height = block_height
        data.data = tx_data
        return data

    @staticmethod
    def create_tx_delegation(delegation_infos: list) -> 'DelegationTx':
        tx = DelegationTx()
        tx.delegation_info = delegation_infos
        return tx

    @classmethod
    def create_delegation_info(cls, address: 'Address', value: int) -> 'DelegationInfo':
        info = DelegationInfo()
        info.address = address
        info.value = value
        Logger.debug(f"create_delegation_info: {info.address}", cls.TAG)
        return info

    @staticmethod
    def create_tx_prep_reg() -> 'PRepRegisterTx':
        tx = PRepRegisterTx()
        return tx

    @staticmethod
    def create_tx_prep_unreg() -> 'PRepUnregisterTx':
        tx = PRepUnregisterTx()
        return tx
