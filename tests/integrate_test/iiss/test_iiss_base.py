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
from typing import List, Tuple, Dict, Union, Optional

from iconservice.base.address import Address
from iconservice.base.address import ZERO_SCORE_ADDRESS, GOVERNANCE_SCORE_ADDRESS
from iconservice.base.type_converter_templates import ConstantKeys
from iconservice.icon_constant import ConfigKey, PREP_MAIN_AND_SUB_PREPS, REV_IISS, PREP_MAIN_PREPS, ICX_IN_LOOP, \
    REV_DECENTRALIZATION, IISS_INITIAL_IREP
from tests.integrate_test.test_integrate_base import TestIntegrateBase, TOTAL_SUPPLY


class TestIISSBase(TestIntegrateBase):
    CALCULATE_PERIOD = 10
    TERM_PERIOD = 10

    def setUp(self):
        super().setUp()
        self.public_key_array = [os.urandom(32) for _ in range(PREP_MAIN_AND_SUB_PREPS)]
        self._addr_array = [Address.from_bytes(hashlib.sha3_256(public_key[1:]).digest()[-20:])
                            for public_key in self.public_key_array]

    def _make_init_config(self) -> dict:
        return {
            ConfigKey.SERVICE: {
                ConfigKey.SERVICE_FEE: True
            },
            ConfigKey.IISS_CALCULATE_PERIOD: self.CALCULATE_PERIOD,
            ConfigKey.TERM_PERIOD: self.TERM_PERIOD}

    def make_blocks(self, to: int):
        block_height = self._block_height

        while to > block_height:
            tx = self._make_icx_send_tx(self._genesis, self._addr_array[0], 0)
            prev_block, tx_results = self._make_and_req_block([tx])
            self._write_precommit_state(prev_block)
            block_height = self._block_height

    def make_blocks_to_end_calculation(self) -> int:
        iiss_info: dict = self.get_iiss_info()
        next_calculation: int = iiss_info.get('nextCalculation', 0)

        self.make_blocks(to=next_calculation - 1)

        self.assertEqual(self._block_height, next_calculation - 1)

        return next_calculation - 1

    @staticmethod
    def _make_tx_for_estimating_step_from_origin_tx(tx: dict):
        tx = deepcopy(tx)
        tx["method"] = "debug_estimateStep"
        del tx["params"]["nonce"]
        del tx["params"]["stepLimit"]
        del tx["params"]["timestamp"]
        del tx["params"]["txHash"]
        del tx["params"]["signature"]
        return tx

    def estimate_step(self, tx: dict):
        converted_tx = self._make_tx_for_estimating_step_from_origin_tx(tx)
        return self.icon_service_engine.estimate_step(request=converted_tx)

    def update_governance(self):
        tx = self._make_deploy_tx("sample_builtin",
                                  "latest_version/governance",
                                  self._admin,
                                  GOVERNANCE_SCORE_ADDRESS)
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)

    def create_set_revision_tx(self,
                               revision: int) -> dict:
        return self._make_score_call_tx(self._admin,
                                        GOVERNANCE_SCORE_ADDRESS,
                                        'setRevision',
                                        {
                                            "code": hex(revision),
                                            "name": f"1.1.{revision}"
                                        })

    def create_set_stake_tx(self,
                            address: 'Address',
                            value: int):
        return self._make_score_call_tx(address,
                                        ZERO_SCORE_ADDRESS,
                                        'setStake',
                                        {
                                            "value": hex(value)
                                        })

    def create_set_delegation_tx(self,
                                 address: 'Address',
                                 origin_delegations: List[Tuple['Address', int]]):
        delegations: List[Dict[str, str]] = self.create_delegation_params(origin_delegations)
        return self._make_score_call_tx(address,
                                        ZERO_SCORE_ADDRESS,
                                        'setDelegation',
                                        {
                                            "delegations": delegations
                                        })

    @staticmethod
    def create_delegation_params(params: List[Tuple['Address', int]]) -> List[Dict[str, str]]:
        return [{"address": str(address), "value": hex(value)}
                for (address, value) in params
                if value > 0]

    def create_register_prep_tx(self,
                                address: 'Address',
                                reg_data: Dict[str, Union[str, bytes]] = None,
                                public_key: str = None,
                                value: int = 0):
        if reg_data is None:
            reg_data: dict = self.create_register_prep_params(address, public_key)

        return self._make_score_call_tx(address, ZERO_SCORE_ADDRESS, 'registerPRep', reg_data, value)

    @staticmethod
    def _create_dummy_public_key(data: bytes) -> bytes:
        return b"\x04" + hashlib.sha3_512(data).digest()

    def create_register_prep_params(self,
                                    address: 'Address', public_key: str) -> Dict[str, str]:
        name = f"node{address}"
        if public_key is None:
            public_key = self._create_dummy_public_key(name.encode()).hex()

        return {
            ConstantKeys.NAME: name,
            ConstantKeys.COUNTRY: "ZZZ",
            ConstantKeys.CITY: "Unknown",
            ConstantKeys.EMAIL: f"{name}@example.com",
            ConstantKeys.WEBSITE: f"https://{name}.example.com",
            ConstantKeys.DETAILS: f"https://{name}.example.com/details",
            ConstantKeys.P2P_ENDPOINT: f"{name}.example.com:7100",
            ConstantKeys.PUBLIC_KEY: public_key
        }

    def create_set_prep_tx(self,
                           address: 'Address',
                           set_data: Dict[str, Union[str, bytes]] = None):
        if set_data is None:
            set_data: dict = {}
        return self._make_score_call_tx(address, ZERO_SCORE_ADDRESS, 'setPRep', set_data)

    def create_set_governance_variables(
            self, address: 'Address', irep: int) -> dict:
        """Create a setGovernanceVariables TX

        :param address: from address
        :param irep: irep in loop
        :return:
        """
        return self._make_score_call_tx(
            addr_from=address,
            addr_to=ZERO_SCORE_ADDRESS,
            method="setGovernanceVariables",
            params={"irep": hex(irep)}
        )

    def create_unregister_prep_tx(self,
                                  address: 'Address'):
        return self._make_score_call_tx(address, ZERO_SCORE_ADDRESS, 'unregisterPRep', {})

    def create_claim_tx(self,
                        address: 'Address'):
        return self._make_score_call_tx(address, ZERO_SCORE_ADDRESS, 'claimIScore', {})

    def get_main_prep_list(self) -> dict:
        query_request = {
            "version": self._version,
            "from": self._admin,
            "to": ZERO_SCORE_ADDRESS,
            "dataType": "call",
            "data": {
                "method": "getMainPRepList",
                "params": {}
            }
        }
        return self._query(query_request)

    def get_sub_prep_list(self) -> dict:
        query_request = {
            "version": self._version,
            "from": self._admin,
            "to": ZERO_SCORE_ADDRESS,
            "dataType": "call",
            "data": {
                "method": "getSubPRepList",
                "params": {}
            }
        }
        return self._query(query_request)

    def get_prep_list(self,
                      start_ranking: Optional[int] = None,
                      end_ranking: Optional[int] = None) -> dict:
        params = {}
        if start_ranking is not None:
            params['startRanking'] = hex(start_ranking)
        if end_ranking is not None:
            params['endRanking'] = hex(end_ranking)

        query_request = {
            "version": self._version,
            "from": self._admin,
            "to": ZERO_SCORE_ADDRESS,
            "dataType": "call",
            "data": {
                "method": "getPRepList",
                "params": params
            }
        }
        return self._query(query_request)

    def get_prep(self,
                 prep: Union['Address', str]) -> dict:
        if isinstance(prep, Address):
            prep: str = str(prep)

        query_request = {
            "version": self._version,
            "from": self._admin,
            "to": ZERO_SCORE_ADDRESS,
            "dataType": "call",
            "data": {
                "method": "getPRep",
                "params": {"address": prep}
            }
        }
        return self._query(query_request)

    def get_stake(self,
                  address: Union['Address', str]) -> dict:
        if isinstance(address, Address):
            address: str = str(address)

        query_request = {
            "version": self._version,
            "from": self._admin,
            "to": ZERO_SCORE_ADDRESS,
            "dataType": "call",
            "data": {
                "method": "getStake",
                "params": {"address": address}
            }
        }
        return self._query(query_request)

    def get_delegation(self,
                       address: Union['Address', str]) -> dict:
        if isinstance(address, Address):
            address: str = str(address)

        query_request = {
            "version": self._version,
            "from": self._admin,
            "to": ZERO_SCORE_ADDRESS,
            "dataType": "call",
            "data": {
                "method": "getDelegation",
                "params": {"address": address}
            }
        }
        return self._query(query_request)

    def query_iscore(self,
                     address: Union['Address', str]) -> dict:
        if isinstance(address, Address):
            address: str = str(address)

        query_request = {
            "version": self._version,
            "from": self._admin,
            "to": ZERO_SCORE_ADDRESS,
            "dataType": "call",
            "data": {
                "method": "queryIScore",
                "params": {"address": address}
            }
        }
        return self._query(query_request)

    def get_iiss_info(self) -> dict:

        query_request = {
            "version": self._version,
            "from": self._admin,
            "to": ZERO_SCORE_ADDRESS,
            "dataType": "call",
            "data": {
                "method": "getIISSInfo",
                "params": {}
            }
        }
        return self._query(query_request)

    def get_balance(self,
                    address: Union['Address', str]) -> int:
        if isinstance(address, str):
            address: 'Address' = Address.from_string(address)

        return self._query({"address": address}, 'icx_getBalance')

    def get_total_supply(self) -> int:
        return self._query({}, 'icx_getTotalSupply')

    def init_decentralized(self):
        # decentralized
        self.update_governance()

        # set Revision REV_IISS
        tx: dict = self.create_set_revision_tx(REV_IISS)
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)

        expected_irep_when_rev_iiss = 0
        response: dict = self.get_iiss_info()
        self.assertEqual(expected_irep_when_rev_iiss, response['variable']['irep'])

        main_preps = self._addr_array[:PREP_MAIN_PREPS]

        total_supply = TOTAL_SUPPLY * ICX_IN_LOOP
        # Minimum_delegate_amount is 0.02 * total_supply
        # In this test delegate 0.03*total_supply because `Issue transaction` exists since REV_IISS
        minimum_delegate_amount_for_decentralization: int = total_supply * 2 // 1000 + 1
        init_balance: int = minimum_delegate_amount_for_decentralization * 10

        # distribute icx PREP_MAIN_PREPS ~ PREP_MAIN_PREPS + PREP_MAIN_PREPS - 1
        tx_list: list = []
        for i in range(PREP_MAIN_PREPS):
            tx: dict = self._make_icx_send_tx(self._genesis,
                                              self._addr_array[PREP_MAIN_PREPS + i],
                                              init_balance)
            tx_list.append(tx)
        prev_block, tx_results = self._make_and_req_block(tx_list)
        for tx_result in tx_results:
            self.assertEqual(int(True), tx_result.status)
        self._write_precommit_state(prev_block)

        # stake PREP_MAIN_PREPS ~ PREP_MAIN_PREPS + PREP_MAIN_PREPS - 1
        stake_amount: int = minimum_delegate_amount_for_decentralization
        tx_list: list = []
        for i in range(PREP_MAIN_PREPS):
            tx: dict = self.create_set_stake_tx(self._addr_array[PREP_MAIN_PREPS + i],
                                                stake_amount)
            tx_list.append(tx)
        prev_block, tx_results = self._make_and_req_block(tx_list)
        for tx_result in tx_results:
            self.assertEqual(int(True), tx_result.status)
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

        # register PRep
        tx_list: list = []

        for i, address in enumerate(main_preps):
            tx: dict = self.create_register_prep_tx(address, public_key=f"0x{self.public_key_array[i].hex()}")
            tx_list.append(tx)
        prev_block, tx_results = self._make_and_req_block(tx_list)
        for tx_result in tx_results:
            self.assertEqual(int(True), tx_result.status)

        self._write_precommit_state(prev_block)
        # irep of each prep should be 50000 ICX when revision IISS_REV
        expected_inital_irep_of_prep = IISS_INITIAL_IREP
        for address in main_preps:
            response = self.get_prep(address)
            self.assertEqual(expected_inital_irep_of_prep, response['irep'])

        # delegate to PRep
        tx_list: list = []
        for i in range(PREP_MAIN_PREPS):
            tx: dict = self.create_set_delegation_tx(self._addr_array[PREP_MAIN_PREPS + i],
                                                     [
                                                         (
                                                             self._addr_array[i],
                                                             minimum_delegate_amount_for_decentralization
                                                         )
                                                     ])
            tx_list.append(tx)
        prev_block, tx_results = self._make_and_req_block(tx_list)
        for tx_result in tx_results:
            self.assertEqual(int(True), tx_result.status)
        self._write_precommit_state(prev_block)

        # get main prep
        response: dict = self.get_main_prep_list()
        expected_response: dict = {
            "preps": [],
            "totalDelegated": 0
        }
        self.assertEqual(expected_response, response)

        # set Revision REV_IISS (decentralization)
        tx: dict = self.create_set_revision_tx(REV_DECENTRALIZATION)
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)

        expected_irep_when_decentralized = IISS_INITIAL_IREP
        response: dict = self.get_iiss_info()
        self.assertEqual(expected_irep_when_decentralized, response['variable']['irep'])

        # get main prep
        response: dict = self.get_main_prep_list()
        expected_preps: list = []
        expected_total_delegated: int = 0
        for address in main_preps:
            expected_preps.append({
                'address': address,
                'delegated': minimum_delegate_amount_for_decentralization
            })
            expected_total_delegated += minimum_delegate_amount_for_decentralization
        expected_response: dict = {
            "preps": expected_preps,
            "totalDelegated": expected_total_delegated
        }
        self.assertEqual(expected_response, response)

        # delegate to PRep 0
        tx_list: list = []
        for i in range(PREP_MAIN_PREPS):
            tx: dict = self.create_set_delegation_tx(self._addr_array[PREP_MAIN_PREPS + i],
                                                     [
                                                         (
                                                             self._addr_array[i],
                                                             0
                                                         )
                                                     ])
            tx_list.append(tx)
        prev_block, tx_results = self._make_and_req_block(tx_list)
        for tx_result in tx_results:
            self.assertEqual(int(True), tx_result.status)
        self._write_precommit_state(prev_block)

        self.make_blocks_to_end_calculation()

        # get main prep
        response: dict = self.get_main_prep_list()
        expected_preps: list = []
        for address in main_preps:
            expected_preps.append({
                'address': address,
                'delegated': 0
            })
        expected_response: dict = {
            "preps": expected_preps,
            "totalDelegated": 0
        }
        self.assertEqual(expected_response, response)
