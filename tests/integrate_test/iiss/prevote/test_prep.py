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
from iconservice.base.address import Address
from iconservice.base.exception import InvalidParamsException, ExceptionCode
from iconservice.base.type_converter_templates import ConstantKeys
from iconservice.icon_constant import IISS_INITIAL_IREP
from iconservice.icon_constant import REV_IISS, PREP_MAIN_PREPS, ConfigKey, IISS_MAX_DELEGATIONS, ICX_IN_LOOP
from tests import create_address
from tests.integrate_test.iiss.test_iiss_base import TestIISSBase


class TestIntegratePrep(TestIISSBase):

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
            tx: dict = self.create_register_prep_tx(self._addr_array[i])
            tx_list.append(tx)
        prev_block, tx_results = self._make_and_req_block(tx_list)
        for tx_result in tx_results:
            self.assertEqual(int(True), tx_result.status)
        self._write_precommit_state(prev_block)

        # get prep 0 ~ PREP_MAIN_PREPS
        register_block_height: int = self._block_height
        for i in range(PREP_MAIN_PREPS):
            response: dict = self.get_prep(self._addr_array[i])
            expected_params: dict = self.create_register_prep_params(self._addr_array[i])
            expected_response: dict = \
                {
                    "delegation":
                        {
                            "delegated": 0,
                            "stake": 0
                        },
                    "registration":
                        {
                            "details": expected_params["details"],
                            "email": expected_params["email"],
                            "irep": self._config[ConfigKey.INITIAL_IREP],
                            "irepUpdateBlockHeight": register_block_height,
                            "name": expected_params['name'],
                            "p2pEndPoint": expected_params['p2pEndPoint'],
                            "publicKey": bytes.fromhex(expected_params['publicKey']),
                            "website": expected_params['website']
                        },
                    "stats":
                        {
                            "totalBlocks": 0,
                            "validatedBlocks": 0
                        },
                    "status": 0
                }
            self.assertEqual(expected_response, response)

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
            expected_params: dict = self.create_register_prep_params(self._addr_array[i])
            expected_response: dict = \
                {
                    "delegation":
                        {
                            "delegated": 0,
                            "stake": 0
                        },
                    "registration":
                        {
                            "details": expected_params["details"],
                            "email": expected_params["email"],
                            "irep": self._config[ConfigKey.INITIAL_IREP],
                            "irepUpdateBlockHeight": register_block_height,
                            "name": f"new{str(self._addr_array[i])}",
                            "p2pEndPoint": expected_params['p2pEndPoint'],
                            "publicKey": bytes.fromhex(expected_params['publicKey']),
                            "website": expected_params['website']
                        },
                    "stats":
                        {
                            "totalBlocks": 0,
                            "validatedBlocks": 0
                        },
                    "status": 0
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
        expected_response: dict = \
            {
                "startRanking": 0,
                "totalDelegated": 0,
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
        address_list: list = [create_address() for _ in range(prep_count)]

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
            tx: dict = self.create_register_prep_tx(address_list[i])
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
            tx: dict = self.create_register_prep_tx(self._addr_array[i])
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
            preps.append(
                {
                    "address": self._addr_array[i],
                    "delegated": delegation_amount
                }
            )
        expected_response: dict = \
            {
                "preps": preps,
                "startRanking": 1,
                "totalDelegated": stake_amount
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

        tx: dict = self.create_register_prep_tx(prep_address)
        prev_block, tx_results = self._make_and_req_block([tx])
        self.assertEqual(int(True), tx_results[0].status)
        self._write_precommit_state(prev_block)

        response = self.get_prep(prep_address)

        registration = response["registration"]
        self.assertEqual(IISS_INITIAL_IREP, registration[ConstantKeys.IREP])

        # setGovernanceVariables call should be failed until IISS decentralization feature is enabled
        irep: int = registration[ConstantKeys.IREP]

        tx: dict = self.create_set_governance_variables(prep_address, irep + 10)
        prev_block, tx_results = self._make_and_req_block([tx])

        tx_result = tx_results[0]
        self.assertEqual(int(False), tx_result.status)
        self.assertEqual(ExceptionCode.METHOD_NOT_FOUND, tx_result.failure.code)
