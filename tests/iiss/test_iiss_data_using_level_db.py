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

import unittest
from typing import TYPE_CHECKING

import plyvel

from iconservice.iiss.reward_calc.msg_data import Header, GovernanceVariable, PRepsData, TxData, TxType, \
    DelegationTx, DelegationInfo, PRepRegisterTx, PRepUnregisterTx, BlockProduceInfoData
from tests import create_address

if TYPE_CHECKING:
    from iconservice.base.address import Address


class TestIissDataUsingLevelDB(unittest.TestCase):
    db_path: str = './mock_db'

    def setUp(self):
        self.db = plyvel.DB('./mock_db', create_if_missing=True)
        self.debug = True

        self.iiss_header: 'Header' = Header()
        self.iiss_header.version = 10
        self.iiss_header.block_height = 20

        self.iiss_gv: 'GovernanceVariable' = GovernanceVariable()
        self.iiss_gv.block_height = 20
        self.iiss_gv.calculated_incentive_rep = 30
        self.iiss_gv.reward_rep = 10_000

        self.iiss_block_produce_info: 'BlockProduceInfoData' = BlockProduceInfoData()
        self.iiss_block_produce_info.block_height = 20
        self.iiss_block_produce_info.block_generator = create_address(data=b'generator_address')
        list_of_address = []
        for x in range(0, 10):
            list_of_address.append(create_address(data=b'address' + x.to_bytes(1, 'big')))
        self.iiss_block_produce_info.block_validator_list = list_of_address

        self.iiss_prep: 'PRepsData' = PRepsData()
        self.iiss_prep.block_height = 20
        self.iiss_prep.total_delegation = 10_000

        self.iiss_prep.prep_list = []
        for x in range(0, 10):
            delegate_info: 'DelegationInfo' = DelegationInfo()
            delegate_info.address = create_address(data=b'address' + x.to_bytes(1, 'big'))
            delegate_info.value = 10 ** 10
            self.iiss_prep.prep_list.append(delegate_info)

        self.tx_delegate: 'TxData' = TxData()
        self.tx_delegate_index: int = 1
        self.tx_delegate.address: 'Address' = create_address(data=b'addr2')
        self.tx_delegate.block_height: int = 10 ** 3
        self.tx_delegate.type: 'TxType' = TxType.DELEGATION
        self.tx_delegate.data: 'DelegationTx' = DelegationTx()

        delegate_info: 'DelegationInfo' = DelegationInfo()
        delegate_info.address = create_address(data=b'addr3')
        delegate_info.value = 10 ** 10
        self.tx_delegate.data.delegation_info.append(delegate_info)

        delegate_info: 'DelegationInfo' = DelegationInfo()
        delegate_info.address = create_address(data=b'addr4')
        delegate_info.value = 10 ** 20
        self.tx_delegate.data.delegation_info.append(delegate_info)

        self.tx_prep_reg: 'TxData' = TxData()
        self.tx_prep_reg_index: int = 3
        self.tx_prep_reg.address: 'Address' = create_address(data=b'addr6')
        self.tx_prep_reg.block_height: int = 10 ** 3
        self.tx_prep_reg.type: 'TxType' = TxType.PREP_REGISTER
        self.tx_prep_reg.data: 'PRepRegisterTx' = PRepRegisterTx()

        self.tx_prep_un_reg: 'TxData' = TxData()
        self.tx_prep_un_reg_index: int = 4
        self.tx_prep_un_reg.address: 'Address' = create_address(data=b'addr7')
        self.tx_prep_un_reg.block_height: int = 10 ** 3
        self.tx_prep_un_reg.type: 'TxType' = TxType.PREP_UNREGISTER
        self.tx_prep_un_reg.data: 'PRepUnregisterTx' = PRepUnregisterTx()

    def tearDown(self):
        #rmtree(self.db_path)
        pass

    def test_iiss_data_using_level_db(self):
        self._dump_mock_db()
        self._load_mock_db()

    def test_iiss_header_data(self):
        value: bytes = self.iiss_header.make_value()
        ret_h: 'Header' = self.iiss_header.from_bytes(value)

        self.assertEqual(self.iiss_header.version, ret_h.version)
        self.assertEqual(self.iiss_header.block_height, ret_h.block_height)

    def test_iiss_governance_variable_data(self):
        key: bytes = self.iiss_gv.make_key()
        value: bytes = self.iiss_gv.make_value()
        ret_gv: 'GovernanceVariable' = self.iiss_gv.from_bytes(key, value)

        self.assertEqual(self.iiss_gv.block_height, ret_gv.block_height)
        self.assertEqual(self.iiss_gv.calculated_incentive_rep, ret_gv.calculated_incentive_rep)
        self.assertEqual(self.iiss_gv.reward_rep, ret_gv.reward_rep)

    def test_iiss_block_produce_info_data(self):
        key: bytes = self.iiss_block_produce_info.make_key()
        value: bytes = self.iiss_block_produce_info.make_value()
        ret_bp: 'BlockProduceInfoData' = self.iiss_block_produce_info.from_bytes(key, value)

        self.assertEqual(self.iiss_block_produce_info.block_height, ret_bp.block_height)
        self.assertEqual(self.iiss_block_produce_info.block_generator, ret_bp.block_generator)
        self.assertEqual(self.iiss_block_produce_info.block_validator_list, ret_bp.block_validator_list)

    def test_preps_data(self):
        key: bytes = self.iiss_prep.make_key()
        value: bytes = self.iiss_prep.make_value()
        ret_p: 'PRepsData' = self.iiss_prep.from_bytes(key, value)

        self.assertEqual(self.iiss_prep.block_height, ret_p.block_height)
        self.assertEqual(self.iiss_prep.total_delegation, ret_p.total_delegation)
        for index, iiss_prep in enumerate(self.iiss_prep.prep_list):
            self.assertEqual(iiss_prep.value, ret_p.prep_list[index].value)
            self.assertEqual(iiss_prep.address, ret_p.prep_list[index].address)

    def test_iiss_tx_data_delegate(self):
        key: bytes = self.tx_delegate.make_key(self.tx_delegate_index)
        value: bytes = self.tx_delegate.make_value()
        ret_tx: 'TxData' = self.tx_delegate.from_bytes(value)
        expected_key = b'TX' + self.tx_delegate_index.to_bytes(8, byteorder='big')

        self.assertEqual(expected_key, key)
        self.assertEqual(self.tx_delegate.address, ret_tx.address)
        self.assertEqual(self.tx_delegate.block_height, ret_tx.block_height)
        self.assertEqual(self.tx_delegate.type, ret_tx.type)

        self.assertEqual(self.tx_delegate.data.delegation_info[0].address, ret_tx.data.delegation_info[0].address)
        self.assertEqual(self.tx_delegate.data.delegation_info[0].value, ret_tx.data.delegation_info[0].value)
        self.assertEqual(self.tx_delegate.data.delegation_info[1].address, ret_tx.data.delegation_info[1].address)
        self.assertEqual(self.tx_delegate.data.delegation_info[1].value, ret_tx.data.delegation_info[1].value)

    def test_iiss_tx_data_preb_reg_tx(self):
        key: bytes = self.tx_delegate.make_key(self.tx_prep_reg_index)
        value: bytes = self.tx_prep_reg.make_value()
        ret_tx: 'TxData' = self.tx_prep_reg.from_bytes(value)

        expected_key = b'TX' + self.tx_prep_reg_index.to_bytes(8, byteorder='big')
        self.assertEqual(expected_key, key)
        self.assertEqual(self.tx_prep_reg.address, ret_tx.address)
        self.assertEqual(self.tx_prep_reg.block_height, ret_tx.block_height)
        self.assertEqual(self.tx_prep_reg.type, ret_tx.type)

    def test_iiss_tx_data_preb_un_reg_tx(self):
        key: bytes = self.tx_delegate.make_key(self.tx_prep_un_reg_index)
        value: bytes = self.tx_prep_un_reg.make_value()
        ret_tx: 'TxData' = self.tx_prep_un_reg.from_bytes(value)

        expected_key = b'TX' + self.tx_prep_un_reg_index.to_bytes(8, byteorder='big')
        self.assertEqual(expected_key, key)
        self.assertEqual(self.tx_prep_un_reg.address, ret_tx.address)
        self.assertEqual(self.tx_prep_un_reg.block_height, ret_tx.block_height)
        self.assertEqual(self.tx_prep_un_reg.type, ret_tx.type)

    def _dump_mock_db(self):
        key: bytes = self.iiss_header.make_key()
        value: bytes = self.iiss_header.make_value()
        self.db.put(key, value)

        if self.debug:
            print("===IISS_HEADER===")
            print(f"version: {self.iiss_header.version}")
            print(f"block_height: {self.iiss_header.block_height}")
            print(f"key: {key}")
            print(f"value: {value}")
            print("")

        key: bytes = self.iiss_gv.make_key()
        value: bytes = self.iiss_gv.make_value()
        self.db.put(key, value)

        if self.debug:
            print("===IISS_GOVERNANCE_VARIABLE===")
            print(f"block_height: {self.iiss_gv.block_height}")
            print(f"calculated incentive_rep: {self.iiss_gv.calculated_incentive_rep}")
            print(f"reward_rep: {self.iiss_gv.reward_rep}")
            print(f"key: {key}")
            print(f"value: {value}")
            print("")

        key: bytes = self.iiss_block_produce_info.make_key()
        value: bytes = self.iiss_block_produce_info.make_value()
        self.db.put(key, value)

        if self.debug:
            print("===IISS_BLOCK_PRODUCE_INFO_DATA===")
            print(f"block_height: {self.iiss_block_produce_info.block_height}")
            print(f"block_generator: {str(self.iiss_block_produce_info.block_generator)}")
            print(f"block_validator_list: {[str(address)for address in self.iiss_block_produce_info.block_validator_list]}")
            print(f"key: {key}")
            print(f"value: {value}")
            print("")

        key: bytes = self.iiss_prep.make_key()
        value: bytes = self.iiss_prep.make_value()
        self.db.put(key, value)

        if self.debug:
            prep_list: list = [[str(prep.address), prep.value] for prep in self.iiss_prep.prep_list]
            print("===PREPS_DATA===")
            print(f"block_height: {self.iiss_prep.block_height}")
            print(f"total_delegation: {self.iiss_prep.total_delegation}")
            print(f"prep_list: {prep_list}")
            print(f"key: {key}")
            print(f"value: {value}")
            print("")

        key: bytes = self.tx_delegate.make_key(self.tx_delegate_index)
        value: bytes = self.tx_delegate.make_value()
        self.db.put(key, value)

        if self.debug:
            print("===IISS_TX_DATA-1===")
            print(f"index: {self.tx_delegate_index}")
            print(f"address: {self.tx_delegate.address}")
            print(f"block_height: {self.tx_delegate.block_height}")
            print(f"type: {self.tx_delegate.type}")
            print(f"ori_delegate: {[(str(x.address), x.value) for x in self.tx_delegate.data.delegation_info]}")
            print(f"delegate: {self.tx_delegate.data.encode()}")
            print(f"key: {key}")
            print(f"value: {value}")
            print("")

        key: bytes = self.tx_prep_reg.make_key(self.tx_prep_reg_index)
        value: bytes = self.tx_prep_reg.make_value()
        self.db.put(key, value)

        if self.debug:
            print("===IISS_TX_DATA-2===")
            print(f"index: {self.tx_prep_reg_index}")
            print(f"address: {self.tx_prep_reg.address}")
            print(f"block_height: {self.tx_prep_reg.block_height}")
            print(f"type: {self.tx_prep_reg.type}")
            print(f"data: {self.tx_prep_reg.data.encode()}")
            print(f"key: {key}")
            print(f"value: {value}")
            print("")

        key: bytes = self.tx_prep_un_reg.make_key(self.tx_prep_un_reg_index)
        value: bytes = self.tx_prep_un_reg.make_value()
        self.db.put(key, value)

        if self.debug:
            print("===IISS_TX_DATA-3===")
            print(f"index: {self.tx_prep_un_reg_index}")
            print(f"address: {self.tx_prep_un_reg.address}")
            print(f"block_height: {self.tx_prep_un_reg.block_height}")
            print(f"type: {self.tx_prep_un_reg.type}")
            print(f"data: {self.tx_prep_un_reg.data.encode()}")
            print(f"key: {key}")
            print(f"value: {value}")
            print("")

    def _load_mock_db(self):
        key: bytes = self.iiss_header.make_key()
        value = self.db.get(key)
        ret_h: 'Header' = self.iiss_header.from_bytes(value)

        self.assertEqual(self.iiss_header.version, ret_h.version)
        self.assertEqual(self.iiss_header.block_height, ret_h.block_height)

        key: bytes = self.iiss_gv.make_key()
        value = self.db.get(key)
        ret_gv: 'GovernanceVariable' = self.iiss_gv.from_bytes(key, value)

        self.assertEqual(self.iiss_gv.block_height, ret_gv.block_height)
        self.assertEqual(self.iiss_gv.calculated_incentive_rep, ret_gv.calculated_incentive_rep)
        self.assertEqual(self.iiss_gv.reward_rep, ret_gv.reward_rep)

        key: bytes = self.iiss_block_produce_info.make_key()
        value = self.db.get(key)
        ret_bp: 'BlockProduceInfoData' = self.iiss_block_produce_info.from_bytes(key, value)

        self.assertEqual(self.iiss_block_produce_info.block_height, ret_bp.block_height)
        self.assertEqual(self.iiss_block_produce_info.block_generator, ret_bp.block_generator)
        self.assertEqual(self.iiss_block_produce_info.block_validator_list, ret_bp.block_validator_list)

        key: bytes = self.iiss_prep.make_key()
        value = self.db.get(key)
        ret_p: 'PRepsData' = self.iiss_prep.from_bytes(key, value)

        self.assertEqual(self.iiss_prep.block_height, ret_p.block_height)
        self.assertEqual(self.iiss_prep.total_delegation, ret_p.total_delegation)
        for index, iiss_prep in enumerate(self.iiss_prep.prep_list):
            self.assertEqual(iiss_prep.value, ret_p.prep_list[index].value)
            self.assertEqual(iiss_prep.address, ret_p.prep_list[index].address)

        key: bytes = self.tx_delegate.make_key(self.tx_delegate_index)
        value = self.db.get(key)
        ret_tx: 'TxData' = self.tx_delegate.from_bytes(value)

        expected_key = b'TX' + self.tx_delegate_index.to_bytes(8, byteorder='big')
        self.assertEqual(expected_key, key)
        self.assertEqual(self.tx_delegate.address, ret_tx.address)
        self.assertEqual(self.tx_delegate.block_height, ret_tx.block_height)
        self.assertEqual(self.tx_delegate.type, ret_tx.type)

        self.assertEqual(self.tx_delegate.data.delegation_info[0].address, ret_tx.data.delegation_info[0].address)
        self.assertEqual(self.tx_delegate.data.delegation_info[0].value, ret_tx.data.delegation_info[0].value)
        self.assertEqual(self.tx_delegate.data.delegation_info[1].address, ret_tx.data.delegation_info[1].address)
        self.assertEqual(self.tx_delegate.data.delegation_info[1].value, ret_tx.data.delegation_info[1].value)

        key: bytes = self.tx_prep_reg.make_key(self.tx_prep_reg_index)
        value = self.db.get(key)
        ret_tx: 'TxData' = self.tx_prep_reg.from_bytes(value)

        expected_key = b'TX' + self.tx_prep_reg_index.to_bytes(8, byteorder='big')
        self.assertEqual(expected_key, key)
        self.assertEqual(self.tx_prep_reg.address, ret_tx.address)
        self.assertEqual(self.tx_prep_reg.block_height, ret_tx.block_height)
        self.assertEqual(self.tx_prep_reg.type, ret_tx.type)

        key: bytes = self.tx_prep_un_reg.make_key(self.tx_prep_un_reg_index)
        value = self.db.get(key)
        ret_tx: 'TxData' = self.tx_prep_un_reg.from_bytes(value)

        expected_key = b'TX' + self.tx_prep_un_reg_index.to_bytes(8, byteorder='big')
        self.assertEqual(expected_key, key)
        self.assertEqual(self.tx_prep_un_reg.address, ret_tx.address)
        self.assertEqual(self.tx_prep_un_reg.block_height, ret_tx.block_height)
        self.assertEqual(self.tx_prep_un_reg.type, ret_tx.type)


if __name__ == '__main__':
    unittest.main()
