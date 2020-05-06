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

from typing import TYPE_CHECKING, List

from iconservice import SYSTEM_SCORE_ADDRESS, Address
from tests.integrate_test.test_integrate_base import TestIntegrateBase

if TYPE_CHECKING:
    from iconservice.iconscore.icon_score_result import TransactionResult

ONE = "1"
ZERO = "0"
EMPTY_STR = ""
EMPTY_BYTE = bytes.hex(b"")
NUM1 = 1
NUM0 = 0
INT_VAL = hex(20)
STRING_VAL = "string value"
BYTE_VAL = bytes.hex(b"byte string")
ADDRESS_VAL = str(Address.from_string(f"hx{'abcd1234' * 5}"))
BOOL_VAL = hex(False)


class TestIntegrateMethodParamters(TestIntegrateBase):
    def _init_score(self, pre_validation_enabled: bool = True) -> "Address":
        tx = self.create_deploy_score_tx(
            score_root="sample_scores",
            score_name="sample_db_returns",
            from_=self._accounts[0],
            to_=SYSTEM_SCORE_ADDRESS,
            deploy_params={
                "value": str(self._accounts[1].address),
                "value1": str(self._accounts[1].address),
            },
            pre_validation_enabled=pre_validation_enabled,
        )

        tx_results: List["TransactionResult"] = self.process_confirm_block_tx([tx])
        return tx_results[0].score_address

    def _score_call(
        self,
        to_: "Address",
        func_name: str,
        params: dict,
        pre_validation_enabled: bool = True,
        expected_status: bool = True,
    ):
        tx = self.create_score_call_tx(
            self._accounts[0],
            to_,
            func_name,
            params,
            pre_validation_enabled=pre_validation_enabled,
        )
        self.process_confirm_block_tx([tx], expected_status=expected_status)

    def test_int_type_parameters_methods(self):
        score_address: "Address" = self._init_score()

        query_request = {
            "from": self._admin,
            "to": score_address,
            "dataType": "call",
            "data": {"method": "get_value1", "params": {}},
        }
        response = self._query(query_request)
        self.assertEqual(response, 0)  # original value: 0(int)

        # set value to '1' -> set 1
        self._score_call(
            to_=score_address,
            func_name="set_value1",
            params={"value": ONE},
            pre_validation_enabled=False,
        )

        # set value to '0' -> set 0
        self._score_call(
            to_=score_address,
            func_name="set_value1",
            params={"value": ZERO},
            pre_validation_enabled=False,
        )

        # set value to '' -> fail
        self._score_call(
            to_=score_address,
            func_name="set_value1",
            params={"value": EMPTY_STR},
            pre_validation_enabled=False,
            expected_status=False,
        )

        # set value to b'' -> fail
        self._score_call(
            to_=score_address,
            func_name="set_value1",
            params={"value": EMPTY_BYTE},
            pre_validation_enabled=False,
            expected_status=False,
        )

        # set value to None -> fail
        self._score_call(
            to_=score_address,
            func_name="set_value1",
            params={"value": None},
            pre_validation_enabled=False,
            expected_status=False,
        )

        # set value to 1 -> fail
        self._score_call(
            to_=score_address,
            func_name="set_value1",
            params={"value": NUM1},
            pre_validation_enabled=False,
            expected_status=False,
        )

        # set value to 0 -> fail
        self._score_call(
            to_=score_address,
            func_name="set_value1",
            params={"value": NUM0},
            pre_validation_enabled=False,
            expected_status=False,
        )

        # set value to '0x14' -> set 20
        self._score_call(
            to_=score_address,
            func_name="set_value1",
            params={"value": INT_VAL},
            pre_validation_enabled=False,
        )
        response = self._query(query_request)
        self.assertEqual(response, 20)

        # set value to 'string value'' -> fail
        self._score_call(
            to_=score_address,
            func_name="set_value1",
            params={"value": STRING_VAL},
            pre_validation_enabled=False,
            expected_status=False,
        )

        # set value to b'byte value' -> fail
        self._score_call(
            to_=score_address,
            func_name="set_value1",
            params={"value": BYTE_VAL},
            pre_validation_enabled=False,
            expected_status=False,
        )

        # set value to address value -> fail
        self._score_call(
            to_=score_address,
            func_name="set_value1",
            params={"value": ADDRESS_VAL},
            pre_validation_enabled=False,
            expected_status=False,
        )

        # set value to False -> 0
        self._score_call(
            to_=score_address,
            func_name="set_value1",
            params={"value": BOOL_VAL},
            pre_validation_enabled=False,
        )

        response = self._query(query_request)
        self.assertEqual(response, 0)

        # set value to 'a' -> fail
        self._score_call(
            to_=score_address,
            func_name="set_value1",
            params={"value": "a"},
            expected_status=False,
        )

        # set value to 'A' -> fail
        self._score_call(
            to_=score_address,
            func_name="set_value1",
            params={"value": "A"},
            expected_status=False,
        )

    def test_str_type_parameters_methods(self):
        score_address: "Address" = self._init_score(pre_validation_enabled=False)

        query_request = {
            "from": self._admin,
            "to": score_address,
            "dataType": "call",
            "data": {"method": "get_value2", "params": {}},
        }
        response = self._query(query_request)
        self.assertEqual(response, "")  # original value: 0(int)

        # set value to '1' -> set '1'
        self._score_call(
            to_=score_address,
            func_name="set_value2",
            params={"value": ONE},
            pre_validation_enabled=False,
        )
        response = self._query(query_request)
        self.assertEqual(response, ONE)

        # set value to '0' -> set '0'
        self._score_call(
            to_=score_address,
            func_name="set_value2",
            params={"value": ZERO},
            pre_validation_enabled=False,
        )
        response = self._query(query_request)
        self.assertEqual(response, ZERO)

        # set value to '' -> set ''
        self._score_call(
            to_=score_address,
            func_name="set_value2",
            params={"value": EMPTY_STR},
            pre_validation_enabled=False,
        )
        response = self._query(query_request)
        self.assertEqual(response, EMPTY_STR)

        # set value to b'' -> set ''
        self._score_call(
            to_=score_address,
            func_name="set_value2",
            params={"value": EMPTY_BYTE},
            pre_validation_enabled=False,
        )
        response = self._query(query_request)
        self.assertEqual(response, "")

        # set value to None -> fail
        self._score_call(
            to_=score_address,
            func_name="set_value2",
            params={"value": None},
            pre_validation_enabled=False,
            expected_status=False,
        )

        # set value to 1 -> fail
        self._score_call(
            to_=score_address,
            func_name="set_value2",
            params={"value": NUM1},
            pre_validation_enabled=False,
            expected_status=False,
        )

        # set value to 0 -> fail
        self._score_call(
            to_=score_address,
            func_name="set_value2",
            params={"value": NUM0},
            pre_validation_enabled=False,
            expected_status=False,
        )

        # set value to '0x14' -> '0x14'
        self._score_call(
            to_=score_address,
            func_name="set_value2",
            params={"value": INT_VAL},
            pre_validation_enabled=False,
        )
        response = self._query(query_request)
        self.assertEqual(response, hex(20))

        # set value to 'string value' -> 'string value'
        self._score_call(
            to_=score_address,
            func_name="set_value2",
            params={"value": STRING_VAL},
            pre_validation_enabled=False,
        )
        response = self._query(query_request)
        self.assertEqual(response, STRING_VAL)

        # set value to b'byte value' -> b'byte value'
        self._score_call(
            to_=score_address,
            func_name="set_value2",
            params={"value": BYTE_VAL},
            pre_validation_enabled=False,
        )
        response = self._query(query_request)
        self.assertEqual(response, BYTE_VAL)

        # set value to address value -> address string
        self._score_call(
            to_=score_address,
            func_name="set_value2",
            params={"value": ADDRESS_VAL},
            pre_validation_enabled=False,
        )
        response = self._query(query_request)
        self.assertEqual(response, ADDRESS_VAL)

        # set value to False -> '0x0'
        self._score_call(
            to_=score_address,
            func_name="set_value2",
            params={"value": BOOL_VAL},
            pre_validation_enabled=False,
        )
        response = self._query(query_request)
        self.assertEqual(response, hex(False))

    def test_byte_type_parameters_methods(self):
        score_address: "Address" = self._init_score(pre_validation_enabled=False)

        query_request = {
            "from": self._admin,
            "to": score_address,
            "dataType": "call",
            "data": {"method": "get_value3", "params": {}},
        }
        response = self._query(query_request)
        self.assertEqual(response, None)  # original value: 0(int)

        # set value to '1' -> fail
        self._score_call(
            to_=score_address,
            func_name="set_value3",
            params={"value": ONE},
            pre_validation_enabled=False,
            expected_status=False,
        )

        # set value to '0' -> fail
        self._score_call(
            to_=score_address,
            func_name="set_value3",
            params={"value": ZERO},
            pre_validation_enabled=False,
            expected_status=False,
        )

        # set value to '' fail -> None
        self._score_call(
            to_=score_address,
            func_name="set_value3",
            params={"value": EMPTY_STR},
            pre_validation_enabled=False,
        )
        response = self._query(query_request)
        self.assertEqual(response, None)

        # set value to b'' -> None
        self._score_call(
            to_=score_address,
            func_name="set_value3",
            params={"value": EMPTY_BYTE},
            pre_validation_enabled=False,
        )
        response = self._query(query_request)
        self.assertEqual(response, None)

        # set value to None -> fail
        self._score_call(
            to_=score_address,
            func_name="set_value3",
            params={"value": None},
            pre_validation_enabled=False,
            expected_status=False,
        )

        # set value to 1 -> fail
        self._score_call(
            to_=score_address,
            func_name="set_value3",
            params={"value": NUM1},
            pre_validation_enabled=False,
            expected_status=False,
        )

        # set value to 0 -> fail
        self._score_call(
            to_=score_address,
            func_name="set_value3",
            params={"value": NUM0},
            pre_validation_enabled=False,
            expected_status=False,
        )

        # set value to '0x14' -> b'\x14'
        self._score_call(
            to_=score_address,
            func_name="set_value3",
            params={"value": INT_VAL},
            pre_validation_enabled=False,
        )
        response = self._query(query_request)
        self.assertEqual(response, bytes.fromhex("14"))

        # set value to 'string value' -> fail
        self._score_call(
            to_=score_address,
            func_name="set_value3",
            params={"value": STRING_VAL},
            pre_validation_enabled=False,
            expected_status=False,
        )

        # set value to b'byte value' -> byte value
        self._score_call(
            to_=score_address,
            func_name="set_value3",
            params={"value": BYTE_VAL},
            pre_validation_enabled=False,
        )
        response = self._query(query_request)
        self.assertEqual(response, int.to_bytes(int(BYTE_VAL, 16), 11, "big"))

        # set value to address value -> fail
        self._score_call(
            to_=score_address,
            func_name="set_value3",
            params={"value": ADDRESS_VAL},
            pre_validation_enabled=False,
            expected_status=False,
        )

        # set value to False -> fail
        self._score_call(
            to_=score_address,
            func_name="set_value3",
            params={"value": BOOL_VAL},
            pre_validation_enabled=False,
            expected_status=False,
        )

    def test_address_type_parameters_methods(self):
        score_address: "Address" = self._init_score()

        query_request = {
            "from": self._admin,
            "to": score_address,
            "dataType": "call",
            "data": {"method": "get_value4", "params": {}},
        }
        response = self._query(query_request)
        self.assertEqual(response, self._accounts[1].address)  # original value: 0(int)

        # set value to '1' -> fail
        self._score_call(
            to_=score_address,
            func_name="set_value4",
            params={"value": ONE},
            pre_validation_enabled=False,
            expected_status=False,
        )

        # set value to '0' -> fail
        self._score_call(
            to_=score_address,
            func_name="set_value4",
            params={"value": ZERO},
            pre_validation_enabled=False,
            expected_status=False,
        )

        # set value to '' fail
        self._score_call(
            to_=score_address,
            func_name="set_value4",
            params={"value": EMPTY_STR},
            pre_validation_enabled=False,
            expected_status=False,
        )

        # set value to b'' fail
        self._score_call(
            to_=score_address,
            func_name="set_value4",
            params={"value": EMPTY_BYTE},
            pre_validation_enabled=False,
            expected_status=False,
        )

        # set value to None -> fail
        self._score_call(
            to_=score_address,
            func_name="set_value4",
            params={"value": None},
            pre_validation_enabled=False,
            expected_status=False,
        )

        # set value to 1 -> fail
        self._score_call(
            to_=score_address,
            func_name="set_value4",
            params={"value": NUM1},
            pre_validation_enabled=False,
            expected_status=False,
        )

        # set value to 0 -> fail
        self._score_call(
            to_=score_address,
            func_name="set_value4",
            params={"value": NUM0},
            pre_validation_enabled=False,
            expected_status=False,
        )

        # set value to '0x14'
        self._score_call(
            to_=score_address,
            func_name="set_value4",
            params={"value": INT_VAL},
            pre_validation_enabled=False,
            expected_status=False,
        )

        # set value to 'string value''
        self._score_call(
            to_=score_address,
            func_name="set_value4",
            params={"value": STRING_VAL},
            pre_validation_enabled=False,
            expected_status=False,
        )

        # set value to b'byte value'
        self._score_call(
            to_=score_address,
            func_name="set_value4",
            params={"value": BYTE_VAL},
            pre_validation_enabled=False,
            expected_status=False,
        )

        # set value to address value
        self._score_call(
            to_=score_address,
            func_name="set_value4",
            params={"value": ADDRESS_VAL},
            pre_validation_enabled=False,
        )
        response = self._query(query_request)
        self.assertEqual(response, Address.from_string(ADDRESS_VAL))

        # set value to False
        self._score_call(
            to_=score_address,
            func_name="set_value4",
            params={"value": BOOL_VAL},
            pre_validation_enabled=False,
            expected_status=False,
        )

    def test_bool_type_parameters_methods(self):
        score_address: "Address" = self._init_score()

        query_request = {
            "from": self._admin,
            "to": score_address,
            "dataType": "call",
            "data": {"method": "get_value5", "params": {}},
        }
        response = self._query(query_request)
        self.assertEqual(response, False)  # original value: 0(int)

        # set value to '1' -> True
        self._score_call(
            to_=score_address,
            func_name="set_value5",
            params={"value": ONE},
            pre_validation_enabled=False,
        )
        response = self._query(query_request)
        self.assertEqual(response, True)

        # set value to '0' -> False
        self._score_call(
            to_=score_address,
            func_name="set_value5",
            params={"value": ZERO},
            pre_validation_enabled=False,
        )
        response = self._query(query_request)
        self.assertEqual(response, False)

        # set value to '' -> fail
        self._score_call(
            to_=score_address,
            func_name="set_value5",
            params={"value": EMPTY_STR},
            pre_validation_enabled=False,
            expected_status=False,
        )

        # set value to b'' -> fail
        self._score_call(
            to_=score_address,
            func_name="set_value5",
            params={"value": EMPTY_BYTE},
            pre_validation_enabled=False,
            expected_status=False,
        )

        # set value to None -> fail
        self._score_call(
            to_=score_address,
            func_name="set_value5",
            params={"value": None},
            pre_validation_enabled=False,
            expected_status=False,
        )

        # set value to 1 -> fail
        self._score_call(
            to_=score_address,
            func_name="set_value5",
            params={"value": NUM1},
            pre_validation_enabled=False,
            expected_status=False,
        )

        # set value to 0 -> fail
        self._score_call(
            to_=score_address,
            func_name="set_value5",
            params={"value": NUM0},
            pre_validation_enabled=False,
            expected_status=False,
        )

        # set value to '0x14' -> True
        self._score_call(
            to_=score_address,
            func_name="set_value5",
            params={"value": INT_VAL},
            pre_validation_enabled=False,
        )
        response = self._query(query_request)
        self.assertEqual(response, True)

        # set value to 'string value' -> fail
        self._score_call(
            to_=score_address,
            func_name="set_value5",
            params={"value": STRING_VAL},
            pre_validation_enabled=False,
            expected_status=False,
        )

        # set value to b'byte value' -> fail
        self._score_call(
            to_=score_address,
            func_name="set_value5",
            params={"value": BYTE_VAL},
            pre_validation_enabled=False,
            expected_status=False,
        )

        # set value to address value -> fail
        self._score_call(
            to_=score_address,
            func_name="set_value5",
            params={"value": ADDRESS_VAL},
            pre_validation_enabled=False,
            expected_status=False,
        )

        # set value to False -> False
        self._score_call(
            to_=score_address,
            func_name="set_value5",
            params={"value": BOOL_VAL},
            pre_validation_enabled=False,
        )
        response = self._query(query_request)
        self.assertEqual(response, False)
