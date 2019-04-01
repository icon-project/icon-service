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
from typing import Any

from iconcommons import IconConfig

from iconservice import ZERO_SCORE_ADDRESS
from iconservice.base.address import Address, AddressPrefix
from iconservice.base.exception import InvalidRequestException
from iconservice.icon_config import default_icon_config
from iconservice.icon_constant import ConfigKey
from iconservice.icon_service_engine import IconServiceEngine
from iconservice.iconscore.icon_score_result import TransactionResult
from tests.integrate_test import root_clear
from tests.integrate_test.test_integrate_base import TestIntegrateBase


class TestIntegrateFeeSharing(TestIntegrateBase):

    def setUp(self):
        super().setUp()
        root_clear(self._score_root_path, self._state_db_root_path)

        self._block_height = 0
        self._prev_block_hash = None

        config = IconConfig("", default_icon_config)
        config.load()
        config.update_conf({ConfigKey.BUILTIN_SCORE_OWNER: str(self._admin)})
        config.update_conf({ConfigKey.SERVICE: {ConfigKey.SERVICE_AUDIT: False,
                                                ConfigKey.SERVICE_FEE: True,
                                                ConfigKey.SERVICE_DEPLOYER_WHITE_LIST: False,
                                                ConfigKey.SERVICE_SCORE_PACKAGE_VALIDATOR: False}})
        config.update_conf({ConfigKey.SCORE_ROOT_PATH: self._score_root_path,
                            ConfigKey.STATE_DB_ROOT_PATH: self._state_db_root_path})
        config.update_conf(self._make_init_config())

        self.icon_service_engine = IconServiceEngine()
        self.icon_service_engine.open(config)

        self._genesis_invoke()

        deploy_tx_hash = self._deploy_score('install/test_score', 0, self._admin)
        self.assertEqual(deploy_tx_hash.status, int(True))
        self.score_address = deploy_tx_hash.score_address

    def tearDown(self):
        super().tearDown()

    def _deploy_score(self, score_path: str,
                      value: int,
                      from_address: 'Address') -> Any:
        address = ZERO_SCORE_ADDRESS

        tx = self._make_deploy_tx("test_deploy_scores",
                                  score_path,
                                  from_address,
                                  address,
                                  deploy_params={'value': hex(value)})

        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        return tx_results[0]

    # noinspection PyDefaultArgument
    def _query_request(self, method: str, params: dict = {}):
        query_request = {
            "version": self._version,
            "from": self._admin,
            "to": ZERO_SCORE_ADDRESS,
            "dataType": "call",
            "data": {
                "method": method,
                "params": params
            }
        }
        response = self._query(query_request)
        return response

    def _set_ratio(self, score_address: Address, ratio: int, sender: Address = None) -> TransactionResult:
        if sender is None:
            sender = self._admin
        set_ratio_tx_hash = self._make_score_call_tx(sender, ZERO_SCORE_ADDRESS, 'setRatio',
                                                     {"_score": str(score_address), "_ratio": hex(ratio)})
        prev_block, tx_results = self._make_and_req_block([set_ratio_tx_hash])
        self._write_precommit_state(prev_block)
        return tx_results[0]

    def _deposit_icx(self, score_address: Address, amount: int, period: int,
                     sender: Address = None) -> TransactionResult:
        if sender is None:
            sender = self._admin
        deposit_req = self._make_score_call_tx(sender, ZERO_SCORE_ADDRESS, "createDeposit",
                                               {"_score": str(score_address),
                                                "_amount": hex(amount), "_period": hex(period)})
        prev_block, tx_results = self._make_and_req_block([deposit_req])
        self._write_precommit_state(prev_block)
        return tx_results[0]

    def test_get_ratio(self):
        # tx_hash = deploy_tx_hash.tx_hash
        fee_sharing_ratio = self._query_request("getFeeShare", {"_score": str(self.score_address)})

        self.assertEqual(fee_sharing_ratio, 0)

    def test_set_ratio(self):
        for i in range(-50, 151, 50):
            set_ratio_tx_result = self._set_ratio(self.score_address, i)
            if i > 100 or i < 0:
                self.assertEqual(set_ratio_tx_result.status, 0)
                continue
            self.assertEqual(set_ratio_tx_result.status, 1)
            fee_sharing_ratio = self._query_request("getFeeShare", {"_score": str(self.score_address)})
            self.assertEqual(fee_sharing_ratio, i)

    def test_deposit_fee(self):
        deposit_tx_result = self._deposit_icx(self.score_address, 5000 * 10 ** 18, 1_296_000)

        deposit_id = deposit_tx_result.tx_hash
        deposit_info = self._query_request('getDeposit', {"_id": f"0x{bytes.hex(deposit_id)}"})
        self.assertTrue(deposit_info)

    def test_deposit_fee_icx_range(self):
        deposit_tx_result = self._deposit_icx(self.score_address, 100_001 * 10 ** 18, 1_296_000)
        self.assertFalse(deposit_tx_result.status)

        deposit_tx_result = self._deposit_icx(self.score_address, 4999 * 10 ** 18, 1_296_000)
        self.assertFalse(deposit_tx_result.status)

    def test_deposit_fee_period_range(self):
        deposit_tx_result = self._deposit_icx(self.score_address, 5000 * 10 ** 18, 31_104_001)
        self.assertFalse(deposit_tx_result.status)

        deposit_tx_result = self._deposit_icx(self.score_address, 5000 * 10 ** 18, 1_295_999)
        self.assertFalse(deposit_tx_result.status)

    def test_invoke_insufficient_score(self):
        set_ratio_tx_result = self._set_ratio(self.score_address, 100)
        self.assertEqual(set_ratio_tx_result.status, 1)

        with self.assertRaises(InvalidRequestException) as e:
            self._make_score_call_tx(self._admin, self.score_address, 'set_value',
                                     {"value": hex(100)})
        self.assertEqual(e.exception.message, "Step limit too low")

    def test_sharing_fee_case_score_0(self):
        user_balance = self._query({"address": self._admin}, "icx_getBalance")
        initial_available_depost = self._query_request('getScoreInfo', {"_score": str(self.score_address)})[
            'availableDeposit']

        score_call_tx = self._make_score_call_tx(self._admin, self.score_address, 'set_value', {"value": hex(100)})
        prev_block, tx_results = self._make_and_req_block([score_call_tx])
        self._write_precommit_state(prev_block)

        fee_used = tx_results[0].step_used * tx_results[0].step_price

        after_call_user_balance = self._query({"address": self._admin}, "icx_getBalance")
        after_call_available_depost = self._query_request('getScoreInfo', {"_score": str(self.score_address)})[
            'availableDeposit']
        self.assertEqual(user_balance - fee_used, after_call_user_balance)
        self.assertEqual(initial_available_depost, after_call_available_depost)
        self.assertFalse(tx_results[0].to_dict().get('detailed_step_used'))

    def test_sharing_fee_case_score_50(self):
        # set ratio
        set_ratio_tx_result = self._set_ratio(self.score_address, 50)
        self.assertEqual(set_ratio_tx_result.status, 1)
        # deposit icx
        deposit_tx_result = self._deposit_icx(self.score_address, 15000 * 10 ** 18, 1_296_000)
        self.assertEqual(deposit_tx_result.status, 1)
        user_balance = self._query({"address": self._admin}, "icx_getBalance")
        initial_available_deposit = self._query_request('getScoreInfo', {"_score": str(self.score_address)})[
            'availableDeposit']

        # invoke score method
        score_call_tx = self._make_score_call_tx(self._admin, self.score_address, 'set_value', {"value": hex(100)})
        prev_block, tx_results = self._make_and_req_block([score_call_tx])
        self._write_precommit_state(prev_block)

        # check result
        after_call_available_depost = self._query_request('getScoreInfo', {"_score": str(self.score_address)})[
            'availableDeposit']
        user_used_fee = tx_results[0].detail_step_used[self._admin] * tx_results[0].step_price
        score_used_fee = tx_results[0].detail_step_used[self.score_address] * tx_results[0].step_price
        after_call_user_balance = self._query({"address": self._admin}, "icx_getBalance")

        self.assertEqual(initial_available_deposit - score_used_fee, after_call_available_depost)
        self.assertEqual(user_balance - user_used_fee, after_call_user_balance)

    def test_sharing_fee_case_score_100(self):
        # set ratio
        set_ratio_tx_result = self._set_ratio(self.score_address, 100)
        self.assertEqual(set_ratio_tx_result.status, 1)
        # deposit icx
        deposit_tx_result = self._deposit_icx(self.score_address, 15000 * 10 ** 18, 1_296_000)
        self.assertEqual(deposit_tx_result.status, 1)
        user_balance = self._query({"address": self._admin}, "icx_getBalance")
        initial_available_deposit = self._query_request('getScoreInfo', {"_score": str(self.score_address)})[
            'availableDeposit']

        # invoke score method
        score_call_tx = self._make_score_call_tx(self._admin, self.score_address, 'set_value', {"value": hex(100)})
        prev_block, tx_results = self._make_and_req_block([score_call_tx])
        self._write_precommit_state(prev_block)

        # check result
        after_call_available_deposit = self._query_request('getScoreInfo', {"_score": str(self.score_address)})[
            'availableDeposit']
        score_used_fee = tx_results[0].detail_step_used[self.score_address] * tx_results[0].step_price
        after_call_user_balance = self._query({"address": self._admin}, "icx_getBalance")
        self.assertEqual(initial_available_deposit - score_used_fee, after_call_available_deposit)
        self.assertEqual(user_balance, after_call_user_balance)
        self.assertFalse(tx_results[0].detail_step_used.get(self._admin))

    def test_score_call_after_deposit_expired(self):
        # change min_deposit_period
        self.icon_service_engine._fee_engine._MIN_DEPOSIT_PERIOD = 1
        # set ratio
        set_ratio_tx_result = self._set_ratio(self.score_address, 100)
        self.assertEqual(set_ratio_tx_result.status, 1)
        # deposit icx
        deposit_tx_result = self._deposit_icx(self.score_address, 15000 * 10 ** 18, 1)
        self.assertEqual(deposit_tx_result.status, 1)
        initial_available_deposit = self._query_request('getScoreInfo', {"_score": str(self.score_address)})[
            'availableDeposit']
        self.assertNotEqual(initial_available_deposit, 0)

        # increase block_height
        send_icx_tx = self._make_icx_send_tx(self._genesis, self._addr_array[0], 10 ** 18)
        prev_block, tx_results = self._make_and_req_block([send_icx_tx])
        self._write_precommit_state(prev_block)

        # invoke score method
        with self.assertRaises(InvalidRequestException) as e:
            self._make_score_call_tx(self._admin, self.score_address, 'set_value', {"value": hex(100)})
        self.assertEqual(e.exception.message, "Step limit too low")

        # check result
        after_destroyed_available_deposit = self._query_request('getScoreInfo', {"_score": str(self.score_address)})[
            'availableDeposit']
        self.assertEqual(after_destroyed_available_deposit, 0)

    def test_deposit_unauthorized_account(self):
        # give icx to tester
        send_icx_tx = self._make_icx_send_tx(self._genesis, self._addr_array[0], 10000 * 10 ** 18)
        prev_block, tx_results = self._make_and_req_block([send_icx_tx])
        self._write_precommit_state(prev_block)

        # unauthorized account deposit 5000icx in SCORE
        set_ratio_tx_result = self._deposit_icx(self.score_address, 5000 * 10 ** 18, 1296000, self._addr_array[0])

        self.assertEqual(set_ratio_tx_result.status, 0)
        self.assertTrue(set_ratio_tx_result.failure)

    def test_deposit_nonexistent_score(self):
        # give icx to tester
        send_icx_tx = self._make_icx_send_tx(self._genesis, self._addr_array[0], 10000 * 10 ** 18)
        prev_block, tx_results = self._make_and_req_block([send_icx_tx])
        self._write_precommit_state(prev_block)

        # deposit icx in nonexistent SCORE
        set_ratio_tx_result = self._deposit_icx(Address.from_prefix_and_int(AddressPrefix.CONTRACT, 3), 5000 * 10 ** 18,
                                                1296000)

        self.assertEqual(set_ratio_tx_result.status, 0)
        self.assertTrue(set_ratio_tx_result.failure)

    def test_set_ratio_unauthorized_account(self):
        # give icx to tester
        send_icx_tx = self._make_icx_send_tx(self._genesis, self._addr_array[0], 10000 * 10 ** 18)
        prev_block, tx_results = self._make_and_req_block([send_icx_tx])
        self._write_precommit_state(prev_block)

        # unauthorized account try to set ratio
        set_ratio_tx_result = self._set_ratio(self.score_address, 100, self._addr_array[0])

        self.assertEqual(set_ratio_tx_result.status, 0)
        self.assertTrue(set_ratio_tx_result.failure)

    def test_set_ratio_nonexistent_score(self):
        # give icx to tester
        send_icx_tx = self._make_icx_send_tx(self._genesis, self._addr_array[0], 10000 * 10 ** 18)
        prev_block, tx_results = self._make_and_req_block([send_icx_tx])
        self._write_precommit_state(prev_block)

        # set ratio for nonexistent score
        set_ratio_tx_result = self._deposit_icx(Address.from_prefix_and_int(AddressPrefix.CONTRACT, 3), 5000 * 10 ** 18,
                                                1296000)

        self.assertEqual(set_ratio_tx_result.status, 0)
        self.assertTrue(set_ratio_tx_result.failure)
