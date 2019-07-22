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

"""IconScoreEngine testcase
"""
import hashlib
import os
from copy import deepcopy

from iconservice.base.address import Address
from iconservice.base.exception import InvalidParamsException, ExceptionCode
from iconservice.base.type_converter_templates import ConstantKeys
from iconservice.icon_constant import IISS_INITIAL_IREP, PRepGrade, PRepStatus
from iconservice.icon_constant import REV_IISS, PREP_MAIN_PREPS, ConfigKey, IISS_MAX_DELEGATIONS, ICX_IN_LOOP
from tests.integrate_test.iiss.test_iiss_base import TestIISSBase

name = "prep"

prep_register_data = {
    ConstantKeys.NAME: name,
    ConstantKeys.EMAIL: f"{name}@example.com",
    ConstantKeys.WEBSITE: f"https://{name}.example.com",
    ConstantKeys.DETAILS: f"https://{name}.example.com/details",
    ConstantKeys.P2P_ENDPOINT: f"{name}.example.com:7100",
    ConstantKeys.PUBLIC_KEY: "0x12",
    ConstantKeys.CITY: "city",
    ConstantKeys.COUNTRY: "country"
}


class TestIntegratePrep(TestIISSBase):
    def _make_init_config(self) -> dict:
        config: dict = super()._make_init_config()
        config[ConfigKey.PREP_REGISTRATION_FEE] = 0
        return config

    def test_preps(self):
        self.update_governance()

        # set Revision REV_IISS
        tx: dict = self.create_set_revision_tx(REV_IISS)
        prev_block, tx_results = self._make_and_req_block([tx])
        self.assertEqual(int(True), tx_results[0].status)
        self._write_precommit_state(prev_block)

        # distribute icx for register PREP_MAIN_PREPS ~ PREP_MAIN_PREPS + PREP_MAIN_PREPS - 1
        tx_list: list = []
        for i in range(PREP_MAIN_PREPS):
            tx: dict = self._make_icx_send_tx(self._genesis,
                                              self._addr_array[i],
                                              3000 * ICX_IN_LOOP)
            tx_list.append(tx)
        prev_block, tx_results = self._make_and_req_block(tx_list)
        for tx_result in tx_results:
            self.assertEqual(int(True), tx_result.status)
        self._write_precommit_state(prev_block)

        # register prep 0 ~ PREP_MAIN_PREPS - 1
        tx_list: list = []
        for i in range(PREP_MAIN_PREPS):
            tx: dict = self.create_register_prep_tx(self._addr_array[i],
                                                    public_key=f"0x{self.public_key_array[i].hex()}")
            tx_list.append(tx)
        prev_block, tx_results = self._make_and_req_block(tx_list)
        for tx_result in tx_results:
            self.assertEqual(int(True), tx_result.status)
        self._write_precommit_state(prev_block)

        # get prep 0 ~ PREP_MAIN_PREPS
        register_block_height: int = self._block_height
        for i in range(PREP_MAIN_PREPS):
            response: dict = self.get_prep(self._addr_array[i])
            expected_params: dict = self.create_register_prep_params(self._addr_array[i],
                                                                     f"0x{self.public_key_array[i].hex()}")
            self.assertEqual(0, response["delegated"])
            self.assertEqual(0, response["stake"])
            self.assertEqual(self._config[ConfigKey.INITIAL_IREP], response["irep"])
            self.assertEqual(register_block_height, response["irepUpdateBlockHeight"])
            self.assertEqual(bytes.fromhex(expected_params['publicKey'][2:]), response["publicKey"])
            for key in ("details", "email", "name", "country", "city", "p2pEndpoint", "website"):
                self.assertEqual(expected_params[key], response[key])
            self.assertEqual(0, response["totalBlocks"])
            self.assertEqual(0, response["validatedBlocks"])
            self.assertEqual(PRepStatus.ACTIVE.value, response["status"])
            self.assertEqual(PRepGrade.CANDIDATE.value, response["grade"])

        # set prep 0 ~ PREP_MAIN_PREPS - 1
        tx_list: list = []
        for i in range(PREP_MAIN_PREPS):
            tx: dict = self.create_set_prep_tx(self._addr_array[i], {"name": f"new{str(self._addr_array[i])}"})
            tx_list.append(tx)
        prev_block, tx_results = self._make_and_req_block(tx_list)
        for tx_result in tx_results:
            self.assertEqual(int(True), tx_result.status)
        self._write_precommit_state(prev_block)

        # get prep 0 ~ PREP_MAIN_PREPS
        for i in range(PREP_MAIN_PREPS):
            response: dict = self.get_prep(self._addr_array[i])
            expected_params: dict = self.create_register_prep_params(self._addr_array[i],
                                                                     public_key=f"0x{self.public_key_array[i].hex()}")
            expected_response: dict = {
                "delegated": 0,
                "stake": 0,
                "details": expected_params["details"],
                "email": expected_params["email"],
                "irep": self._config[ConfigKey.INITIAL_IREP],
                "irepUpdateBlockHeight": register_block_height,
                "name": f"new{str(self._addr_array[i])}",
                "country": expected_params["country"],
                "city": expected_params["city"],
                "p2pEndpoint": expected_params['p2pEndpoint'],
                "publicKey": bytes.fromhex(expected_params['publicKey'][2:]),
                "website": expected_params['website'],
                "totalBlocks": 0,
                "validatedBlocks": 0,
                "status": PRepStatus.ACTIVE.value,
                "grade": PRepGrade.CANDIDATE.value
            }
            self.assertEqual(expected_response, response)

        # unregister prep 0 ~ PREP_MAIN_PREPS - 1
        tx_list: list = []
        for i in range(PREP_MAIN_PREPS):
            tx: dict = self.create_unregister_prep_tx(self._addr_array[i])
            tx_list.append(tx)
        prev_block, tx_results = self._make_and_req_block(tx_list)
        for tx_result in tx_results:
            self.assertEqual(int(True), tx_result.status)
        self._write_precommit_state(prev_block)

        response: dict = self.get_prep_list()
        expected_response: dict = {
            "blockHeight": prev_block.height,
            "startRanking": 0,
            "totalDelegated": 0,
            "totalStake": 0,
            "preps": []
        }
        self.assertEqual(expected_response, response)

    def test_get_prep_list(self):
        self.update_governance()

        # set Revision REV_IISS
        tx: dict = self.create_set_revision_tx(REV_IISS)
        prev_block, tx_results = self._make_and_req_block([tx])
        self.assertEqual(int(True), tx_results[0].status)
        self._write_precommit_state(prev_block)

        prep_count: int = 3000
        public_key_list: list = [os.urandom(32) for _ in range(prep_count)]
        address_list = [Address.from_bytes(hashlib.sha3_256(public_key[1:]).digest()[-20:])
                        for public_key in public_key_list]

        # distribute icx for register PREP_MAIN_PREPS ~ PREP_MAIN_PREPS + PREP_MAIN_PREPS - 1
        tx_list: list = []
        for i in range(prep_count):
            tx: dict = self._make_icx_send_tx(self._genesis,
                                              address_list[i],
                                              3000 * ICX_IN_LOOP)
            tx_list.append(tx)
        prev_block, tx_results = self._make_and_req_block(tx_list)
        for tx_result in tx_results:
            self.assertEqual(int(True), tx_result.status)
        self._write_precommit_state(prev_block)

        # register prep
        tx_list: list = []
        for i in range(prep_count):
            tx: dict = self.create_register_prep_tx(address_list[i], public_key=f"0x{public_key_list[i].hex()}")
            tx_list.append(tx)
        prev_block, tx_results = self._make_and_req_block(tx_list)
        for tx_result in tx_results:
            self.assertEqual(int(True), tx_result.status)
        self._write_precommit_state(prev_block)

        with self.assertRaises(InvalidParamsException) as e:
            self.get_prep_list(start_index=-1)

        with self.assertRaises(InvalidParamsException) as e:
            self.get_prep_list(end_index=-1)

        with self.assertRaises(InvalidParamsException) as e:
            self.get_prep_list(0, 1)

        with self.assertRaises(InvalidParamsException) as e:
            self.get_prep_list(1, 0)

        with self.assertRaises(InvalidParamsException) as e:
                self.get_prep_list(2, 1)

        response: dict = self.get_prep_list(2, 2)
        actual_preps: list = response['preps']
        self.assertEqual(1, len(actual_preps))

        response: dict = self.get_prep_list(start_index=1)
        actual_preps: list = response['preps']
        self.assertEqual(prep_count, len(actual_preps))

    def test_preps_and_delegated(self):
        self.update_governance()

        # set Revision REV_IISS
        tx: dict = self.create_set_revision_tx(REV_IISS)
        prev_block, tx_results = self._make_and_req_block([tx])
        self.assertEqual(int(True), tx_results[0].status)
        self._write_precommit_state(prev_block)

        # distribute icx for register PREP_MAIN_PREPS ~ PREP_MAIN_PREPS + PREP_MAIN_PREPS - 1
        tx_list: list = []
        for i in range(PREP_MAIN_PREPS):
            tx: dict = self._make_icx_send_tx(self._genesis,
                                              self._addr_array[i],
                                              3000 * ICX_IN_LOOP)
            tx_list.append(tx)
        prev_block, tx_results = self._make_and_req_block(tx_list)
        for tx_result in tx_results:
            self.assertEqual(int(True), tx_result.status)
        self._write_precommit_state(prev_block)

        # register prep 0 ~ PREP_MAIN_PREPS - 1
        tx_list: list = []
        for i in range(PREP_MAIN_PREPS):
            tx: dict = self.create_register_prep_tx(self._addr_array[i],
                                                    public_key=f"0x{self.public_key_array[i].hex()}")
            tx_list.append(tx)
        prev_block, tx_results = self._make_and_req_block(tx_list)
        for tx_result in tx_results:
            self.assertEqual(int(True), tx_result.status)
        self._write_precommit_state(prev_block)

        # gain 10 icx user0
        balance: int = 100 * ICX_IN_LOOP
        tx = self._make_icx_send_tx(self._genesis, self._addr_array[0], balance)
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)

        # stake 10 icx user0
        stake_amount: int = 10 * ICX_IN_LOOP
        tx: dict = self.create_set_stake_tx(self._addr_array[0], stake_amount)
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)

        # delegation 1 icx user0 ~ 9
        delegations: list = []
        delegation_amount: int = 1 * ICX_IN_LOOP
        for i in range(IISS_MAX_DELEGATIONS):
            delegations.append((self._addr_array[i], delegation_amount))
        tx: dict = self.create_set_delegation_tx(self._addr_array[0], delegations)
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)

        response: dict = self.get_main_prep_list()
        actual_list: list = response["preps"]
        self.assertEqual(0, len(actual_list))

        response: dict = self.get_sub_prep_list()
        actual_list: list = response["preps"]
        self.assertEqual(0, len(actual_list))

        response: dict = self.get_prep_list(end_index=IISS_MAX_DELEGATIONS)
        preps: list = []
        for i in range(IISS_MAX_DELEGATIONS):
            address: 'Address' = self._addr_array[i]
            preps.append(
                {
                    "status": 0,
                    "grade": PRepGrade.CANDIDATE.value,
                    "country": "ZZZ",
                    "city": "Unknown",
                    "address": address,
                    "delegated": delegation_amount,
                    "name": f"node{address}",
                    "totalBlocks": 0,
                    "validatedBlocks": 0
                }
            )
        expected_response: dict = \
            {
                "blockHeight": prev_block.height,
                "startRanking": 1,
                "totalDelegated": stake_amount,
                "totalStake": stake_amount,
                "preps": preps,
            }
        self.assertEqual(expected_response, response)

    # TODO
    def test_prep_fail1(self):
        pass

    def test_set_governance_variables_failure(self):
        """setGovernanceVariable request causes MethodNotFound exception under prevoting revision

        :return:
        """
        self.update_governance()

        prep_address: 'Address' = self._addr_array[0]

        # set Revision REV_IISS
        tx: dict = self.create_set_revision_tx(REV_IISS)
        prev_block, tx_results = self._make_and_req_block([tx])
        self.assertEqual(int(True), tx_results[0].status)
        self._write_precommit_state(prev_block)

        # distribute icx for prep
        tx: dict = self._make_icx_send_tx(self._genesis,
                                          prep_address,
                                          3000 * ICX_IN_LOOP)
        prev_block, tx_results = self._make_and_req_block([tx])
        self.assertEqual(int(True), tx_results[0].status)
        self._write_precommit_state(prev_block)

        tx: dict = self.create_register_prep_tx(prep_address, public_key=f"0x{self.public_key_array[0].hex()}")
        prev_block, tx_results = self._make_and_req_block([tx])
        self.assertEqual(int(True), tx_results[0].status)
        self._write_precommit_state(prev_block)

        # get prep
        response = self.get_prep(prep_address)
        self.assertEqual(IISS_INITIAL_IREP, response[ConstantKeys.IREP])

        irep: int = response[ConstantKeys.IREP]

        # setGovernanceVariables call should be failed until IISS decentralization feature is enabled
        tx: dict = self.create_set_governance_variables(prep_address, irep + 10)
        prev_block, tx_results = self._make_and_req_block([tx])

        tx_result = tx_results[0]
        self.assertEqual(int(False), tx_result.status)
        self.assertEqual(ExceptionCode.METHOD_NOT_FOUND, tx_result.failure.code)

    def test_reg_prep_validator(self):
        self.update_governance()

        # set Revision REV_IISS
        tx: dict = self.create_set_revision_tx(REV_IISS)
        prev_block, tx_results = self._make_and_req_block([tx])
        self.assertEqual(int(True), tx_results[0].status)
        self._write_precommit_state(prev_block)

        # gain 10 icx user0
        balance: int = ICX_IN_LOOP
        tx_list = []
        for i in range(8):
            tx = self._make_icx_send_tx(self._genesis, self._addr_array[i], balance)
            tx_list.append(tx)
        prev_block, tx_results = self._make_and_req_block(tx_list)
        self._write_precommit_state(prev_block)

        self._validate_name()
        self._validate_email()
        self._validate_website()
        self._validate_country()
        self._validate_city()
        self._validate_details()
        self._validate_p2p_endpoint()
        self._validate_public_key()

    def _validate_name(self):
        reg_data: dict = deepcopy(prep_register_data)
        reg_data[ConstantKeys.NAME] = ''
        reg_data[ConstantKeys.PUBLIC_KEY] = f"0x{self.public_key_array[0].hex()}"
        tx = self.create_register_prep_tx(self._addr_array[0], reg_data)
        prev_block, tx_results = self._make_and_req_block([tx])
        tx_result = tx_results[0]
        self.assertFalse(tx_result.status)

        reg_data[ConstantKeys.NAME] = "valid name"
        reg_data[ConstantKeys.PUBLIC_KEY] = f"0x{self.public_key_array[0].hex()}"
        tx = self.create_register_prep_tx(self._addr_array[0], reg_data)
        prev_block, tx_results = self._make_and_req_block([tx])
        tx_result = tx_results[0]
        self.assertTrue(tx_result.status)

    def _validate_email(self):
        invalid_email_list = ['', 'invalid email', 'invalid.com', 'invalid@', 'invalid@a', 'invalid@a.',
                              'invalid@.com']

        for email in invalid_email_list:
            reg_data: dict = deepcopy(prep_register_data)
            reg_data[ConstantKeys.EMAIL] = email
            reg_data[ConstantKeys.PUBLIC_KEY] = f"0x{self.public_key_array[1].hex()}"
            tx = self.create_register_prep_tx(self._addr_array[1], reg_data)
            prev_block, tx_results = self._make_and_req_block([tx])
            tx_result = tx_results[0]
            self.assertFalse(tx_result.status)

        reg_data: dict = deepcopy(prep_register_data)
        reg_data[ConstantKeys.EMAIL] = "valid@validexample.com"
        reg_data[ConstantKeys.PUBLIC_KEY] = f"0x{self.public_key_array[1].hex()}"
        tx = self.create_register_prep_tx(self._addr_array[1], reg_data)
        prev_block, tx_results = self._make_and_req_block([tx])
        tx_result = tx_results[0]
        self.assertTrue(tx_result.status)

    def _validate_website(self):
        invalid_website_list = ['', 'invalid website', 'invalid.com', 'invalid_.com', 'c.com', 'http://c.com',
                                'https://c.com', 'ftp://caaa.com', "http://valid.", "https://valid."]

        for website in invalid_website_list:
            reg_data: dict = deepcopy(prep_register_data)
            reg_data[ConstantKeys.WEBSITE] = website
            reg_data[ConstantKeys.PUBLIC_KEY] = f"0x{self.public_key_array[2].hex()}"
            tx = self.create_register_prep_tx(self._addr_array[2], reg_data)
            prev_block, tx_results = self._make_and_req_block([tx])
            tx_result = tx_results[0]
            self.assertFalse(tx_result.status)

        reg_data: dict = deepcopy(prep_register_data)
        reg_data[ConstantKeys.WEBSITE] = "https://validurl.com"
        reg_data[ConstantKeys.PUBLIC_KEY] = f"0x{self.public_key_array[2].hex()}"
        tx = self.create_register_prep_tx(self._addr_array[2], reg_data)
        prev_block, tx_results = self._make_and_req_block([tx])
        tx_result = tx_results[0]
        self.assertTrue(tx_result.status)

    # TODO
    def _validate_country(self):
        pass

    # TODO
    def _validate_city(self):
        pass

    def _validate_details(self):
        invalid_website_list = ['', 'invalid website', 'invalid.com', 'invalid_.com', 'c.com', 'http://c.com',
                                'https://c.com', 'ftp://caaa.com', "http://valid.", "https://valid."]

        for website in invalid_website_list:
            reg_data: dict = deepcopy(prep_register_data)
            reg_data[ConstantKeys.WEBSITE] = website
            reg_data[ConstantKeys.PUBLIC_KEY] = f"0x{self.public_key_array[5].hex()}"
            tx = self.create_register_prep_tx(self._addr_array[5], reg_data)
            prev_block, tx_results = self._make_and_req_block([tx])
            tx_result = tx_results[0]
            self.assertFalse(tx_result.status)

        reg_data: dict = deepcopy(prep_register_data)
        reg_data[ConstantKeys.WEBSITE] = "https://validurl.com/json"
        reg_data[ConstantKeys.PUBLIC_KEY] = f"0x{self.public_key_array[5].hex()}"
        tx = self.create_register_prep_tx(self._addr_array[5], reg_data)
        prev_block, tx_results = self._make_and_req_block([tx])
        tx_result = tx_results[0]
        self.assertTrue(tx_result.status)

    def _validate_p2p_endpoint(self):
        invalid_website_list = ['', 'invalid website', 'invalid.com', 'invalid_.com', 'c.com', 'http://c.com',
                                'https://c.com', 'ftp://caaa.com', "http://valid.", "https://valid."
                                "https://target.asdf:7100"]

        for website in invalid_website_list:
            reg_data: dict = deepcopy(prep_register_data)
            reg_data[ConstantKeys.P2P_ENDPOINT] = website
            reg_data[ConstantKeys.PUBLIC_KEY] = f"0x{self.public_key_array[6].hex()}"
            tx = self.create_register_prep_tx(self._addr_array[6], reg_data)
            prev_block, tx_results = self._make_and_req_block([tx])
            tx_result = tx_results[0]
            self.assertFalse(tx_result.status)

        validate_endpoint = "20.20.7.8:8000"

        reg_data: dict = deepcopy(prep_register_data)
        reg_data[ConstantKeys.P2P_ENDPOINT] = validate_endpoint
        reg_data[ConstantKeys.PUBLIC_KEY] = f"0x{self.public_key_array[6].hex()}"
        tx = self.create_register_prep_tx(self._addr_array[6], reg_data)
        prev_block, tx_results = self._make_and_req_block([tx])
        tx_result = tx_results[0]
        self.assertTrue(tx_result.status)

    def _validate_public_key(self):
        invalid_public_key_list = ['', f'0x{b"dummy".hex()}']

        for public_key in invalid_public_key_list:
            reg_data: dict = deepcopy(prep_register_data)
            reg_data[ConstantKeys.PUBLIC_KEY] = public_key
            tx = self.create_register_prep_tx(self._addr_array[7], reg_data)
            prev_block, tx_results = self._make_and_req_block([tx])
            tx_result = tx_results[0]
            self.assertFalse(tx_result.status)

        reg_data: dict = deepcopy(prep_register_data)
        reg_data[ConstantKeys.PUBLIC_KEY] = f"0x{self.public_key_array[6].hex()}"
        tx = self.create_register_prep_tx(self._addr_array[6], reg_data)
        prev_block, tx_results = self._make_and_req_block([tx])
        tx_result = tx_results[0]
        self.assertTrue(tx_result.status)
