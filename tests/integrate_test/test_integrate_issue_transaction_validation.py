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
from iconservice.base.exception import InvalidBlockException
from iconservice.icon_config import default_icon_config
from iconservice.icon_constant import ISSUE_CALCULATE_ORDER, ISSUE_EVENT_LOG_MAPPER, ConfigKey, REV_IISS, \
    IconScoreContextType, ISCORE_EXCHANGE_RATE
from iconservice.iconscore.icon_score_context import IconScoreContext
from iconservice.iiss.reward_calc.ipc.reward_calc_proxy import CalculateResponse
from tests import create_address
from tests.integrate_test.test_integrate_base import TestIntegrateBase


class TestIntegrateIssueTransactionValidation(TestIntegrateBase):
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

    def _make_dummy_tx(self):
        return self._make_icx_send_tx(self._genesis, create_address(), 1)

    def setUp(self):
        # same as fee treasury address constant value
        self._fee_treasury = Address.from_prefix_and_int(AddressPrefix.CONTRACT, 1)
        default_icon_config[ConfigKey.IREP] = 100_000_000_000
        super().setUp()
        self._update_governance()
        self._set_revision(REV_IISS)

        # todo: if get_issue_info is redundant, should fix this method
        context = IconScoreContext(IconScoreContextType.DIRECT)
        self.issue_data, self.total_issue_amount = IconScoreContext.engine.issue.create_icx_issue_info(context)

        # self.total_issue_amount = 0
        # for group_dict in self.issue_data.values():
        #     self.total_issue_amount += group_dict["value"]

    def test_validate_issue_transaction_position(self):
        # failure case: when first transaction is not a issue transaction, should raise error
        invalid_tx_list = [
            self._make_dummy_tx()
        ]
        self.assertRaises(InvalidBlockException, self._make_and_req_block_for_issue_test, invalid_tx_list)

        # failure case: when first transaction is not a issue transaction
        # but 2nd is a issue transaction, should raise error
        invalid_tx_list = [
            self._make_dummy_tx(),
            self._make_issue_tx(self.issue_data)
        ]
        self.assertRaises(InvalidBlockException, self._make_and_req_block_for_issue_test, invalid_tx_list)

        # failure case: if there are more than 2 issue transaction, should raise error
        invalid_tx_list = [
            self._make_issue_tx(self.issue_data),
            self._make_issue_tx(self.issue_data)
        ]
        self.assertRaises(InvalidBlockException, self._make_and_req_block_for_issue_test, invalid_tx_list)

        # failure case: when there is no issue transaction, should raise error
        invalid_tx_list = [
            self._make_dummy_tx(),
            self._make_dummy_tx(),
            self._make_dummy_tx()
        ]
        self.assertRaises(InvalidBlockException, self._make_and_req_block_for_issue_test, invalid_tx_list)

    def test_validate_issue_transaction_format(self):
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
            self.assertRaises(InvalidBlockException, self._make_and_req_block_for_issue_test, tx_list)
            copied_issue_data[group_key] = temp

        # more than
        copied_issue_data = deepcopy(self.issue_data)
        copied_issue_data['dummy_key'] = {}
        tx_list = [
            self._make_issue_tx(copied_issue_data),
            self._make_dummy_tx(),
            self._make_dummy_tx()
        ]
        self.assertRaises(InvalidBlockException, self._make_and_req_block_for_issue_test, tx_list)

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
            self.assertRaises(InvalidBlockException, self._make_and_req_block_for_issue_test, tx_list)
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
                self.assertRaises(InvalidBlockException, self._make_and_req_block_for_issue_test, tx_list)
                data[key] = temp

    def test_validate_issue_transaction_value(self):
        expected_step_price = 0
        expected_step_used = 0

        # success case: when valid issue transaction invoked, should issue icx according to calculated icx issue amount
        before_total_supply = self._query({}, "icx_getTotalSupply")
        before_treasury_icx_amount = self._query({"address": self._fee_treasury}, 'icx_getBalance')

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
            expected_indexed: list = ISSUE_EVENT_LOG_MAPPER[group_key]['indexed']
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

    def test_validate_issue_transaction_value_corrected_issue_amount(self):
        # success case: when iconservice over issued 10 icx than reward carc, icx issue amount
        # should be corrected on calc period.
        calc_period = 10
        check_point = calc_period + 9

        cumulative_fee = 10
        expected_issue_amount = 4642222
        calculate_response_iscore = 46422210000
        expected_diff_in_calc_period = (expected_issue_amount * calc_period) - \
                                       (calculate_response_iscore // ISCORE_EXCHANGE_RATE)

        def mock_calculate(self, path, block_height):
            response = CalculateResponse(0, True, 1, calculate_response_iscore, b'mocked_response')
            self._calculation_callback(response)

        tx_list = [
            self._make_dummy_tx(),
            self._make_dummy_tx()
        ]
        for x in range(0, 50):
            if x % 16 == 0:
                self._mock_ipc(mock_calculate)
            copyed_tx_list = deepcopy(tx_list)
            prev_block, tx_results = self._make_and_req_block_for_issue_test(copyed_tx_list,
                                                                             is_block_editable=True,
                                                                             cumulative_fee=cumulative_fee)
            issue_amount = tx_results[0].event_logs[0].data[3]
            actual_covered_by_fee = tx_results[0].event_logs[1].data[0]
            actual_covered_by_remain = tx_results[0].event_logs[1].data[1]
            actual_issue_amount = tx_results[0].event_logs[1].data[2]
            if x == 0:
                self.assertEqual(0, actual_covered_by_fee)
                self.assertEqual(0, actual_covered_by_remain)
                self.assertEqual(expected_issue_amount, actual_issue_amount)
                self.assertEqual(0, tx_results[0].event_logs[1].data[3])

            elif x == check_point:
                self.assertEqual(cumulative_fee, actual_covered_by_fee)
                self.assertEqual(expected_diff_in_calc_period, actual_covered_by_remain)
                self.assertEqual(expected_issue_amount - cumulative_fee - expected_diff_in_calc_period,
                                 actual_issue_amount)
                self.assertEqual(0, tx_results[0].event_logs[1].data[3])
                check_point += calc_period
            else:
                self.assertEqual(cumulative_fee, actual_covered_by_fee)
                self.assertEqual(0, actual_covered_by_remain)
                self.assertEqual(expected_issue_amount - cumulative_fee, actual_issue_amount)
                self.assertEqual(0, tx_results[0].event_logs[1].data[3])
            self.assertEqual(issue_amount, actual_covered_by_fee + actual_covered_by_remain + actual_issue_amount)

            self._write_precommit_state(prev_block)

