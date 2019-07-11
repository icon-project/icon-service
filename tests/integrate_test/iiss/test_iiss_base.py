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
from typing import List, Tuple, Dict, Union, Optional

from iconservice.base.address import Address
from iconservice.base.address import ZERO_SCORE_ADDRESS, GOVERNANCE_SCORE_ADDRESS
from iconservice.base.type_converter_templates import ConstantKeys
from iconservice.icon_constant import ConfigKey
from tests.integrate_test.test_integrate_base import TestIntegrateBase


class TestIISSBase(TestIntegrateBase):

    def _make_init_config(self) -> dict:
        return {
            ConfigKey.SERVICE: {
                ConfigKey.SERVICE_FEE: True
            },
            ConfigKey.IISS_CALCULATE_PERIOD: 10,
            ConfigKey.TERM_PERIOD: 10}

    def make_blocks(self, to: int):
        block_height = self._block_height

        while to > block_height:
            tx = self._make_icx_send_tx(self._genesis, self._addr_array[0], 0)
            prev_block, tx_results = self._make_and_req_block([tx])
            self._write_precommit_state(prev_block)
            block_height = self._block_height

    def make_blocks_to_next_calculation(self) -> int:
        iiss_info: dict = self.get_iiss_info()
        next_calculation: int = iiss_info.get('nextCalculation', 0)

        self.make_blocks(to=next_calculation)

        self.assertEqual(self._block_height, next_calculation)

        return next_calculation

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
                                reg_data: Dict[str, Union[str, bytes]] = None):
        if reg_data is None:
            reg_data: dict = self.create_register_prep_params(address)

        return self._make_score_call_tx(address, ZERO_SCORE_ADDRESS, 'registerPRep', reg_data)

    @staticmethod
    def _create_dummy_public_key(data: bytes) -> bytes:
        return b"\x04" + hashlib.sha3_512(data).digest()

    def create_register_prep_params(self,
                                    address: 'Address') -> Dict[str, str]:
        name = f"node{address}"

        return {
            ConstantKeys.NAME: name,
            ConstantKeys.EMAIL: f"{name}@example.com",
            ConstantKeys.WEBSITE: f"https://{name}.example.com",
            ConstantKeys.DETAILS: f"https://{name}.example.com/details",
            ConstantKeys.P2P_END_POINT: f"https://{name}.example.com:7100",
            ConstantKeys.PUBLIC_KEY: self._create_dummy_public_key(name.encode()).hex()
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
                      start_index: Optional[int] = None,
                      end_index: Optional[int] = None) -> dict:
        params = {}
        if start_index is not None:
            params['startRanking'] = hex(start_index)
        if end_index is not None:
            params['endRanking'] = hex(end_index)

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
