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

from typing import TYPE_CHECKING, List

from iconcommons import Logger
from ..reward_calc.msg_data import Header, GovernanceVariable, PRepsData, TxData, \
    DelegationTx, DelegationInfo, PRepRegisterTx, PRepUnregisterTx, BlockProduceInfoData

if TYPE_CHECKING:
    from ...base.address import Address
    from ..reward_calc.msg_data import Tx
    from ...prep.data import PRep


class DataCreator:
    @staticmethod
    def create_header(version: int, block_height: int) -> 'Header':
        data = Header()
        data.version: int = version
        data.block_height: int = block_height
        return data

    @staticmethod
    def create_gv_variable(block_height: int,
                           calculated_irep: int,
                           reward_rep: int) -> 'GovernanceVariable':
        data = GovernanceVariable()
        data.block_height: int = block_height
        data.calculated_irep: int = calculated_irep
        data.reward_rep: int = reward_rep
        return data

    @staticmethod
    def create_block_produce_info_data(block_height: int,
                                       block_generator: 'Address',
                                       block_validators: List['Address']) -> 'BlockProduceInfoData':
        data = BlockProduceInfoData()
        data.block_height: int = block_height
        data.block_generator: 'Address' = block_generator
        data.block_validator_list: List['Address'] = block_validators
        return data

    @staticmethod
    def create_prep_data(block_height: int, total_delegation: int, preps: List['PRep']) -> 'PRepsData':

        converted_preps: List['DelegationInfo'] = []
        for prep in preps:
            Logger.debug(f"create_prep_data: {str(prep.address)}", "iiss")
            info = DataCreator.create_delegation_info(prep.address, prep.delegated)
            converted_preps.append(info)

        data = PRepsData()
        data.block_height: int = block_height
        data.total_delegation: int = total_delegation
        data.prep_list: List['DelegationInfo'] = converted_preps
        return data

    @staticmethod
    def create_tx(address: 'Address', block_height: int, tx_data: 'Tx') -> 'TxData':
        data = TxData()
        data.address: 'Address' = address
        data.block_height: int = block_height
        data.data: 'Tx' = tx_data
        return data

    @staticmethod
    def create_tx_delegation(delegation_infos: list) -> 'DelegationTx':
        tx = DelegationTx()
        tx.delegation_info: list = delegation_infos
        return tx

    @staticmethod
    def create_delegation_info(address: 'Address', value: int) -> 'DelegationInfo':
        info = DelegationInfo()
        info.address: 'Address' = address
        info.value: int = value
        Logger.debug(f"create_delegation_info: {str(info.address)}", "iiss")
        return info

    @staticmethod
    def create_tx_prep_reg() -> 'PRepRegisterTx':
        tx = PRepRegisterTx()
        return tx

    @staticmethod
    def create_tx_prep_unreg() -> 'PRepUnregisterTx':
        tx = PRepUnregisterTx()
        return tx
