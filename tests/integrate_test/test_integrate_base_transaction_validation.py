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

"""IconScoreEngine testcase
"""
from copy import deepcopy

from iconservice.base.address import ZERO_SCORE_ADDRESS, Address, AddressPrefix, GOVERNANCE_SCORE_ADDRESS
from iconservice.base.block import Block
from iconservice.base.exception import InvalidBaseTransactionException
from iconservice.base.type_converter_templates import ConstantKeys
from iconservice.icon_config import default_icon_config
from iconservice.icon_constant import ISSUE_CALCULATE_ORDER, ISSUE_EVENT_LOG_MAPPER, REV_IISS, \
    IconScoreContextType, ISCORE_EXCHANGE_RATE, REV_DECENTRALIZATION, ICX_IN_LOOP, ConfigKey
from iconservice.iconscore.icon_score_context import IconScoreContext
from iconservice.icx.issue.regulator import Regulator
from iconservice.iiss.reward_calc.ipc.reward_calc_proxy import CalculateResponse
from iconservice.prep.data import PRepFlag
from tests import create_address, create_block_hash
from tests.integrate_test import create_timestamp
from tests.integrate_test.test_integrate_base import TestIntegrateBase


class TestIntegrateBaseTransactionValidation(TestIntegrateBase):
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

    def _decentralize(self, main_preps: list, delegate_amount: int):

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
        for i, address in enumerate(main_preps):
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
            } for address in main_preps[:10]]
        self._delegate(addr1, data)

        data: list = [
            {
                "address": str(address),
                "value": hex(delegate_amount)
            } for address in main_preps[10:20]]
        self._delegate(addr2, data)

        data: list = [
            {
                "address": str(address),
                "value": hex(delegate_amount)
            } for address in main_preps[20:22]]
        self._delegate(addr3, data)

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

    def _make_dummy_tx(self):
        return self._make_icx_send_tx(self._genesis, create_address(), 1)

    def _create_base_transaction(self):
        context = IconScoreContext(IconScoreContextType.DIRECT)
        context.preps: 'PRepContainer' = context.engine.prep.preps.copy(PRepFlag.NONE)
        issue_data, total_issue_amount = context.engine.issue.create_icx_issue_info(context)
        block_height: int = self._block_height
        block_hash = create_block_hash()
        timestamp_us = create_timestamp()
        block = Block(block_height, block_hash, timestamp_us, self._prev_block_hash, 0)
        context.block = block
        regulator = Regulator()
        regulator.set_corrected_issue_data(context, total_issue_amount)

        issue_data["result"] = {
            "coveredByFee": regulator.covered_icx_by_fee,
            "coveredByOverIssuedICX": regulator.covered_icx_by_over_issue,
            "issue": regulator.corrected_icx_issue_amount
        }

        return self.icon_service_engine.formatting_transaction("base", issue_data, context.block.timestamp)

    def _set_prep(self, address: 'Address', data: dict, _revision: int = REV_IISS):

        data = deepcopy(data)
        value = data.get(ConstantKeys.IREP)
        if value:
            data[ConstantKeys.IREP] = hex(value)

        tx = self._make_score_call_tx(address, ZERO_SCORE_ADDRESS, 'setPRep', data)
        prev_block, tx_results = self._make_and_req_block([tx])

        tx_result: 'TransactionResult' = tx_results[0]

        self.assertEqual(1, tx_result.status)
        self.assertEqual('PRepSet(Address)', tx_result.event_logs[0].indexed[0])
        self.assertEqual(address, tx_result.event_logs[0].data[0])
        self._write_precommit_state(prev_block)

    def setUp(self):
        _PREPS_LEN = 30
        _MAIN_PREPS_LEN = 22
        _AMOUNT_DELEGATE = 10000
        _MINIMUM_DELEGATE_AMOUNT = 10 ** 18
        # same as fee treasury address constant value
        self._fee_treasury = Address.from_prefix_and_int(AddressPrefix.CONTRACT, 1)
        default_icon_config[ConfigKey.IISS_CALCULATE_PERIOD] = 10
        default_icon_config[ConfigKey.TERM_PERIOD] = 10
        super().setUp()
        self._update_governance()
        self._set_revision(REV_IISS)

        addr_array = [create_address() for _ in range(_PREPS_LEN)]

        total_supply = 800_460_000 * ICX_IN_LOOP

        # Minimum_delegate_amount is 0.02 * total_supply
        # In this test delegate 0.03*total_supply because `Issue transaction` exists since REV_IISS
        delegate_amount = total_supply * 2 // 1000

        # generate preps
        self._decentralize(addr_array, delegate_amount)

        response = self._get_prep_list()
        total_delegated: int = response['totalDelegated']
        prep_list: list = response['preps']

        self.assertEqual(delegate_amount * 22, total_delegated)
        self.assertEqual(_PREPS_LEN, len(prep_list))
        #
        # for prep in addr_array:
        #     update_data: dict = {
        #         ConstantKeys.IREP: 30_000 * ICX_IN_LOOP
        #     }
        #     self._set_prep(prep, update_data)

        self._set_revision(REV_DECENTRALIZATION)

        # todo: if get_issue_info is redundant, should fix this method
        context = IconScoreContext(IconScoreContextType.DIRECT)
        context.preps: 'PRepContainer' = context.engine.prep.preps.copy(PRepFlag.NONE)

        self.issue_data, self.total_issue_amount = IconScoreContext.engine.issue.create_icx_issue_info(context)
        # self.total_issue_amount = 0
        # for group_dict in self.issue_data.values():
        #     self.total_issue_amount += group_dict["value"]

    def test_validate_base_transaction_position(self):
        # isBlockEditable is false in this method

        # failure case: when first transaction is not a issue transaction, should raise error
        invalid_tx_list = [
            self._make_dummy_tx()
        ]
        self.assertRaises(InvalidBaseTransactionException, self._make_and_req_block_for_issue_test, invalid_tx_list)

        # failure case: when first transaction is not a issue transaction
        # but 2nd is a issue transaction, should raise error
        invalid_tx_list = [
            self._make_dummy_tx(),
            self._make_issue_tx(self.issue_data)
        ]
        self.assertRaises(InvalidBaseTransactionException, self._make_and_req_block_for_issue_test, invalid_tx_list)

        # failure case: if there are more than 2 issue transaction, should raise error
        invalid_tx_list = [
            self._make_issue_tx(self.issue_data),
            self._make_issue_tx(self.issue_data)
        ]
        self.assertRaises(InvalidBaseTransactionException, self._make_and_req_block_for_issue_test, invalid_tx_list)

        # failure case: when there is no issue transaction, should raise error
        invalid_tx_list = [
            self._make_dummy_tx(),
            self._make_dummy_tx(),
            self._make_dummy_tx()
        ]
        self.assertRaises(InvalidBaseTransactionException, self._make_and_req_block_for_issue_test, invalid_tx_list)

    def test_validate_base_transaction_format(self):
        # isBlockEditable is false in this method

        # failure case: when group(i.e. prep, eep, dapp) key in the issue transaction's data is different with
        # stateDB, should raise error

        # less than
        copied_issue_data = deepcopy(self.issue_data)
        for group_key in self.issue_data.keys():
            temp = copied_issue_data[group_key]
            del copied_issue_data[group_key]
            tx_list = [
                self._make_issue_tx(copied_issue_data),
                self._make_dummy_tx(),
                self._make_dummy_tx()
            ]
            self.assertRaises(InvalidBaseTransactionException, self._make_and_req_block_for_issue_test, tx_list)
            copied_issue_data[group_key] = temp

        # more than
        copied_issue_data = deepcopy(self.issue_data)
        copied_issue_data['dummy_key'] = {}
        tx_list = [
            self._make_issue_tx(copied_issue_data),
            self._make_dummy_tx(),
            self._make_dummy_tx()
        ]
        self.assertRaises(InvalidBaseTransactionException, self._make_and_req_block_for_issue_test, tx_list)

        # failure case: when group's inner data key (i.e. incentiveRep, rewardRep, etc) is different
        # with stateDB (except value), should raise error

        # more than
        copied_issue_data = deepcopy(self.issue_data)
        for _, data in copied_issue_data.items():
            data['dummy_key'] = ""
            tx_list = [
                self._make_issue_tx(copied_issue_data),
                self._make_dummy_tx(),
                self._make_dummy_tx()
            ]
            self.assertRaises(InvalidBaseTransactionException, self._make_and_req_block_for_issue_test, tx_list)
            del data['dummy_key']

        # less than
        copied_issue_data = deepcopy(self.issue_data)
        for group, data in copied_issue_data.items():
            for key in self.issue_data[group].keys():
                temp = data[key]
                del data[key]
                tx_list = [
                    self._make_issue_tx(copied_issue_data),
                    self._make_dummy_tx(),
                    self._make_dummy_tx()
                ]
                self.assertRaises(InvalidBaseTransactionException, self._make_and_req_block_for_issue_test, tx_list)
                data[key] = temp

    def test_validate_base_transaction_value_editable_block(self):
        expected_step_price = 0
        expected_step_used = 0

        # failure case: when issue transaction invoked even though isBlockEditable is true, should raise error
        # case of isBlockEditable is True
        before_total_supply = self._query({}, "icx_getTotalSupply")
        before_treasury_icx_amount = self._query({"address": self._fee_treasury}, 'icx_getBalance')

        base_transaction = self._create_base_transaction()

        tx_list = [
            base_transaction,
            self._make_dummy_tx(),
            self._make_dummy_tx()
        ]
        self.assertRaises(KeyError,
                          self._make_and_req_block_for_issue_test,
                          tx_list, None, None, None, True, 0)

        # success case: when valid issue transaction invoked, should issue icx according to calculated icx issue amount
        # case of isBlockEditable is True
        tx_list = [
            self._make_dummy_tx(),
            self._make_dummy_tx()
        ]
        prev_block, tx_results = self._make_and_req_block_for_issue_test(tx_list, is_block_editable=True)
        self._write_precommit_state(prev_block)
        expected_tx_status = 1
        expected_failure = None
        expected_trace = []
        self.assertEqual(expected_tx_status, tx_results[0].status)
        self.assertEqual(expected_failure, tx_results[0].failure)
        self.assertEqual(expected_step_price, tx_results[0].step_price)
        self.assertEqual(expected_step_used, tx_results[0].step_used)
        self.assertEqual(expected_trace, tx_results[0].traces)

        for index, group_key in enumerate(ISSUE_CALCULATE_ORDER):
            if group_key not in self.issue_data:
                continue
            expected_score_address = ZERO_SCORE_ADDRESS
            expected_indexed: list = [ISSUE_EVENT_LOG_MAPPER[group_key]['event_signature']]
            expected_data: list = [self.issue_data[group_key][key] for key in ISSUE_EVENT_LOG_MAPPER[group_key]['data']]
            self.assertEqual(expected_score_address, tx_results[0].event_logs[index].score_address)
            self.assertEqual(expected_indexed, tx_results[0].event_logs[index].indexed)
            self.assertEqual(expected_data, tx_results[0].event_logs[index].data)

        # event log about correction
        self.assertEqual(0, tx_results[0].event_logs[1].data[0])
        self.assertEqual(0, tx_results[0].event_logs[1].data[1])
        self.assertEqual(self.total_issue_amount, tx_results[0].event_logs[1].data[2])
        self.assertEqual(0, tx_results[0].event_logs[1].data[3])

        after_total_supply = self._query({}, "icx_getTotalSupply")
        after_treasury_icx_amount = self._query({"address": self._fee_treasury}, 'icx_getBalance')

        self.assertEqual(before_total_supply + self.total_issue_amount, after_total_supply)
        self.assertEqual(before_treasury_icx_amount + self.total_issue_amount, after_treasury_icx_amount)

    def test_validate_base_transaction_value_not_editable_block(self):
        expected_step_price = 0
        expected_step_used = 0

        # success case: when valid issue transaction invoked, should issue icx according to calculated icx issue amount
        # case of isBlockEditable is False
        before_total_supply = self._query({}, "icx_getTotalSupply")
        before_treasury_icx_amount = self._query({"address": self._fee_treasury}, 'icx_getBalance')
        base_transaction = self._create_base_transaction()

        tx_list = [
            base_transaction,
            self._make_dummy_tx(),
            self._make_dummy_tx()
        ]
        prev_block, tx_results = self._make_and_req_block_for_issue_test(tx_list, is_block_editable=False)
        self._write_precommit_state(prev_block)
        expected_tx_status = 1
        expected_failure = None
        expected_trace = []
        self.assertEqual(expected_tx_status, tx_results[0].status)
        self.assertEqual(expected_failure, tx_results[0].failure)
        self.assertEqual(expected_step_price, tx_results[0].step_price)
        self.assertEqual(expected_step_used, tx_results[0].step_used)
        self.assertEqual(expected_trace, tx_results[0].traces)

        for index, group_key in enumerate(ISSUE_CALCULATE_ORDER):
            if group_key not in self.issue_data:
                continue
            expected_score_address = ZERO_SCORE_ADDRESS
            expected_indexed: list = [ISSUE_EVENT_LOG_MAPPER[group_key]['event_signature']]
            expected_data: list = [self.issue_data[group_key][key] for key in ISSUE_EVENT_LOG_MAPPER[group_key]['data']]
            self.assertEqual(expected_score_address, tx_results[0].event_logs[index].score_address)
            self.assertEqual(expected_indexed, tx_results[0].event_logs[index].indexed)
            self.assertEqual(expected_data, tx_results[0].event_logs[index].data)

        # event log about correction
        self.assertEqual(0, tx_results[0].event_logs[1].data[0])
        self.assertEqual(0, tx_results[0].event_logs[1].data[1])
        self.assertEqual(self.total_issue_amount, tx_results[0].event_logs[1].data[2])
        self.assertEqual(0, tx_results[0].event_logs[1].data[3])

        after_total_supply = self._query({}, "icx_getTotalSupply")
        after_treasury_icx_amount = self._query({"address": self._fee_treasury}, 'icx_getBalance')

        self.assertEqual(before_total_supply + self.total_issue_amount, after_total_supply)
        self.assertEqual(before_treasury_icx_amount + self.total_issue_amount, after_treasury_icx_amount)

    def test_validate_base_transaction_value_corrected_issue_amount(self):
        # success case: when icon service over issued 10 icx than reward carc, icx issue amount
        # should be corrected on calc period.
        calc_period = 10
        calc_point = calc_period
        expected_sequence = 0

        diff_between_is_and_rc = 10 * ISCORE_EXCHANGE_RATE
        cumulative_fee = 10
        first_expected_issue_amount = 2589195129375951183
        calculate_response_iscore = \
            first_expected_issue_amount * calc_period * ISCORE_EXCHANGE_RATE - diff_between_is_and_rc

        expected_issue_amount = 2561944563165905521
        calculate_response_iscore_after_first_period = \
            expected_issue_amount * 10 * ISCORE_EXCHANGE_RATE - diff_between_is_and_rc
        expected_diff_in_calc_period = (expected_issue_amount * calc_period) - \
                                       (calculate_response_iscore_after_first_period // ISCORE_EXCHANGE_RATE)

        def mock_calculated(_self, _path, _block_height):
            response = CalculateResponse(0, True, 1, calculate_response_iscore, b'mocked_response')
            _self._calculation_callback(response)

        self._mock_ipc(mock_calculated)

        tx_list = [
            self._make_dummy_tx(),
            self._make_dummy_tx()
        ]
        for x in range(1, 11):

            copied_tx_list = deepcopy(tx_list)
            prev_block, tx_results = self._make_and_req_block_for_issue_test(copied_tx_list,
                                                                             is_block_editable=True,
                                                                             cumulative_fee=cumulative_fee)
            issue_amount = tx_results[0].event_logs[0].data[3]
            actual_covered_by_fee = tx_results[0].event_logs[1].data[0]
            actual_covered_by_remain = tx_results[0].event_logs[1].data[1]
            actual_issue_amount = tx_results[0].event_logs[1].data[2]
            print(f"=================={x}====================")
            print(tx_results[0].event_logs[0].data)
            print(tx_results[0].event_logs[1].data)
            if x == 1:
                self.assertEqual(0, actual_covered_by_fee)
                self.assertEqual(0, actual_covered_by_remain)
                self.assertEqual(first_expected_issue_amount, actual_issue_amount)
                self.assertEqual(0, tx_results[0].event_logs[1].data[3])

                actual_sequence = tx_results[0].event_logs[2].data[0]
                actual_start_block = tx_results[0].event_logs[2].data[1]
                actual_end_block = tx_results[0].event_logs[2].data[2]
                self.assertEqual(expected_sequence, actual_sequence)
                self.assertEqual(prev_block._height, actual_start_block)
                self.assertEqual(prev_block._height + calc_period - 1, actual_end_block)
                expected_sequence += 1
            elif x == calc_point:
                calc_point += calc_period
            else:
                self.assertEqual(cumulative_fee, actual_covered_by_fee)
                self.assertEqual(0, actual_covered_by_remain)
                self.assertEqual(first_expected_issue_amount - cumulative_fee, actual_issue_amount)
                self.assertEqual(0, tx_results[0].event_logs[1].data[3])
            self.assertEqual(issue_amount, actual_covered_by_fee + actual_covered_by_remain + actual_issue_amount)
            self._write_precommit_state(prev_block)

        calculate_response_iscore = calculate_response_iscore_after_first_period

        for x in range(11, 51):
            copied_tx_list = deepcopy(tx_list)
            prev_block, tx_results = self._make_and_req_block_for_issue_test(copied_tx_list,
                                                                             is_block_editable=True,
                                                                             cumulative_fee=cumulative_fee)
            issue_amount = tx_results[0].event_logs[0].data[3]
            actual_covered_by_fee = tx_results[0].event_logs[1].data[0]
            actual_covered_by_remain = tx_results[0].event_logs[1].data[1]
            actual_issue_amount = tx_results[0].event_logs[1].data[2]
            print(f"=================={x}====================")
            print(tx_results[0].event_logs[0].data)
            print(tx_results[0].event_logs[1].data)
            if x == calc_point:
                self.assertEqual(cumulative_fee, actual_covered_by_fee)
                self.assertEqual(expected_diff_in_calc_period, actual_covered_by_remain)
                self.assertEqual(expected_issue_amount - cumulative_fee - expected_diff_in_calc_period,
                                 actual_issue_amount)
                self.assertEqual(0, tx_results[0].event_logs[1].data[3])
                calc_point += calc_period
            elif x == calc_point - calc_period + 1:
                actual_sequence = tx_results[0].event_logs[2].data[0]
                actual_start_block = tx_results[0].event_logs[2].data[1]
                actual_end_block = tx_results[0].event_logs[2].data[2]
                self.assertEqual(expected_sequence, actual_sequence)
                self.assertEqual(prev_block._height, actual_start_block)
                self.assertEqual(prev_block._height + calc_period - 1, actual_end_block)
                expected_sequence += 1
            else:
                self.assertEqual(cumulative_fee, actual_covered_by_fee)
                self.assertEqual(0, actual_covered_by_remain)
                self.assertEqual(expected_issue_amount - cumulative_fee, actual_issue_amount)
                self.assertEqual(0, tx_results[0].event_logs[1].data[3])
            self.assertEqual(issue_amount, actual_covered_by_fee + actual_covered_by_remain + actual_issue_amount)

            self._write_precommit_state(prev_block)
