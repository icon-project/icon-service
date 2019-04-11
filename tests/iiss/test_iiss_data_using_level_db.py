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

import plyvel
import unittest
from typing import TYPE_CHECKING

from iconservice.iiss.iiss_msg_data import IissHeader, IissGovernanceVariable, PrepsData, IissTxData, IissTxType, \
    DelegationTx, DelegationInfo, PRepRegisterTx, PRepUnregisterTx
from tests import create_address, rmtree

if TYPE_CHECKING:
    from iconservice.base.address import Address


class TestIissDataUsingLevelDB(unittest.TestCase):
    db_path: str = './mock_db'

    def setUp(self):
        self.db = plyvel.DB('./mock_db', create_if_missing=True)
        self.debug = True

        self.iiss_header: 'IissHeader' = IissHeader()
        self.iiss_header.version = 10
        self.iiss_header.block_height = 20

        self.iiss_gv: 'IissGovernanceVariable' = IissGovernanceVariable()
        self.iiss_gv.block_height = 20
        self.iiss_gv.icx_price = 10
        self.iiss_gv.incentive_rep = 30
        self.iiss_gv.reward_rep = 10_000

        self.iiss_prep: 'PrepsData' = PrepsData()
        self.iiss_prep.block_height = 20
        self.iiss_prep.block_generator = create_address(data=b'generator_address')
        list_of_address = []
        for x in range(0, 10):
            list_of_address.append(create_address(data=b'address' + x.to_bytes(1, 'big')))
        self.iiss_prep.block_validator_list = list_of_address

        self.tx_delegate: 'IissTxData' = IissTxData()
        self.tx_delegate.index: int = 1
        self.tx_delegate.address: 'Address' = create_address(data=b'addr2')
        self.tx_delegate.block_height: int = 10 ** 3
        self.tx_delegate.type: 'IissTxType' = IissTxType.DELEGATION
        self.tx_delegate.data: 'DelegationTx' = DelegationTx()

        delegate_info: 'DelegationInfo' = DelegationInfo()
        delegate_info.address = create_address(data=b'addr3')
        delegate_info.value = 10 ** 10
        self.tx_delegate.data.delegation_info.append(delegate_info)

        delegate_info: 'DelegationInfo' = DelegationInfo()
        delegate_info.address = create_address(data=b'addr4')
        delegate_info.value = 10 ** 20
        self.tx_delegate.data.delegation_info.append(delegate_info)

        self.tx_prep_reg: 'IissTxData' = IissTxData()
        self.tx_prep_reg.index: int = 3
        self.tx_prep_reg.address: 'Address' = create_address(data=b'addr6')
        self.tx_prep_reg.block_height: int = 10 ** 3
        self.tx_prep_reg.type: 'IissTxType' = IissTxType.PREP_REGISTER
        self.tx_prep_reg.data: 'PRepRegisterTx' = PRepRegisterTx()

        self.tx_prep_un_reg: 'IissTxData' = IissTxData()
        self.tx_prep_un_reg.index: int = 4
        self.tx_prep_un_reg.address: 'Address' = create_address(data=b'addr7')
        self.tx_prep_un_reg.block_height: int = 10 ** 3
        self.tx_prep_un_reg.type: 'IissTxType' = IissTxType.PREP_UNREGISTER
        self.tx_prep_un_reg.data: 'PRepUnregisterTx' = PRepUnregisterTx()

    def tearDown(self):
        rmtree(self.db_path)
        pass

    def test_iiss_data_using_level_db(self):
        self._dump_mock_db()
        self._load_mock_db()

    def test_iiss_header_data(self):
        data: bytes = self.iiss_header.make_value()
        ret_h: 'IissHeader' = self.iiss_header.from_bytes(data)

        self.assertEqual(self.iiss_header.version, ret_h.version)
        self.assertEqual(self.iiss_header.block_height, ret_h.block_height)

    def test_iiss_governance_variable_data(self):
        key: bytes = self.iiss_gv.make_key()
        data: bytes = self.iiss_gv.make_value()
        ret_gv: 'IissGovernanceVariable' = self.iiss_gv.from_bytes(key, data)

        self.assertEqual(self.iiss_gv.block_height, ret_gv.block_height)
        self.assertEqual(self.iiss_gv.icx_price, ret_gv.icx_price)
        self.assertEqual(self.iiss_gv.incentive_rep, ret_gv.incentive_rep)
        self.assertEqual(self.iiss_gv.reward_rep, ret_gv.reward_rep)

    def test_preps_data(self):
        key: bytes = self.iiss_prep.make_key()
        data: bytes = self.iiss_prep.make_value()
        ret_p: 'PrepsData' = self.iiss_prep.from_bytes(key, data)

        self.assertEqual(self.iiss_prep.block_height, ret_p.block_height)
        self.assertEqual(self.iiss_prep.block_generator, ret_p.block_generator)
        self.assertEqual(self.iiss_prep.block_validator_list, ret_p.block_validator_list)

    def test_iiss_tx_data_delegate(self):
        data: bytes = self.tx_delegate.make_value()
        ret_tx: 'IissTxData' = self.tx_delegate.from_bytes(self.tx_delegate.index, data)

        self.assertEqual(self.tx_delegate.index, ret_tx.index)
        self.assertEqual(self.tx_delegate.address, ret_tx.address)
        self.assertEqual(self.tx_delegate.block_height, ret_tx.block_height)
        self.assertEqual(self.tx_delegate.type, ret_tx.type)

        self.assertEqual(self.tx_delegate.data.delegation_info[0].address, ret_tx.data.delegation_info[0].address)
        self.assertEqual(self.tx_delegate.data.delegation_info[0].value, ret_tx.data.delegation_info[0].value)
        self.assertEqual(self.tx_delegate.data.delegation_info[1].address, ret_tx.data.delegation_info[1].address)
        self.assertEqual(self.tx_delegate.data.delegation_info[1].value, ret_tx.data.delegation_info[1].value)

    def test_iiss_tx_data_preb_reg_tx(self):
        data: bytes = self.tx_prep_reg.make_value()
        ret_tx: 'IissTxData' = self.tx_prep_reg.from_bytes(self.tx_prep_reg.index, data)

        self.assertEqual(self.tx_prep_reg.index, ret_tx.index)
        self.assertEqual(self.tx_prep_reg.address, ret_tx.address)
        self.assertEqual(self.tx_prep_reg.block_height, ret_tx.block_height)
        self.assertEqual(self.tx_prep_reg.type, ret_tx.type)

    def test_iiss_tx_data_preb_un_reg_tx(self):
        data: bytes = self.tx_prep_un_reg.make_value()
        ret_tx: 'IissTxData' = self.tx_prep_un_reg.from_bytes(self.tx_prep_un_reg.index, data)

        self.assertEqual(self.tx_prep_un_reg.index, ret_tx.index)
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
            print(f"icx_price: {self.iiss_gv.icx_price}")
            print(f"incentive_rep: {self.iiss_gv.incentive_rep}")
            print(f"reward_rep: {self.iiss_gv.reward_rep}")
            print(f"key: {key}")
            print(f"value: {value}")
            print("")

        key: bytes = self.iiss_prep.make_key()
        value: bytes = self.iiss_prep.make_value()
        self.db.put(key, value)

        if self.debug:
            print("===PREPS_DATA===")
            print(f"block_height: {self.iiss_prep.block_height}")
            print(f"block_block_generator: {self.iiss_prep.block_generator}")
            print(f"block_block_validator_list: {self.iiss_prep.block_validator_list}")
            print(f"key: {key}")
            print(f"value: {value}")
            print("")

        key: bytes = self.tx_delegate.make_key()
        value: bytes = self.tx_delegate.make_value()
        self.db.put(key, value)

        if self.debug:
            print("===IISS_TX_DATA-1===")
            print(f"index: {self.tx_delegate.index}")
            print(f"address: {self.tx_delegate.address}")
            print(f"block_height: {self.tx_delegate.block_height}")
            print(f"type: {self.tx_delegate.type}")
            print(f"ori_delegate: {[(str(x.address), x.value) for x in self.tx_delegate.data.delegation_info]}")
            print(f"delegate: {self.tx_delegate.data.encode()}")
            print(f"key: {key}")
            print(f"value: {value}")
            print("")

        key: bytes = self.tx_prep_reg.make_key()
        value: bytes = self.tx_prep_reg.make_value()
        self.db.put(key, value)

        if self.debug:
            print("===IISS_TX_DATA-2===")
            print(f"index: {self.tx_prep_reg.index}")
            print(f"address: {self.tx_prep_reg.address}")
            print(f"block_height: {self.tx_prep_reg.block_height}")
            print(f"type: {self.tx_prep_reg.type}")
            print(f"data: {self.tx_prep_reg.data.encode()}")
            print(f"key: {key}")
            print(f"value: {value}")
            print("")

        key: bytes = self.tx_prep_un_reg.make_key()
        value: bytes = self.tx_prep_un_reg.make_value()
        self.db.put(key, value)

        if self.debug:
            print("===IISS_TX_DATA-3===")
            print(f"index: {self.tx_prep_un_reg.index}")
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
        ret_h: 'IissHeader' = self.iiss_header.from_bytes(value)

        self.assertEqual(self.iiss_header.version, ret_h.version)
        self.assertEqual(self.iiss_header.block_height, ret_h.block_height)

        key: bytes = self.iiss_gv.make_key()
        value = self.db.get(key)
        ret_gv: 'IissGovernanceVariable' = self.iiss_gv.from_bytes(key, value)

        self.assertEqual(self.iiss_gv.block_height, self.iiss_gv.block_height)
        self.assertEqual(self.iiss_gv.icx_price, ret_gv.icx_price)
        self.assertEqual(self.iiss_gv.incentive_rep, ret_gv.incentive_rep)
        self.assertEqual(self.iiss_gv.reward_rep, ret_gv.reward_rep)

        key: bytes = self.iiss_prep.make_key()
        value = self.db.get(key)
        ret_p: 'PrepsData' = self.iiss_prep.from_bytes(key, value)

        self.assertEqual(self.iiss_prep.block_height, ret_p.block_height)
        self.assertEqual(self.iiss_prep.block_generator, ret_p.block_generator)
        self.assertEqual(self.iiss_prep.block_validator_list, ret_p.block_validator_list)

        key: bytes = self.tx_delegate.make_key()
        value = self.db.get(key)
        ret_tx: 'IissTxData' = self.tx_delegate.from_bytes(self.tx_delegate.index, value)

        self.assertEqual(self.tx_delegate.index, ret_tx.index)
        self.assertEqual(self.tx_delegate.address, ret_tx.address)
        self.assertEqual(self.tx_delegate.block_height, ret_tx.block_height)
        self.assertEqual(self.tx_delegate.type, ret_tx.type)

        self.assertEqual(self.tx_delegate.data.delegation_info[0].address, ret_tx.data.delegation_info[0].address)
        self.assertEqual(self.tx_delegate.data.delegation_info[0].value, ret_tx.data.delegation_info[0].value)
        self.assertEqual(self.tx_delegate.data.delegation_info[1].address, ret_tx.data.delegation_info[1].address)
        self.assertEqual(self.tx_delegate.data.delegation_info[1].value, ret_tx.data.delegation_info[1].value)

        key: bytes = self.tx_prep_reg.make_key()
        value = self.db.get(key)
        ret_tx: 'IissTxData' = self.tx_prep_reg.from_bytes(self.tx_prep_reg.index, value)

        self.assertEqual(self.tx_prep_reg.index, ret_tx.index)
        self.assertEqual(self.tx_prep_reg.address, ret_tx.address)
        self.assertEqual(self.tx_prep_reg.block_height, ret_tx.block_height)
        self.assertEqual(self.tx_prep_reg.type, ret_tx.type)

        key: bytes = self.tx_prep_un_reg.make_key()
        value = self.db.get(key)
        ret_tx: 'IissTxData' = self.tx_prep_un_reg.from_bytes(self.tx_prep_un_reg.index, value)

        self.assertEqual(self.tx_prep_un_reg.index, ret_tx.index)
        self.assertEqual(self.tx_prep_un_reg.address, ret_tx.address)
        self.assertEqual(self.tx_prep_un_reg.block_height, ret_tx.block_height)
        self.assertEqual(self.tx_prep_un_reg.type, ret_tx.type)


if __name__ == '__main__':
    unittest.main()
