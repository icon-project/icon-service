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
from iconservice.base.exception import IconServiceBaseException, IllegalFormatException
from iconservice.icon_config import default_icon_config
from iconservice.icon_constant import ISSUE_CALCULATE_ORDER, ISSUE_EVENT_LOG_MAPPER, ConfigKey
from tests import create_address
from tests.integrate_test.test_integrate_base import TestIntegrateBase


class TestIntegrateIssueTransactionValidation(TestIntegrateBase):
    def _update_governance(self):
        tx = self._make_deploy_tx("test_builtin",
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
        default_icon_config[ConfigKey.GOVERNANCE_VARIABLE]["incentiveRep"] = 100_000_000
        super().setUp()
        self._update_governance()
        self._set_revision(5)

        # todo: if get_issue_info is redundant, should fix this method
        self.issue_data = self.icon_service_engine.query("iiss_get_issue_info", {})
        self.total_issue_amount = 0
        for group_dict in self.issue_data.values():
            self.total_issue_amount += group_dict["value"]

    def test_validate_issue_transaction_position(self):
        # failure case: when first transaction is not a issue transaction, should raise error
        invalid_tx_list = [
            self._make_dummy_tx()
        ]
        self.assertRaises(IconServiceBaseException, self._make_and_req_block, invalid_tx_list)

        # failure case: when first transaction is not a issue transaction
        # but 2nd is a issue transaction, should raise error
        invalid_tx_list = [
            self._make_dummy_tx(),
            self._make_issue_tx(self.issue_data)
        ]
        self.assertRaises(IconServiceBaseException, self._make_and_req_block, invalid_tx_list)

        # failure case: if there are more than 2 issue transaction, should raise error
        invalid_tx_list = [
            self._make_issue_tx(self.issue_data),
            self._make_issue_tx(self.issue_data)
        ]
        self.assertRaises(KeyError, self._make_and_req_block, invalid_tx_list)

        # failure case: when there is no issue transaction, should raise error
        invalid_tx_list = [
            self._make_dummy_tx(),
            self._make_dummy_tx(),
            self._make_dummy_tx()
        ]
        self.assertRaises(IconServiceBaseException, self._make_and_req_block, invalid_tx_list)

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
            self.assertRaises(IllegalFormatException, self._make_and_req_block, tx_list)
            copied_issue_data[group_key] = temp

        # more than
        copied_issue_data = deepcopy(self.issue_data)
        copied_issue_data['dummy_key'] = {}
        tx_list = [
            self._make_issue_tx(copied_issue_data),
            self._make_dummy_tx(),
            self._make_dummy_tx()
        ]
        self.assertRaises(IllegalFormatException, self._make_and_req_block, tx_list)

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
            self.assertRaises(IllegalFormatException, self._make_and_req_block, tx_list)
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
                self.assertRaises(IllegalFormatException, self._make_and_req_block, tx_list)
                data[key] = temp

    def test_validate_issue_transaction_value(self):
        # failure case: when group(i.e. prep, eep, dapp) key in the issue transaction's data is different with
        # stateDB, transaction result should be failure
        copied_issue_data = deepcopy(self.issue_data)
        invalid_value = 999999999999999999

        expected_tx_status = 0
        expected_failure_msg = 'Have difference between issue transaction and actual db data'
        expected_event_logs = []
        expected_step_price = 0
        expected_step_used = 0
        for group, data in copied_issue_data.items():
            for key in self.issue_data[group].keys():
                temp = data[key]
                data[key] = invalid_value
                tx_list = [
                    self._make_issue_tx(copied_issue_data),
                    self._make_dummy_tx(),
                    self._make_dummy_tx()
                ]
                _, tx_results = self._make_and_req_block(tx_list)
                self.assertEqual(expected_tx_status, tx_results[0].status)
                self.assertEqual(expected_failure_msg, tx_results[0].failure.message)
                self.assertEqual(expected_event_logs, tx_results[0].event_logs)
                self.assertEqual(expected_step_price, tx_results[0].step_price)
                self.assertEqual(expected_step_used, tx_results[0].step_used)
                data[key] = temp

        # success case: when valid issue transaction invoked, should issue icx according to calculated icx issue amount
        before_total_supply = self._query({}, "icx_getTotalSupply")
        before_treasury_icx_amount = self._query({"address": self._fee_treasury}, 'icx_getBalance')

        tx_list = [
            self._make_issue_tx(self.issue_data),
            self._make_dummy_tx(),
            self._make_dummy_tx()
        ]
        prev_block, tx_results = self._make_and_req_block(tx_list)
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
        self.assertEqual(0, tx_results[0].event_logs[1].data[2])
        self.assertEqual(self.total_issue_amount, tx_results[0].event_logs[1].data[3])
        after_total_supply = self._query({}, "icx_getTotalSupply")
        after_treasury_icx_amount = self._query({"address": self._fee_treasury}, 'icx_getBalance')

        self.assertEqual(before_total_supply + self.total_issue_amount, after_total_supply)
        self.assertEqual(before_treasury_icx_amount + self.total_issue_amount, after_treasury_icx_amount)
