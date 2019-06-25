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
from iconservice.icon_constant import IconScoreContextType, REV_IISS, PREP_SUB_PREPS
from iconservice.icon_constant import REV_DECENTRALIZATION, IISS_MIN_IREP, PREP_MAIN_PREPS
from iconservice.iconscore.icon_score_context import IconScoreContext
from iconservice.iiss import get_minimum_delegate_for_bottom_prep
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

    # decentralize by delegate to 22 accounts.
    def _decentralize(self, main_preps: list=None):
        self.total_supply = 2_000_000 * self._icx_factor
        if main_preps is None:
            self.main_preps = [create_address() for _ in range(PREP_MAIN_PREPS)]
        else:
            self.main_preps = main_preps
        # Minimum_delegate_amount is 0.02 * total_supply
        # In this test delegate 0.03*total_supply because `Issue transaction` exists since REV_IISS
        self.delegate_amount = self.total_supply * 3 // 1000
        # Can delegate up to 10 preps at a time
        stake_amount: int = self.delegate_amount * 10
        addr1, addr2, addr3 = create_address(), create_address(), create_address()
        tx1 = self._make_icx_send_tx(self._genesis, addr1, stake_amount)
        tx2 = self._make_icx_send_tx(self._genesis, addr2, stake_amount)
        tx3 = self._make_icx_send_tx(self._genesis, addr3, stake_amount)
        prev_block, tx_results = self._make_and_req_block([tx1, tx2, tx3])
        self._write_precommit_state(prev_block)
        # stake
        self._stake(addr1, stake_amount)
        self._stake(addr2, stake_amount)
        self._stake(addr3, stake_amount)
        # register preps
        for i, address in enumerate(self.main_preps):
            data: dict = {
                ConstantKeys.NAME: "name",
                ConstantKeys.EMAIL: "email",
                ConstantKeys.WEBSITE: "website",
                ConstantKeys.DETAILS: "json",
                ConstantKeys.P2P_END_POINT: "ip",
                ConstantKeys.PUBLIC_KEY: f'publicKey{i}'.encode(),
                ConstantKeys.IREP: IISS_MIN_IREP
            }
            self._reg_prep(address, data)

        # delegate
        delegate_info_addr1 = [{"address": str(address), "value": hex(self.delegate_amount)}
                               for address in self._addr_array[:10]]
        self._delegate(addr1, delegate_info_addr1)

        delegate_info_addr2 = [{"address": str(address), "value": hex(self.delegate_amount)}
                               for address in self._addr_array[10:20]]
        self._delegate(addr2, delegate_info_addr2)

        delegate_info_addr3 = [{"address": str(address), "value": hex(self.delegate_amount)}
                               for address in self._addr_array[20:22]]
        self._delegate(addr3, delegate_info_addr3)

    def _send_icx_in_loop(self, to_addr: 'Address', balance: int):
        tx = self._make_icx_send_tx(self._genesis, to_addr, balance)
        tx_list = [tx]
        prev_block, tx_results = self._make_and_req_block(tx_list)
        self._write_precommit_state(prev_block)

    def test_reg_prep(self):
        self._update_governance()
        self._set_revision(REV_IISS)
        new_prep = create_address()

        reg_data: dict = {
            ConstantKeys.NAME: "name1",
            ConstantKeys.EMAIL: "email1",
            ConstantKeys.WEBSITE: "website1",
            ConstantKeys.DETAILS: "json1",
            ConstantKeys.P2P_END_POINT: "ip1",
            ConstantKeys.PUBLIC_KEY: f'publicKey1'.encode(),
            ConstantKeys.IREP: IISS_MIN_IREP
        }
        self._reg_prep(new_prep, reg_data)

        query_request = {
            "version": self._version,
            "from": self._addr_array[0],
            "to": ZERO_SCORE_ADDRESS,
            "dataType": "call",
            "data": {
                "method": "getPRep",
                "params": {
                    "address": str(new_prep)
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
        self._update_governance()
        self._set_revision(REV_IISS)
        self._addr_array = [create_address() for _ in range(_PREPS_LEN)]

        # generate preps
        self._decentralize(self._addr_array)
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

        self.assertEqual(self.delegate_amount * 22, total_delegated)
        self.assertEqual(_PREPS_LEN, len(prep_list))

        # set revision to REV_DECENTRALIZATION
        tx = self._make_score_call_tx(self._admin, GOVERNANCE_SCORE_ADDRESS, 'setRevision',
                                      {"code": hex(REV_DECENTRALIZATION), "name": f"1.1.{REV_DECENTRALIZATION}"})
        tx_list = [tx]
        prev_block, tx_results, main_prep_as_dict = self._make_and_req_block_for_prep_test(tx_list)

        # check if tx_result has all fields correctly
        self.assertTrue('preps' and 'state' and 'rootHash' in main_prep_as_dict)
        self.assertTrue(PREP_MAIN_PREPS, len(main_prep_as_dict["preps"]))
        self.assertEqual(0, main_prep_as_dict["state"])

        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))
        self.assertEqual(0, main_prep_as_dict["state"])

        # check if main preps elected
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
        self.assertEqual(PREP_MAIN_PREPS, len(org_response_of_main_prep_list["preps"]))

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
        self.assertEqual(min(_PREPS_LEN - PREP_MAIN_PREPS, PREP_SUB_PREPS - PREP_MAIN_PREPS), len(response["preps"]))

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

        greatest_delegate_amount = self.delegate_amount + 1
        # stake
        self._stake(self._genesis, greatest_delegate_amount)

        # delegate greatest_amount to last prep
        last_addr = self._addr_array[_PREPS_LEN - 1]
        delegations = [{
            "address": str(last_addr),
            "value": hex(greatest_delegate_amount)
        }]
        self._delegate(self._genesis, delegations)

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
        org_response_of_main_prep_list["preps"][0] = {"address": last_addr,
                                                      "delegated": greatest_delegate_amount}

        self.assertEqual(org_response_of_main_prep_list["preps"], response_of_main_prep_list["preps"])

    def test_weighted_average_of_irep(self):
        """
        Scenario
        1. generates preps and delegates more than minumum delegated amount to 22 preps
        2. sets revision to REV_DECENTRALIZATION and generates main and sub preps
        3. check wighted average of irep correct
        :return:
        """
        _PREPS_LEN = 50
        _MAIN_PREPS_LEN = 22
        context = IconScoreContext(IconScoreContextType.DIRECT)
        _AMOUNT_DELEGATE = int(get_minimum_delegate_for_bottom_prep(context=context) * 2)

        self._update_governance()
        self._set_revision(REV_IISS)
        _addr_array = [create_address() for _ in range(_PREPS_LEN)]

        _addr_array_from_1 = create_address()
        _addr_array_from_2 = create_address()
        self._send_icx_in_loop(_addr_array_from_1, _AMOUNT_DELEGATE * 10)
        self._send_icx_in_loop(_addr_array_from_2, _AMOUNT_DELEGATE * 10)

        buf_total_irep = 0
        # generate preps
        for i in range(_PREPS_LEN):
            if i < 22:
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
            self._reg_prep(_addr_array[i], reg_data)

        from_addr_for_stake = [self._admin, _addr_array_from_1, _addr_array_from_2]

        idx_for_stake = 10
        for idx, from_addr in enumerate(from_addr_for_stake):
            # stake
            self._stake(from_addr, _AMOUNT_DELEGATE * 10)
            delegations = []
            for i in range(idx_for_stake - 10, idx_for_stake):
                if i > 21:
                    break
                delegations.append({
                    "address": str(_addr_array[i]),
                    "value": hex(_AMOUNT_DELEGATE)
                })
            self._delegate(from_addr, delegations)
            idx_for_stake += 10

        # set revision to REV_DECENTRALIZATION
        tx = self._make_score_call_tx(self._admin, GOVERNANCE_SCORE_ADDRESS, 'setRevision',
                                      {"code": hex(REV_DECENTRALIZATION), "name": f"1.1.{REV_DECENTRALIZATION}"})
        block, invoke_response, main_prep_as_dict = self._make_and_req_block_for_prep_test([tx])
        self.assertEqual((_AMOUNT_DELEGATE * buf_total_irep) // (_AMOUNT_DELEGATE * _MAIN_PREPS_LEN),
                         main_prep_as_dict['irep'])
