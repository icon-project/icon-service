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
from iconservice.icon_constant import IconScoreContextType, REV_IISS, PREP_SUB_PREPS, IISS_INITIAL_IREP
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
        tx = self._make_score_call_tx(self._admin,
                                      GOVERNANCE_SCORE_ADDRESS,
                                      'setRevision',
                                      {"code": hex(revision),
                                       "name": f"1.1.{revision}"})
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))

    def _stake(self, address: 'Address', value: int):
        tx = self._make_score_call_tx(address, ZERO_SCORE_ADDRESS,
                                      'setStake',
                                      {"value": hex(value)})
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)

    def _delegate(self, address: 'Address', delegations: list):
        tx = self._make_score_call_tx(address,
                                      ZERO_SCORE_ADDRESS,
                                      'setDelegation',
                                      {"delegations": delegations})
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)

    def _reg_prep(self, address: 'Address', data: dict):

        data = deepcopy(data)
        value: str = data[ConstantKeys.PUBLIC_KEY].hex()
        data[ConstantKeys.PUBLIC_KEY] = value

        tx = self._make_score_call_tx(address,
                                      ZERO_SCORE_ADDRESS,
                                      'registerPRep',
                                      data)
        prev_block, tx_results = self._make_and_req_block([tx])
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

        tx = self._make_score_call_tx(address,
                                      ZERO_SCORE_ADDRESS,
                                      'setPRep',
                                      data)
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)

    def _unreg_prep(self, address: 'Address'):

        tx = self._make_score_call_tx(address,
                                      ZERO_SCORE_ADDRESS,
                                      'unregisterPRep',
                                      {})
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)

    # decentralize by delegate to n accounts.
    def _decentralize(self, preps: list, delegate_amount: int):

        # Can delegate up to 10 preps at a time
        stake_amount: int = delegate_amount * 10
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
        for i, address in enumerate(preps):
            data: dict = {
                ConstantKeys.NAME: f"name{i}",
                ConstantKeys.EMAIL: f"email{i}",
                ConstantKeys.WEBSITE: f"website{i}",
                ConstantKeys.DETAILS: f"json{i}",
                ConstantKeys.P2P_END_POINT: f"ip{i}",
                ConstantKeys.PUBLIC_KEY: f'publicKey{i}'.encode(),
            }
            self._reg_prep(address, data)

        # delegate
        data: list = [
            {
                "address": str(address),
                "value": hex(delegate_amount)
            }for address in preps[:10]]
        self._delegate(addr1, data)

        data: list = [
            {
                "address": str(address),
                "value": hex(delegate_amount)
            }for address in preps[10:20]]
        self._delegate(addr2, data)

        data: list = [
            {
                "address": str(address),
                "value": hex(delegate_amount)
            }for address in preps[20:22]]
        self._delegate(addr3, data)

    def _send_icx_in_loop(self, to_addr: 'Address', balance: int):
        tx = self._make_icx_send_tx(self._genesis, to_addr, balance)
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)

    def _get_prep(self, address: 'Address') -> dict:
        query_request = {
            "version": self._version,
            "from": self._addr_array[0],
            "to": ZERO_SCORE_ADDRESS,
            "dataType": "call",
            "data": {
                "method": "getPRep",
                "params": {
                    "address": str(address)
                }
            }
        }
        return self._query(query_request)

    def _get_prep_list(self) -> dict:
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
        return self._query(query_request)

    def _get_main_perps(self) -> dict:
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
        return self._query(query_request)

    def _get_sub_perps(self) -> dict:
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
        return self._query(query_request)

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
        self.assertEqual(preps, len(prep_list))

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

        addr_array = [create_address() for _ in range(_PREPS_LEN)]

        total_supply = 2_000_000 * self._icx_factor

        # Minimum_delegate_amount is 0.02 * total_supply
        # In this test delegate 0.03*total_supply because `Issue transaction` exists since REV_IISS
        delegate_amount = total_supply * 3 // 1000

        # generate preps
        self._decentralize(addr_array, delegate_amount)

        response = self._get_prep_list()
        total_delegated: int = response['totalDelegated']
        prep_list: list = response['preps']

        self.assertEqual(delegate_amount * 22, total_delegated)
        self.assertEqual(_PREPS_LEN, len(prep_list))

        # set revision to REV_DECENTRALIZATION
        tx = self._make_score_call_tx(self._admin, GOVERNANCE_SCORE_ADDRESS, 'setRevision',
                                      {"code": hex(REV_DECENTRALIZATION), "name": f"1.1.{REV_DECENTRALIZATION}"})
        prev_block, tx_results, main_prep_as_dict = self._make_and_req_block_for_prep_test([tx])

        # check if tx_result has all fields correctly
        self.assertTrue('preps' and 'state' and 'rootHash' in main_prep_as_dict)
        self.assertTrue(PREP_MAIN_PREPS, len(main_prep_as_dict["preps"]))
        self.assertEqual(0, main_prep_as_dict["state"])

        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))
        self.assertEqual(0, main_prep_as_dict["state"])

        # check if main preps elected
        main_preps = self._get_main_perps()["preps"]
        self.assertEqual(PREP_MAIN_PREPS, len(main_preps))

        # check if generating sub preps
        sub_preps = self._get_sub_perps()["preps"]
        self.assertEqual(min(_PREPS_LEN - PREP_MAIN_PREPS, PREP_SUB_PREPS - PREP_MAIN_PREPS), len(sub_preps))

        # un-register first main prep
        first_main_prep = main_preps[0]["address"]
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

        greatest_delegate_amount = delegate_amount + 1
        # stake
        self._stake(self._genesis, greatest_delegate_amount)

        # delegate greatest_amount to last prep
        last_addr = addr_array[_PREPS_LEN - 1]
        delegations = [
            {
                "address": str(last_addr),
                "value": hex(greatest_delegate_amount)
            }
        ]
        self._delegate(self._genesis, delegations)

        for i in range(7):
            prev_block, tx_results = self._make_and_req_block([])
            self._write_precommit_state(prev_block)

        # check if sorted correctly
        actual_main_preps = self._get_main_perps()["preps"]
        expected_main_preps: list = main_preps[1:]
        expected_main_preps.insert(
            0, {
                "address": last_addr,
                "delegated": greatest_delegate_amount
            })

        self.assertEqual(expected_main_preps, actual_main_preps)

    def test_weighted_average_of_irep(self):
        """
        Scenario
        1. generates preps and delegates more than minumum delegated amount to 22 preps
        2. sets revision to REV_DECENTRALIZATION and generates main and sub preps
        3. check wighted average of irep correct
        :return:
        """

        _PREPS_LEN = 50
        context = IconScoreContext(IconScoreContextType.DIRECT)
        _AMOUNT_DELEGATE = int(get_minimum_delegate_for_bottom_prep(context=context) * 2)

        self._update_governance()
        self._set_revision(REV_IISS)
        addr_array = [create_address() for _ in range(_PREPS_LEN)]

        self._send_icx_in_loop(addr_array[0], _AMOUNT_DELEGATE * 10)
        self._send_icx_in_loop(addr_array[1], _AMOUNT_DELEGATE * 10)

        buf_total_irep = 0
        # generate preps
        for i in range(_PREPS_LEN):
            if i < PREP_MAIN_PREPS:
                buf_total_irep += IISS_INITIAL_IREP
            reg_data: dict = {
                ConstantKeys.NAME: f"name{i}",
                ConstantKeys.EMAIL: f"email{i}",
                ConstantKeys.WEBSITE: f"website{i}",
                ConstantKeys.DETAILS: f"json{i}",
                ConstantKeys.P2P_END_POINT: f"ip{i}",
                ConstantKeys.PUBLIC_KEY: f'publicKey{i}'.encode(),
            }
            self._reg_prep(addr_array[i], reg_data)

        from_addr_for_stake = [self._admin, addr_array[0], addr_array[1]]

        idx_for_stake = 10
        for idx, from_addr in enumerate(from_addr_for_stake):
            # stake
            self._stake(from_addr, _AMOUNT_DELEGATE * 10)
            delegations = []
            for i in range(idx_for_stake - 10, idx_for_stake):
                if i > 21:
                    break
                delegations.append({
                    "address": str(addr_array[i]),
                    "value": hex(_AMOUNT_DELEGATE)
                })
            self._delegate(from_addr, delegations)
            idx_for_stake += 10

        # set revision to REV_DECENTRALIZATION
        tx = self._make_score_call_tx(self._admin, GOVERNANCE_SCORE_ADDRESS, 'setRevision',
                                      {"code": hex(REV_DECENTRALIZATION), "name": f"1.1.{REV_DECENTRALIZATION}"})
        block, invoke_response, main_prep_as_dict = self._make_and_req_block_for_prep_test([tx])
        self.assertEqual((_AMOUNT_DELEGATE * buf_total_irep) // (_AMOUNT_DELEGATE * PREP_MAIN_PREPS),
                         main_prep_as_dict['irep'])

    def test_low_productivity(self):
        _PREPS_LEN = 200
        _MAIN_PREPS_LEN = 22
        _AMOUNT_DELEGATE = 10000
        _MINIMUM_DELEGATE_AMOUNT = 10 ** 18

        self._update_governance()
        self._set_revision(REV_IISS)

        addr_array = [create_address() for _ in range(_PREPS_LEN)]

        total_supply = 2_000_000 * self._icx_factor

        # Minimum_delegate_amount is 0.02 * total_supply
        # In this test delegate 0.03*total_supply because `Issue transaction` exists since REV_IISS
        delegate_amount = total_supply * 3 // 1000

        # generate preps
        self._decentralize(addr_array, delegate_amount)

        response = self._get_prep_list()
        total_delegated: int = response['totalDelegated']
        prep_list: list = response['preps']

        self.assertEqual(delegate_amount * 22, total_delegated)
        self.assertEqual(_PREPS_LEN, len(prep_list))

        self._set_revision(REV_DECENTRALIZATION)

        # check if generating main preps
        main_preps = self._get_main_perps()["preps"]
        self.assertEqual(_MAIN_PREPS_LEN, len(main_preps))

        for i in range(10):
            prev_block, tx_results = self._make_and_req_block(
                [],
                prev_block_generator=addr_array[0],
                prev_block_validators=[addr_array[1], addr_array[2]])
            self._write_precommit_state(prev_block)

        info = self._get_prep(addr_array[0])
        total_blocks: int = info['stats']['totalBlocks']
        validated_blocks: int = info['stats']['validatedBlocks']
        self.assertEqual(10, total_blocks)
        self.assertEqual(10, validated_blocks)

        info = self._get_prep(addr_array[3])
        total_blocks: int = info['stats']['totalBlocks']
        validated_blocks: int = info['stats']['validatedBlocks']
        self.assertEqual(10, total_blocks)
        self.assertEqual(0, validated_blocks)

    def test_prep_set_irep_in_term(self):
        _PREPS_LEN = 22
        self._update_governance()
        self._set_revision(REV_IISS)

        addr_array = [create_address() for _ in range(_PREPS_LEN)]

        total_supply = 2_000_000 * self._icx_factor

        # Minimum_delegate_amount is 0.02 * total_supply
        # In this test delegate 0.03*total_supply because `Issue transaction` exists since REV_IISS
        delegate_amount = total_supply * 3 // 1000

        # generate preps
        self._decentralize(addr_array, delegate_amount)

        # set revision to REV_DECENTRALIZATION
        tx = self._make_score_call_tx(self._admin, GOVERNANCE_SCORE_ADDRESS, 'setRevision',
                                      {"code": hex(REV_DECENTRALIZATION), "name": f"1.1.{REV_DECENTRALIZATION}"})
        prev_block, tx_results, main_prep_as_dict = self._make_and_req_block_for_prep_test([tx])
        self.assertIsNotNone(main_prep_as_dict)
        data: dict = {
            ConstantKeys.NAME: "name0",
            ConstantKeys.EMAIL: "email0",
            ConstantKeys.WEBSITE: "website0",
            ConstantKeys.DETAILS: "json0",
            ConstantKeys.P2P_END_POINT: "ip0",
            ConstantKeys.PUBLIC_KEY: f'publicKey0'.encode(),
        }

        expected_response: dict = data
        response: dict = self._get_prep(addr_array[0])
        register = response["registration"]

        self.assertEqual(expected_response[ConstantKeys.NAME], register[ConstantKeys.NAME])
        self.assertEqual(expected_response[ConstantKeys.EMAIL], register[ConstantKeys.EMAIL])
        self.assertEqual(expected_response[ConstantKeys.WEBSITE], register[ConstantKeys.WEBSITE])
        self.assertEqual(expected_response[ConstantKeys.DETAILS], register[ConstantKeys.DETAILS])
        self.assertEqual(expected_response[ConstantKeys.P2P_END_POINT], register[ConstantKeys.P2P_END_POINT])
        self.assertEqual(expected_response[ConstantKeys.PUBLIC_KEY], register[ConstantKeys.PUBLIC_KEY])
        self.assertEqual(IISS_INITIAL_IREP, register[ConstantKeys.IREP])

        irep_value = int(IISS_INITIAL_IREP * 1.2)

        set_prep_data1: dict = {
            ConstantKeys.IREP: irep_value,
        }
        self._set_prep(addr_array[0], set_prep_data1)

        response: dict = self._get_prep(addr_array[0])
        register = response["registration"]
        self.assertEqual(data[ConstantKeys.NAME], register[ConstantKeys.NAME])
        self.assertEqual(data[ConstantKeys.WEBSITE], register[ConstantKeys.WEBSITE])
        self.assertEqual(hex(set_prep_data1[ConstantKeys.IREP]), hex(register[ConstantKeys.IREP]))

        irep_value2 = int(irep_value * 1.1)

        set_prep_data2: dict = {
            ConstantKeys.IREP: hex(irep_value2),
        }
        tx = self._make_score_call_tx(addr_array[0],
                                      ZERO_SCORE_ADDRESS,
                                      'setPRep',
                                      set_prep_data2)
        prev_block, tx_results = self._make_and_req_block([tx])
        set_result = tx_results[0]
        self.assertEqual(set_result.status, 0)
        failure_message = set_result.failure.message
        self.assertEqual(failure_message, "Can update irep only one time in term")

        response: dict = self._get_prep(addr_array[0])
        register = response["registration"]
        self.assertEqual(data[ConstantKeys.NAME], register[ConstantKeys.NAME])
        self.assertEqual(data[ConstantKeys.WEBSITE], register[ConstantKeys.WEBSITE])
        self.assertNotEqual(set_prep_data2[ConstantKeys.IREP], hex(register[ConstantKeys.IREP]))

    def test_prep_set_irep_in_term2(self):
        """Test for setting same irep value several time in term and other irep value"""
        _PREPS_LEN = 22
        self._update_governance()
        self._set_revision(REV_IISS)

        addr_array = [create_address() for _ in range(_PREPS_LEN)]

        total_supply = 2_000_000 * self._icx_factor

        # Minimum_delegate_amount is 0.02 * total_supply
        # In this test delegate 0.03*total_supply because `Issue transaction` exists since REV_IISS
        delegate_amount = total_supply * 3 // 1000

        # generate preps
        self._decentralize(addr_array, delegate_amount)

        # set revision to REV_DECENTRALIZATION
        tx = self._make_score_call_tx(self._admin, GOVERNANCE_SCORE_ADDRESS, 'setRevision',
                                      {"code": hex(REV_DECENTRALIZATION), "name": f"1.1.{REV_DECENTRALIZATION}"})
        prev_block, tx_results, main_prep_as_dict = self._make_and_req_block_for_prep_test([tx])
        self.assertIsNotNone(main_prep_as_dict)
        data: dict = {
            ConstantKeys.NAME: "name0",
            ConstantKeys.EMAIL: "email0",
            ConstantKeys.WEBSITE: "website0",
            ConstantKeys.DETAILS: "json0",
            ConstantKeys.P2P_END_POINT: "ip0",
            ConstantKeys.PUBLIC_KEY: f'publicKey0'.encode(),
        }

        expected_response: dict = data
        response: dict = self._get_prep(addr_array[0])
        register = response["registration"]

        self.assertEqual(expected_response[ConstantKeys.NAME], register[ConstantKeys.NAME])
        self.assertEqual(expected_response[ConstantKeys.EMAIL], register[ConstantKeys.EMAIL])
        self.assertEqual(expected_response[ConstantKeys.WEBSITE], register[ConstantKeys.WEBSITE])
        self.assertEqual(expected_response[ConstantKeys.DETAILS], register[ConstantKeys.DETAILS])
        self.assertEqual(expected_response[ConstantKeys.P2P_END_POINT], register[ConstantKeys.P2P_END_POINT])
        self.assertEqual(expected_response[ConstantKeys.PUBLIC_KEY], register[ConstantKeys.PUBLIC_KEY])
        self.assertEqual(IISS_INITIAL_IREP, register[ConstantKeys.IREP])

        for i in range(3):
            irep_set_data: dict = {
                ConstantKeys.IREP: hex(IISS_INITIAL_IREP),
            }
            tx = self._make_score_call_tx(addr_array[0],
                                          ZERO_SCORE_ADDRESS,
                                          'setPRep',
                                          irep_set_data)
            prev_block, tx_results = self._make_and_req_block([tx])
            self._write_precommit_state(prev_block)
            set_result = tx_results[0]
            self.assertEqual(set_result.status, 1)

        irep_value2 = int(IISS_INITIAL_IREP * 1.2)
        irep_set_data: dict = {
            ConstantKeys.IREP: hex(irep_value2),
        }
        tx = self._make_score_call_tx(addr_array[0],
                                      ZERO_SCORE_ADDRESS,
                                      'setPRep',
                                      irep_set_data)
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        set_result = tx_results[0]
        self.assertEqual(set_result.status, 1)

        irep_set_data[ConstantKeys.IREP] = hex(int(irep_value2*1.1))
        tx = self._make_score_call_tx(addr_array[0],
                                      ZERO_SCORE_ADDRESS,
                                      'setPRep',
                                      irep_set_data)
        prev_block, tx_results = self._make_and_req_block([tx])
        set_result = tx_results[0]
        failure_message = set_result.failure.message
        self.assertEqual(set_result.status, 0)
        self.assertEqual(failure_message, 'Can update irep only one time in term')
