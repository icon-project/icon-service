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
from copy import deepcopy
from typing import TYPE_CHECKING

from iconservice.base.address import ZERO_SCORE_ADDRESS, GOVERNANCE_SCORE_ADDRESS
from iconservice.base.exception import InvalidParamsException
from iconservice.base.type_converter_templates import ConstantKeys
from iconservice.icon_constant import REV_IISS, REV_DECENTRALIZATION, IISS_MIN_IREP
from tests import create_address
from tests.integrate_test.test_integrate_base import TestIntegrateBase

if TYPE_CHECKING:
    from iconservice import Address


class TestIntegratePrep(TestIntegrateBase):

    def _update_governance(self):
        tx = self._make_deploy_tx("sample_builtin",
                                  "latest_version/governance",
                                  self._admin,
                                  GOVERNANCE_SCORE_ADDRESS)
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)

    def _set_revision(self, revision: int):
        set_revision_tx = self._make_score_call_tx(self._admin, GOVERNANCE_SCORE_ADDRESS, 'setRevision',
                                                   {"code": hex(revision), "name": f"1.1.{revision}"})
        prev_block, tx_results = self._make_and_req_block([set_revision_tx])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))

    def _stake(self, address: 'Address', value: int):
        tx = self._make_score_call_tx(address, ZERO_SCORE_ADDRESS, 'setStake', {"value": hex(value)})

        tx_list = [tx]
        prev_block, tx_results = self._make_and_req_block(tx_list)

        self._write_precommit_state(prev_block)

    def _delegate(self, address: 'Address', delegations: list):
        tx = self._make_score_call_tx(address, ZERO_SCORE_ADDRESS, 'setDelegation', {"delegations": delegations})

        tx_list = [tx]
        prev_block, tx_results = self._make_and_req_block(tx_list)
        self._write_precommit_state(prev_block)

    def _reg_prep(self, address: 'Address', data: dict):

        data = deepcopy(data)
        value: str = data[ConstantKeys.PUBLIC_KEY].hex()
        data[ConstantKeys.PUBLIC_KEY] = value
        value: str = hex(data[ConstantKeys.IREP])
        data[ConstantKeys.IREP] = value

        tx = self._make_score_call_tx(address, ZERO_SCORE_ADDRESS, 'registerPRep', data)
        tx_list = [tx]
        prev_block, tx_results = self._make_and_req_block(tx_list)
        self.assertEqual('PRepRegistered(Address)', tx_results[1].event_logs[0].indexed[0])
        self.assertEqual(address, tx_results[1].event_logs[0].data[0])
        self._write_precommit_state(prev_block)

    def _reg_prep_bulk(self, bulk: list):
        tx_list: list = []

        for address, data in bulk:
            tx = self._make_score_call_tx(address, ZERO_SCORE_ADDRESS, 'registerPRep', data)
            tx_list.append(tx)

        prev_block, tx_results = self._make_and_req_block(tx_list)
        self._write_precommit_state(prev_block)

    def _set_prep(self, address: 'Address', data: dict):

        data = deepcopy(data)
        value = data.get(ConstantKeys.IREP)
        if value:
            data[ConstantKeys.IREP] = hex(value)

        tx = self._make_score_call_tx(address, ZERO_SCORE_ADDRESS, 'setPRep', data)
        tx_list = [tx]
        prev_block, tx_results = self._make_and_req_block(tx_list)
        self.assertEqual('PRepSet(Address)', tx_results[1].event_logs[0].indexed[0])
        self.assertEqual(address, tx_results[1].event_logs[0].data[0])
        self._write_precommit_state(prev_block)

    def _unreg_prep(self, address: 'Address'):

        tx = self._make_score_call_tx(address, ZERO_SCORE_ADDRESS, 'unregisterPRep', {})
        tx_list = [tx]
        prev_block, tx_results = self._make_and_req_block(tx_list)
        self.assertEqual('PRepUnregistered(Address)', tx_results[1].event_logs[0].indexed[0])
        self.assertEqual(address, tx_results[1].event_logs[0].data[0])
        self._write_precommit_state(prev_block)

    def test_reg_prep(self):
        self._update_governance()
        self._set_revision(REV_IISS)

        reg_data: dict = {
            ConstantKeys.NAME: "name1",
            ConstantKeys.EMAIL: "email1",
            ConstantKeys.WEBSITE: "website1",
            ConstantKeys.DETAILS: "json1",
            ConstantKeys.P2P_END_POINT: "ip1",
            ConstantKeys.PUBLIC_KEY: f'publicKey1'.encode(),
            ConstantKeys.IREP: IISS_MIN_IREP
        }
        self._reg_prep(self._addr_array[0], reg_data)

        query_request = {
            "version": self._version,
            "from": self._addr_array[0],
            "to": ZERO_SCORE_ADDRESS,
            "dataType": "call",
            "data": {
                "method": "getPRep",
                "params": {
                    "address": str(self._addr_array[0])
                }
            }
        }
        response = self._query(query_request)
        register = response["registration"]
        self.assertEqual(reg_data[ConstantKeys.NAME], register[ConstantKeys.NAME])
        self.assertEqual(reg_data[ConstantKeys.EMAIL], register[ConstantKeys.EMAIL])
        self.assertEqual(reg_data[ConstantKeys.WEBSITE], register[ConstantKeys.WEBSITE])
        self.assertEqual(reg_data[ConstantKeys.DETAILS], register[ConstantKeys.DETAILS])
        self.assertEqual(reg_data[ConstantKeys.P2P_END_POINT], register[ConstantKeys.P2P_END_POINT])
        self.assertEqual(reg_data[ConstantKeys.PUBLIC_KEY], register[ConstantKeys.PUBLIC_KEY])
        self.assertEqual(reg_data[ConstantKeys.IREP], register[ConstantKeys.IREP])

    def test_set_prep(self):
        self._update_governance()
        self._set_revision(REV_IISS)

        reg_data: dict = {
            ConstantKeys.NAME: "name1",
            ConstantKeys.EMAIL: "email1",
            ConstantKeys.WEBSITE: "website1",
            ConstantKeys.DETAILS: "json1",
            ConstantKeys.P2P_END_POINT: "ip1",
            ConstantKeys.PUBLIC_KEY: f'publicKey1'.encode(),
            ConstantKeys.IREP: IISS_MIN_IREP
        }
        self._reg_prep(self._addr_array[0], reg_data)

        update_data: dict = {
            ConstantKeys.NAME: "name0",
            ConstantKeys.IREP: IISS_MIN_IREP + 100,
        }
        self._set_prep(self._addr_array[0], update_data)

        query_request = {
            "version": self._version,
            "from": self._addr_array[0],
            "to": ZERO_SCORE_ADDRESS,
            "dataType": "call",
            "data": {
                "method": "getPRep",
                "params": {
                    "address": str(self._addr_array[0])
                }
            }
        }
        response = self._query(query_request)
        register = response["registration"]

        self.assertEqual(update_data[ConstantKeys.NAME], register[ConstantKeys.NAME])
        self.assertEqual(reg_data[ConstantKeys.EMAIL], register[ConstantKeys.EMAIL])
        self.assertEqual(reg_data[ConstantKeys.WEBSITE], register[ConstantKeys.WEBSITE])
        self.assertEqual(reg_data[ConstantKeys.DETAILS], register[ConstantKeys.DETAILS])
        self.assertEqual(reg_data[ConstantKeys.P2P_END_POINT], register[ConstantKeys.P2P_END_POINT])
        self.assertEqual(reg_data[ConstantKeys.PUBLIC_KEY], register[ConstantKeys.PUBLIC_KEY])
        self.assertEqual(update_data[ConstantKeys.IREP], register[ConstantKeys.IREP])

    def test_unreg_prep_candidate(self):
        self._update_governance()
        self._set_revision(REV_IISS)

        reg_data: dict = {
            ConstantKeys.NAME: "name1",
            ConstantKeys.EMAIL: "email1",
            ConstantKeys.WEBSITE: "website1",
            ConstantKeys.DETAILS: "json1",
            ConstantKeys.P2P_END_POINT: "ip1",
            ConstantKeys.PUBLIC_KEY: f'publicKey1'.encode(),
            ConstantKeys.IREP: IISS_MIN_IREP
        }
        self._reg_prep(self._addr_array[0], reg_data)
        self._unreg_prep(self._addr_array[0])

        query_request = {
            "version": self._version,
            "from": self._addr_array[0],
            "to": ZERO_SCORE_ADDRESS,
            "dataType": "call",
            "data": {
                "method": "getPRep",
                "params": {
                    "address": str(self._addr_array[0])
                }
            }
        }

        with self.assertRaises(InvalidParamsException) as e:
            response = self._query(query_request)
        self.assertEqual(f'P-Rep not found: {str(self._addr_array[0])}', e.exception.args[0])

    def test_prep_list(self):
        self._update_governance()
        self._set_revision(REV_IISS)

        for i in range(10):
            reg_data: dict = {
                ConstantKeys.NAME: f"name{i}",
                ConstantKeys.EMAIL: f"email{i}",
                ConstantKeys.WEBSITE: f"website{i}",
                ConstantKeys.DETAILS: f"json{i}",
                ConstantKeys.P2P_END_POINT: f"ip{i}",
                ConstantKeys.PUBLIC_KEY: f'publicKey{i}'.encode(),
                ConstantKeys.IREP: IISS_MIN_IREP + i
            }
            self._reg_prep(self._addr_array[i], reg_data)

        query_request = {
            "version": self._version,
            "from": self._addr_array[0],
            "to": ZERO_SCORE_ADDRESS,
            "dataType": "call",
            "data": {
                "method": "getPRepList",
                "params": {}
            }
        }
        response = self._query(query_request)
        total_delegated: int = response['totalDelegated']
        prep_list: list = response['preps']

        self.assertEqual(0, total_delegated)
        self.assertEqual(10, len(prep_list))

    def test_prep_list2(self):
        self._update_governance()
        self._set_revision(REV_IISS)

        bulk: list = []
        preps = 3000
        for i in range(preps):
            reg_data: dict = {
                ConstantKeys.NAME: f"name{i}",
                ConstantKeys.EMAIL: f"email{i}",
                ConstantKeys.WEBSITE: f"website{i}",
                ConstantKeys.DETAILS: f"json{i}",
                ConstantKeys.P2P_END_POINT: f"ip{i}",
                ConstantKeys.PUBLIC_KEY: f'publicKey{i}'.encode().hex(),
                ConstantKeys.IREP: hex(IISS_MIN_IREP + i)
            }
            bulk.append((create_address(), reg_data))
        self._reg_prep_bulk(bulk)

        query_request = {
            "version": self._version,
            "from": self._addr_array[0],
            "to": ZERO_SCORE_ADDRESS,
            "dataType": "call",
            "data": {
                "method": "getPRepList",
                "params": {
                    "startRanking": hex(0),
                    "endRanking": hex(1)
                }
            }
        }
        with self.assertRaises(InvalidParamsException) as e:
            response = self._query(query_request)
        self.assertEqual("Invalid params: startRanking", e.exception.args[0])

        query_request = {
            "version": self._version,
            "from": self._addr_array[0],
            "to": ZERO_SCORE_ADDRESS,
            "dataType": "call",
            "data": {
                "method": "getPRepList",
                "params": {
                    "startRanking": hex(1),
                    "endRanking": hex(0)
                }
            }
        }
        with self.assertRaises(InvalidParamsException) as e:
            response = self._query(query_request)
        self.assertEqual("Invalid params: endRanking", e.exception.args[0])

        query_request = {
            "version": self._version,
            "from": self._addr_array[0],
            "to": ZERO_SCORE_ADDRESS,
            "dataType": "call",
            "data": {
                "method": "getPRepList",
                "params": {
                    "startRanking": hex(2),
                    "endRanking": hex(1)
                }
            }
        }
        with self.assertRaises(InvalidParamsException) as e:
            response = self._query(query_request)
        self.assertEqual("Invalid params: reverse", e.exception.args[0])

        query_request = {
            "version": self._version,
            "from": self._addr_array[0],
            "to": ZERO_SCORE_ADDRESS,
            "dataType": "call",
            "data": {
                "method": "getPRepList",
                "params": {
                    "startRanking": hex(2),
                    "endRanking": hex(2)
                }
            }
        }
        response = self._query(query_request)
        prep_list: list = response['preps']
        self.assertEqual(1, len(prep_list))

        query_request = {
            "version": self._version,
            "from": self._addr_array[0],
            "to": ZERO_SCORE_ADDRESS,
            "dataType": "call",
            "data": {
                "method": "getPRepList",
                "params": {
                    "startRanking": hex(1)
                }
            }
        }
        response = self._query(query_request)
        prep_list: list = response['preps']
        self.assertEqual(3000, len(prep_list))

    def test_update_prep_list(self):
        """
        Scenario
        1. generates preps
        2. sets revision to REV_DECENTRALIZATION and generates main and sub preps
        3. checks its tx result
        4. unregisters the first main prep
        5. delegates 10000 to the last prep
        6. check main preps sorted
        :return:
        """
        _PREPS_LEN = 200
        _MAIN_PREPS_LEN = 22
        _AMOUNT_DELEGATE = 10000
        self._update_governance()
        self._set_revision(REV_IISS)
        self._addr_array = [create_address() for _ in range(_PREPS_LEN)]

        # generate preps
        for i in range(_PREPS_LEN):
            reg_data: dict = {
                ConstantKeys.NAME: f"name{i}",
                ConstantKeys.EMAIL: f"email{i}",
                ConstantKeys.WEBSITE: f"website{i}",
                ConstantKeys.DETAILS: f"json{i}",
                ConstantKeys.P2P_END_POINT: f"ip{i}",
                ConstantKeys.PUBLIC_KEY: f'publicKey{i}'.encode(),
                ConstantKeys.IREP: IISS_MIN_IREP + i
            }
            self._reg_prep(self._addr_array[i], reg_data)

        query_request = {
            "version": self._version,
            "from": self._addr_array[0],
            "to": ZERO_SCORE_ADDRESS,
            "dataType": "call",
            "data": {
                "method": "getPRepList",
                "params": {
                    "address": str(self._addr_array[0])
                }
            }
        }
        response = self._query(query_request)
        total_delegated: int = response['totalDelegated']
        prep_list: list = response['preps']

        self.assertEqual(0, total_delegated)
        self.assertEqual(_PREPS_LEN, len(prep_list))

        # set revision to REV_DECENTRALIZATION
        tx = self._make_score_call_tx(self._admin, GOVERNANCE_SCORE_ADDRESS, 'setRevision',
                                      {"code": hex(REV_DECENTRALIZATION), "name": f"1.1.{REV_DECENTRALIZATION}"})
        tx_list = [tx]
        prev_block, tx_results, main_prep_as_dict = self._make_and_req_block_for_prep_test(tx_list)

        # check if tx_result has all of field correctly
        self.assertTrue('preps' and 'state' and 'rootHash' in main_prep_as_dict)
        self.assertTrue(_MAIN_PREPS_LEN, len(main_prep_as_dict["preps"]))
        self.assertEqual(0, main_prep_as_dict["state"])

        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))
        self.assertEqual(0, main_prep_as_dict["state"])

        # check if generating main preps
        query_request = {
            "version": self._version,
            "from": self._addr_array[0],
            "to": ZERO_SCORE_ADDRESS,
            "dataType": "call",
            "data": {
                "method": "getMainPRepList",
                "params": {}
            }
        }
        org_response_of_main_prep_list = self._query(query_request)
        self.assertEqual(_MAIN_PREPS_LEN, len(org_response_of_main_prep_list["preps"]))

        # check if generating sub preps
        query_request = {
            "version": self._version,
            "from": self._addr_array[0],
            "to": ZERO_SCORE_ADDRESS,
            "dataType": "call",
            "data": {
                "method": "getSubPRepList",
                "params": {}
            }
        }
        response = self._query(query_request)
        self.assertEqual(min(_PREPS_LEN - _MAIN_PREPS_LEN, 100 - _MAIN_PREPS_LEN), len(response["preps"]))

        # un-register first main prep
        first_main_prep = org_response_of_main_prep_list["preps"][0]["address"]
        self._unreg_prep(first_main_prep)

        query_request = {
            "version": self._version,
            "from": self._addr_array[0],
            "to": ZERO_SCORE_ADDRESS,
            "dataType": "call",
            "data": {
                "method": "getPRep",
                "params": {
                    "address": str(first_main_prep)
                }
            }
        }

        with self.assertRaises(InvalidParamsException) as e:
            self._query(query_request)
        self.assertEqual(f'P-Rep not found: {str(first_main_prep)}', e.exception.args[0])

        # stake
        self._stake(self._admin, _AMOUNT_DELEGATE)

        # delegate 10000 to last prep
        last_addr = self._addr_array[_PREPS_LEN - 1]
        delegations = [{
            "address": str(last_addr),
            "value": hex(_AMOUNT_DELEGATE)
        }]
        self._delegate(self._admin, delegations)

        for i in range(7):
            prev_block, tx_results = self._make_and_req_block([])
            self._write_precommit_state(prev_block)

        query_request = {
            "version": self._version,
            "from": self._addr_array[0],
            "to": ZERO_SCORE_ADDRESS,
            "dataType": "call",
            "data": {
                "method": "getMainPRepList",
                "params": {}
            }
        }
        # check if sorted correctly
        response_of_main_prep_list = self._query(query_request)
        org_response_of_main_prep_list["preps"][0] = {"address": last_addr, "delegated": _AMOUNT_DELEGATE}
        self.assertEqual(org_response_of_main_prep_list["preps"], response_of_main_prep_list["preps"])

    def test_weighted_average_of_irep(self):
        """
        Scenario
        1. generates preps and delegates 10000 to 10 preps
        2. sets revision to REV_DECENTRALIZATION and generates main and sub preps
        3. check wighted average of irep correct
        :return:
        """
        _PREPS_LEN = 200
        _MAIN_PREPS_LEN = 22
        _AMOUNT_DELEGATE = 10000
        self._update_governance()
        self._set_revision(REV_IISS)
        self._addr_array = [create_address() for _ in range(_PREPS_LEN)]

        buf_total_irep = 0
        # generate preps
        for i in range(_PREPS_LEN):
            if i < 10:
                buf_total_irep += IISS_MIN_IREP + i
            reg_data: dict = {
                ConstantKeys.NAME: f"name{i}",
                ConstantKeys.EMAIL: f"email{i}",
                ConstantKeys.WEBSITE: f"website{i}",
                ConstantKeys.DETAILS: f"json{i}",
                ConstantKeys.P2P_END_POINT: f"ip{i}",
                ConstantKeys.PUBLIC_KEY: f'publicKey{i}'.encode(),
                ConstantKeys.IREP: IISS_MIN_IREP + i
            }
            self._reg_prep(self._addr_array[i], reg_data)

        # stake
        self._stake(self._admin, _AMOUNT_DELEGATE * 10)
        delegations = []
        for i in range(10):
            delegations.append({
                "address": str(self._addr_array[i]),
                "value": hex(_AMOUNT_DELEGATE)
            })
        self._delegate(self._admin, delegations)

        # set revision to REV_DECENTRALIZATION
        tx = self._make_score_call_tx(self._admin, GOVERNANCE_SCORE_ADDRESS, 'setRevision',
                                      {"code": hex(REV_DECENTRALIZATION), "name": f"1.1.{REV_DECENTRALIZATION}"})
        block, invoke_response, main_prep_as_dict = self._make_and_req_block_for_prep_test([tx])
        self.assertEqual(_AMOUNT_DELEGATE * buf_total_irep // (_AMOUNT_DELEGATE * 10), main_prep_as_dict['irep'])
