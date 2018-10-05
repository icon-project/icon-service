# -*- coding: utf-8 -*-

# Copyright 2018 ICON Foundation
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


from iconservice import ZERO_SCORE_ADDRESS, Address
from tests.integrate_test.test_integrate_base import TestIntegrateBase

ONE = '1'
ZERO = '0'
EMPTY_STR = ""
EMPTY_BYTE = bytes.hex(b"")
NUM1 = 1
NUM0 = 0
INT_VAL = '0x14'
STRING_VAL = 'string value'
BYTE_VAL = bytes.hex(b'byte string')
ADDRESS_VAL = str(Address.from_string(f"hx{'abcd1234'*5}"))
BOOL_VAL = hex(False)

# 'asdf' '1' -> True, '2', int type에 'a'


class TestIntegrateMethodParamters(TestIntegrateBase):

    def test_int_type_parameters_methods(self):
        tx1 = self._make_deploy_tx("test_scores", "test_db_returns", self._addr_array[0], ZERO_SCORE_ADDRESS,
                                   deploy_params={"value": str(self._addr_array[1]),
                                                  "value1": str(self._addr_array[1])})

        prev_block, tx_results = self._make_and_req_block([tx1])

        self._write_precommit_state(prev_block)

        self.assertEqual(tx_results[0].status, int(True))
        score_addr1 = tx_results[0].score_address

        query_request = {
            "from": self._admin,
            "to": score_addr1,
            "dataType": "call",
            "data": {
                "method": "get_value1",
                "params": {}
            }
        }
        response = self._query(query_request)
        self.assertEqual(response, 0) # original value: 0(int)

        # set value to '1' -> set 1
        tx = self._make_score_call_tx(self._addr_array[0], score_addr1, 'set_value1', {"value": ONE})
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))

        # set value to '0' -> set 0
        tx = self._make_score_call_tx(self._addr_array[0], score_addr1, 'set_value1', {"value": ZERO})
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))

        # set value to '' -> fail
        tx = self._make_score_call_tx(self._addr_array[0], score_addr1, 'set_value1', {"value": EMPTY_STR})
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(False))

        # set value to b'' -> fail
        tx = self._make_score_call_tx(self._addr_array[0], score_addr1, 'set_value1', {"value": EMPTY_BYTE})
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(False))

        # set value to None -> fail
        tx = self._make_score_call_tx(self._addr_array[0], score_addr1, 'set_value1', {"value": None})
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(False))

        # set value to 1 -> fail
        tx = self._make_score_call_tx(self._addr_array[0], score_addr1, 'set_value1', {"value": NUM1})
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(False))

        # set value to 0 -> fail
        tx = self._make_score_call_tx(self._addr_array[0], score_addr1, 'set_value1', {"value": NUM0})
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(False))

        # set value to '0x14' -> set 20
        tx = self._make_score_call_tx(self._addr_array[0], score_addr1, 'set_value1', {"value": INT_VAL})
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))
        response = self._query(query_request)
        self.assertEqual(response, 20)

        # set value to 'string value'' -> fail
        tx = self._make_score_call_tx(self._addr_array[0], score_addr1, 'set_value1', {"value": STRING_VAL})
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(False))

        # set value to b'byte value' -> fail
        tx = self._make_score_call_tx(self._addr_array[0], score_addr1, 'set_value1', {"value": BYTE_VAL})
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(False))

        # set value to address value -> fail
        tx = self._make_score_call_tx(self._addr_array[0], score_addr1, 'set_value1', {"value": ADDRESS_VAL})
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(False))

        # set value to False -> 0
        tx = self._make_score_call_tx(self._addr_array[0], score_addr1, 'set_value1', {"value": BOOL_VAL})
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))
        response = self._query(query_request)
        self.assertEqual(response, 0)

        # set value to 'a' -> fail
        tx = self._make_score_call_tx(self._addr_array[0], score_addr1, 'set_value1', {"value": 'a'})
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(False))

        # set value to 'A' -> fail
        tx = self._make_score_call_tx(self._addr_array[0], score_addr1, 'set_value1', {"value": 'A'})
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(False))

    def test_str_type_parameters_methods(self):
        tx1 = self._make_deploy_tx("test_scores", "test_db_returns", self._addr_array[0], ZERO_SCORE_ADDRESS,
                                   deploy_params={"value": str(self._addr_array[1]),
                                                  "value1": str(self._addr_array[1])})

        prev_block, tx_results = self._make_and_req_block([tx1])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))
        score_addr1 = tx_results[0].score_address

        query_request = {
            "from": self._admin,
            "to": score_addr1,
            "dataType": "call",
            "data": {
                "method": "get_value2",
                "params": {}
            }
        }
        response = self._query(query_request)
        self.assertEqual(response, "") # original value: 0(int)

        # set value to '1' -> set '1'
        tx = self._make_score_call_tx(self._addr_array[0], score_addr1, 'set_value2', {"value": ONE})
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))
        response = self._query(query_request)
        self.assertEqual(response, ONE)

        # set value to '0' -> set '0'
        tx = self._make_score_call_tx(self._addr_array[0], score_addr1, 'set_value2', {"value": ZERO})
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))
        response = self._query(query_request)
        self.assertEqual(response, ZERO)

        # set value to '' -> set ''
        tx = self._make_score_call_tx(self._addr_array[0], score_addr1, 'set_value2', {"value": EMPTY_STR})
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))
        response = self._query(query_request)
        self.assertEqual(response, EMPTY_STR)

        # set value to b'' -> set ''
        tx = self._make_score_call_tx(self._addr_array[0], score_addr1, 'set_value2', {"value": EMPTY_BYTE})
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))
        response = self._query(query_request)
        self.assertEqual(response, '')

        # set value to None -> fail
        tx = self._make_score_call_tx(self._addr_array[0], score_addr1, 'set_value2', {"value": None})
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(False))

        # set value to 1 -> fail
        tx = self._make_score_call_tx(self._addr_array[0], score_addr1, 'set_value2', {"value": NUM1})
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(False))

        # set value to 0 -> fail
        tx = self._make_score_call_tx(self._addr_array[0], score_addr1, 'set_value2', {"value": NUM0})
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(False))

        # set value to '0x14' -> '0x14'
        tx = self._make_score_call_tx(self._addr_array[0], score_addr1, 'set_value2', {"value": INT_VAL})
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))
        response = self._query(query_request)
        self.assertEqual(response, '0x14')

        # set value to 'string value' -> 'string value'
        tx = self._make_score_call_tx(self._addr_array[0], score_addr1, 'set_value2', {"value": STRING_VAL})
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))
        response = self._query(query_request)
        self.assertEqual(response, STRING_VAL)

        # set value to b'byte value' -> b'byte value'
        tx = self._make_score_call_tx(self._addr_array[0], score_addr1, 'set_value2', {"value": BYTE_VAL})
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))
        response = self._query(query_request)
        self.assertEqual(response, BYTE_VAL)

        # set value to address value -> address string
        tx = self._make_score_call_tx(self._addr_array[0], score_addr1, 'set_value2', {"value": ADDRESS_VAL})
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))
        response = self._query(query_request)
        self.assertEqual(response, ADDRESS_VAL)

        # set value to False -> '0x0'
        tx = self._make_score_call_tx(self._addr_array[0], score_addr1, 'set_value2', {"value": BOOL_VAL})
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))
        response = self._query(query_request)
        self.assertEqual(response, hex(False))

    def test_byte_type_parameters_methods(self):
        tx1 = self._make_deploy_tx("test_scores", "test_db_returns", self._addr_array[0], ZERO_SCORE_ADDRESS,
                                   deploy_params={"value": str(self._addr_array[1]),
                                                  "value1": str(self._addr_array[1])})

        prev_block, tx_results = self._make_and_req_block([tx1])

        self._write_precommit_state(prev_block)

        self.assertEqual(tx_results[0].status, int(True))
        score_addr1 = tx_results[0].score_address

        query_request = {
            "from": self._admin,
            "to": score_addr1,
            "dataType": "call",
            "data": {
                "method": "get_value3",
                "params": {}
            }
        }
        response = self._query(query_request)
        self.assertEqual(response, None) # original value: 0(int)

        # set value to '1' -> fail
        tx = self._make_score_call_tx(self._addr_array[0], score_addr1, 'set_value3', {"value": ONE})
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(False))

        # set value to '0' -> fail
        tx = self._make_score_call_tx(self._addr_array[0], score_addr1, 'set_value3', {"value": ZERO})
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(False))

        # set value to '' fail -> None
        tx = self._make_score_call_tx(self._addr_array[0], score_addr1, 'set_value3', {"value": EMPTY_STR})
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))
        response = self._query(query_request)
        self.assertEqual(response, None)

        # set value to b'' -> None
        tx = self._make_score_call_tx(self._addr_array[0], score_addr1, 'set_value3', {"value": EMPTY_BYTE})
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))
        response = self._query(query_request)
        self.assertEqual(response, None)

        # set value to None -> fail
        tx = self._make_score_call_tx(self._addr_array[0], score_addr1, 'set_value3', {"value": None})
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(False))

        # set value to 1 -> fail
        tx = self._make_score_call_tx(self._addr_array[0], score_addr1, 'set_value3', {"value": NUM1})
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(False))

        # set value to 0 -> fail
        tx = self._make_score_call_tx(self._addr_array[0], score_addr1, 'set_value3', {"value": NUM0})
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(False))

        # set value to '0x14' -> b'\x14'
        tx = self._make_score_call_tx(self._addr_array[0], score_addr1, 'set_value3', {"value": INT_VAL})
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))
        response = self._query(query_request)
        self.assertEqual(response, bytes.fromhex('14'))

        # set value to 'string value' -> fail
        tx = self._make_score_call_tx(self._addr_array[0], score_addr1, 'set_value3', {"value": STRING_VAL})
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(False))

        # set value to b'byte value' -> byte value
        tx = self._make_score_call_tx(self._addr_array[0], score_addr1, 'set_value3', {"value": BYTE_VAL})
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))
        response = self._query(query_request)
        self.assertEqual(response, int.to_bytes(int(BYTE_VAL, 16), 11, 'big'))

        # set value to address value -> fail
        tx = self._make_score_call_tx(self._addr_array[0], score_addr1, 'set_value3', {"value": ADDRESS_VAL})
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(False))

        # set value to False -> fail
        tx = self._make_score_call_tx(self._addr_array[0], score_addr1, 'set_value3', {"value": BOOL_VAL})
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(False))

    def test_address_type_parameters_methods(self):

        tx1 = self._make_deploy_tx("test_scores", "test_db_returns", self._addr_array[0], ZERO_SCORE_ADDRESS,
                                   deploy_params={"value": str(self._addr_array[1]),
                                                  "value1": str(self._addr_array[1])})

        prev_block, tx_results = self._make_and_req_block([tx1])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))
        score_addr1 = tx_results[0].score_address
        query_request = {
            "from": self._admin,
            "to": score_addr1,
            "dataType": "call",
            "data": {
                "method": "get_value4",
                "params": {}
            }
        }
        response = self._query(query_request)
        self.assertEqual(response, self._addr_array[1]) # original value: 0(int)

        # set value to '1' -> fail
        tx = self._make_score_call_tx(self._addr_array[0], score_addr1, 'set_value4', {"value": ONE})
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(False))

        # set value to '0' -> fail
        tx = self._make_score_call_tx(self._addr_array[0], score_addr1, 'set_value4', {"value": ZERO})
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(False))

        # set value to '' fail
        tx = self._make_score_call_tx(self._addr_array[0], score_addr1, 'set_value4', {"value": EMPTY_STR})
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(False))

        # set value to b'' fail
        tx = self._make_score_call_tx(self._addr_array[0], score_addr1, 'set_value4', {"value": EMPTY_BYTE})
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(False))

        # set value to None -> fail

        tx = self._make_score_call_tx(self._addr_array[0], score_addr1, 'set_value4', {"value": None})
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(False))

        # set value to 1 -> fail
        tx = self._make_score_call_tx(self._addr_array[0], score_addr1, 'set_value4', {"value": NUM1})
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(False))

        # set value to 0 -> fail
        tx = self._make_score_call_tx(self._addr_array[0], score_addr1, 'set_value4', {"value": NUM0})
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(False))

        # set value to '0x14'
        tx = self._make_score_call_tx(self._addr_array[0], score_addr1, 'set_value4', {"value": INT_VAL})
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(False))

        # set value to 'string value''
        tx = self._make_score_call_tx(self._addr_array[0], score_addr1, 'set_value4', {"value": STRING_VAL})
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(False))

        # set value to b'byte value'
        tx = self._make_score_call_tx(self._addr_array[0], score_addr1, 'set_value4', {"value": BYTE_VAL})
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(False))

        # set value to address value
        tx = self._make_score_call_tx(self._addr_array[0], score_addr1, 'set_value4', {"value": ADDRESS_VAL})
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))
        response = self._query(query_request)
        self.assertEqual(response, Address.from_string(ADDRESS_VAL))

        # set value to False
        tx = self._make_score_call_tx(self._addr_array[0], score_addr1, 'set_value4', {"value": BOOL_VAL})
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(False))

    def test_bool_type_parameters_methods(self):

        tx1 = self._make_deploy_tx("test_scores", "test_db_returns", self._addr_array[0], ZERO_SCORE_ADDRESS,
                                   deploy_params={"value": str(self._addr_array[1]),
                                                  "value1": str(self._addr_array[1])})

        prev_block, tx_results = self._make_and_req_block([tx1])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))
        score_addr1 = tx_results[0].score_address
        query_request = {
            "from": self._admin,
            "to": score_addr1,
            "dataType": "call",
            "data": {
                "method": "get_value5",
                "params": {}
            }
        }
        response = self._query(query_request)
        self.assertEqual(response, False) # original value: 0(int)

        # set value to '1' -> True
        tx = self._make_score_call_tx(self._addr_array[0], score_addr1, 'set_value5', {"value": ONE})
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))
        response = self._query(query_request)
        self.assertEqual(response, True)

        # set value to '0' -> False
        tx = self._make_score_call_tx(self._addr_array[0], score_addr1, 'set_value5', {"value": ZERO})
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))
        response = self._query(query_request)
        self.assertEqual(response, False)

        # set value to '' -> fail
        tx = self._make_score_call_tx(self._addr_array[0], score_addr1, 'set_value5', {"value": EMPTY_STR})
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(False))

        # set value to b'' -> fail
        tx = self._make_score_call_tx(self._addr_array[0], score_addr1, 'set_value5', {"value": EMPTY_BYTE})
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(False))

        # set value to None -> fail
        tx = self._make_score_call_tx(self._addr_array[0], score_addr1, 'set_value5', {"value": None})
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(False))

        # set value to 1 -> fail
        tx = self._make_score_call_tx(self._addr_array[0], score_addr1, 'set_value5', {"value": NUM1})
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(False))

        # set value to 0 -> fail
        tx = self._make_score_call_tx(self._addr_array[0], score_addr1, 'set_value5', {"value": NUM0})
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(False))

        # set value to '0x14' -> True
        tx = self._make_score_call_tx(self._addr_array[0], score_addr1, 'set_value5', {"value": INT_VAL})
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))
        response = self._query(query_request)
        self.assertEqual(response, True)

        # set value to 'string value' -> fail
        tx = self._make_score_call_tx(self._addr_array[0], score_addr1, 'set_value5', {"value": STRING_VAL})
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(False))

        # set value to b'byte value' -> fail
        tx = self._make_score_call_tx(self._addr_array[0], score_addr1, 'set_value5', {"value": BYTE_VAL})
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(False))

        # set value to address value -> fail
        tx = self._make_score_call_tx(self._addr_array[0], score_addr1, 'set_value5', {"value": ADDRESS_VAL})
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(False))

        # set value to False -> False
        tx = self._make_score_call_tx(self._addr_array[0], score_addr1, 'set_value5', {"value": BOOL_VAL})
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))
        response = self._query(query_request)
        self.assertEqual(response, False)
