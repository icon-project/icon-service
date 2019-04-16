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
from iconservice.fee.fee_engine import FeeEngine
from iconservice.icon_config import default_icon_config
from iconservice.icon_constant import ConfigKey
from iconservice.icon_service_engine import IconServiceEngine
from iconservice.iconscore.icon_score_result import TransactionResult
from tests import create_tx_hash
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

        deploy_tx_hash = self._deploy_score('install/test_score_fee_sharing', 0, self._admin, {"value": hex(100)})
        self.assertEqual(deploy_tx_hash.status, int(True))
        self.score_address = deploy_tx_hash.score_address

        deploy_tx_hash2 = self._deploy_score('install/test_score_fee_sharing_inter_call', 0, self._admin,
                                             {"value": hex(100), "score_address": str(self.score_address)})
        self.assertEqual(deploy_tx_hash2.status, int(True))
        self.score_address2 = deploy_tx_hash2.score_address

    def tearDown(self):
        super().tearDown()

    def _deploy_score(self, score_path: str,
                      value: int,
                      from_address: 'Address',
                      deploy_params: dict) -> Any:
        address = ZERO_SCORE_ADDRESS

        tx = self._make_deploy_tx("test_deploy_scores",
                                  score_path,
                                  from_address,
                                  address, deploy_params)

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

    def _deposit_icx(self, score_address: Address, amount: int, period: int,
                     sender: Address = None) -> TransactionResult:
        if sender is None:
            sender = self._admin
        deposit_req = self._make_score_call_tx(sender, ZERO_SCORE_ADDRESS, "addDeposit",
                                               {"score": str(score_address),
                                                "amount": hex(amount), "term": hex(period)})
        prev_block, tx_results = self._make_and_req_block([deposit_req])
        self._write_precommit_state(prev_block)
        return tx_results[0]

    def _withdraw_deposit(self, deposit_id: bytes, sender: Address = None) -> TransactionResult:
        if sender is None:
            sender = self._admin
        withdraw_tx_hash = self._make_score_call_tx(sender, ZERO_SCORE_ADDRESS, "withdrawDeposit",
                                                    {"depositId": f"0x{bytes.hex(deposit_id)}"})
        prev_block, tx_results = self._make_and_req_block([withdraw_tx_hash])
        self._write_precommit_state(prev_block)
        return tx_results[0]

    def test_deposit_fee(self):
        deposit_tx_result = self._deposit_icx(self.score_address, 5000 * 10 ** 18, 1_296_000)

        deposit_id = deposit_tx_result.tx_hash
        deposit_info = self._query_request('getDeposit', {"depositId": f"0x{bytes.hex(deposit_id)}"})
        self.assertTrue(deposit_info)

    def test_deposit_fee_icx_range(self):
        deposit_tx_result = self._deposit_icx(self.score_address, 100_001 * 10 ** 18, 1_296_000)
        self.assertFalse(deposit_tx_result.status)

        deposit_tx_result = self._deposit_icx(self.score_address, 4999 * 10 ** 18, 1_296_000)
        self.assertFalse(deposit_tx_result.status)

    def test_deposit_fee_term_range(self):
        deposit_tx_result = self._deposit_icx(self.score_address, 5000 * 10 ** 18, 31_104_001)
        self.assertFalse(deposit_tx_result.status)

        deposit_tx_result = self._deposit_icx(self.score_address, 5000 * 10 ** 18, 1_295_999)
        self.assertFalse(deposit_tx_result.status)

    def test_sharing_fee_case_score_0(self):
        user_balance = self._query({"address": self._admin}, "icx_getBalance")
        initial_available_depost = self._query_request('getDepositList', {"score": str(self.score_address)})[
            'availableDeposit']

        score_call_tx = self._make_score_call_tx(self._admin, self.score_address, 'set_value', {"value": hex(100)})
        prev_block, tx_results = self._make_and_req_block([score_call_tx])
        self._write_precommit_state(prev_block)

        fee_used = tx_results[0].step_used * tx_results[0].step_price

        after_call_user_balance = self._query({"address": self._admin}, "icx_getBalance")
        after_call_available_depost = self._query_request('getDepositList', {"score": str(self.score_address)})[
            'availableDeposit']
        self.assertEqual(user_balance - fee_used, after_call_user_balance)
        self.assertEqual(initial_available_depost, after_call_available_depost)
        self.assertFalse(tx_results[0].to_dict().get('detailed_step_used'))

    def test_sharing_fee_case_score_50(self):
        # deposit icx
        deposit_tx_result = self._deposit_icx(self.score_address, 15000 * 10 ** 18, 1_296_000)
        self.assertEqual(deposit_tx_result.status, 1)
        user_balance = self._query({"address": self._admin}, "icx_getBalance")
        initial_available_deposit = self._query_request('getDepositList', {"score": str(self.score_address)})[
            'availableDeposit']
        proportion = 50

        # invoke score method
        score_call_tx = self._make_score_call_tx(self._admin, self.score_address, 'set_value', {"value": hex(100),
                                                                                                "proportion": hex(proportion)})
        prev_block, tx_results = self._make_and_req_block([score_call_tx])
        self._write_precommit_state(prev_block)

        # check result
        after_call_available_deposit = self._query_request('getDepositList', {"score": str(self.score_address)})[
            'availableDeposit']
        user_used_fee = tx_results[0].step_used_details[self._admin] * tx_results[0].step_price
        score_used_fee = tx_results[0].step_used_details[self.score_address] * tx_results[0].step_price
        after_call_user_balance = self._query({"address": self._admin}, "icx_getBalance")

        self.assertEqual(initial_available_deposit - score_used_fee, after_call_available_deposit)
        self.assertEqual(user_balance - user_used_fee, after_call_user_balance)
        self.assertEqual(score_used_fee, user_used_fee)

    def test_sharing_fee_case_score_100(self):
        # deposit icx
        deposit_tx_result = self._deposit_icx(self.score_address, 15000 * 10 ** 18, 1_296_000)
        self.assertEqual(deposit_tx_result.status, 1)
        user_balance = self._query({"address": self._admin}, "icx_getBalance")
        initial_available_deposit = self._query_request('getDepositList', {"score": str(self.score_address)})[
            'availableDeposit']

        # invoke score method
        score_call_tx = self._make_score_call_tx(self._admin, self.score_address, 'set_value', {"value": hex(100),
                                                                                                "proportion": hex(100)})
        prev_block, tx_results = self._make_and_req_block([score_call_tx])
        self._write_precommit_state(prev_block)

        # check result
        after_call_available_deposit = self._query_request('getDepositList', {"score": str(self.score_address)})[
            'availableDeposit']
        score_used_fee = tx_results[0].step_used_details[self.score_address] * tx_results[0].step_price
        after_call_user_balance = self._query({"address": self._admin}, "icx_getBalance")
        self.assertEqual(initial_available_deposit - score_used_fee, after_call_available_deposit)
        self.assertEqual(user_balance, after_call_user_balance)
        self.assertFalse(tx_results[0].step_used_details.get(self._admin))

    def test_score_call_after_deposit_expired(self):
        # change min_deposit_term
        self.icon_service_engine._fee_engine._MIN_DEPOSIT_TERM = 1
        # deposit icx
        deposit_tx_result = self._deposit_icx(self.score_address, 15000 * 10 ** 18, 1)
        self.assertEqual(deposit_tx_result.status, 1)
        initial_available_deposit = self._query_request('getDepositList', {"score": str(self.score_address)})[
            'availableDeposit']
        self.assertNotEqual(initial_available_deposit, 0)

        # increase block_height
        send_icx_tx = self._make_icx_send_tx(self._genesis, self._addr_array[0], 10 ** 18)
        prev_block, tx_results = self._make_and_req_block([send_icx_tx])
        self._write_precommit_state(prev_block)

        # invoke score method
        with self.assertRaises(InvalidRequestException) as e:
            self._make_score_call_tx(self._admin, self.score_address, 'set_value',
                                     {"value": hex(100), "proportion": hex(100)})
        self.assertEqual(e.exception.message, "SCORE can not share fee")

        # check result
        after_destroyed_available_deposit = self._query_request('getDepositList', {"score": str(self.score_address)})[
            'availableDeposit']
        self.assertEqual(after_destroyed_available_deposit, 0)

    def test_deposit_unauthorized_account(self):
        # give icx to tester
        send_icx_tx = self._make_icx_send_tx(self._genesis, self._addr_array[0], 10000 * 10 ** 18)
        prev_block, tx_results = self._make_and_req_block([send_icx_tx])
        self._write_precommit_state(prev_block)

        # unauthorized account deposit 5000icx in SCORE
        set_proportion_tx_result = self._deposit_icx(self.score_address, 5000 * 10 ** 18, 1296000, self._addr_array[0])

        self.assertEqual(set_proportion_tx_result.status, 0)
        self.assertTrue(set_proportion_tx_result.failure)

    def test_deposit_nonexistent_score(self):
        # give icx to tester
        send_icx_tx = self._make_icx_send_tx(self._genesis, self._addr_array[0], 10000 * 10 ** 18)
        prev_block, tx_results = self._make_and_req_block([send_icx_tx])
        self._write_precommit_state(prev_block)

        # deposit icx in nonexistent SCORE
        set_proportion_tx_result = self._deposit_icx(Address.from_prefix_and_int(AddressPrefix.CONTRACT, 3),
                                                     5000 * 10 ** 18, 1296000)

        self.assertEqual(set_proportion_tx_result.status, 0)
        self.assertTrue(set_proportion_tx_result.failure)

    def test_get_score_info_without_deposit(self):
        """
        Given : The SCORE is deployed.
        When  : The SCORE does not have any deposit yet.
        Then  : There is not no deposit list
                and all of values like sharing proportion, available virtual step and available deposit is 0.
        """
        score_info = self._query_request("getDepositList", {"score": str(self.score_address)})
        self.assertEqual(score_info["scoreAddress"], self.score_address)
        self.assertEqual(score_info["deposits"], [])
        self.assertEqual(score_info["availableVirtualStep"], 0)
        self.assertEqual(score_info["availableDeposit"], 0)

    def test_get_score_info_with_deposits(self):
        """
        Given : The SCORE is deployed.
        When  : The SCORE has one or two deposits.
        Then  : Checks if values like sharing proportion, available virtual step and available deposit is correct.
        """
        amount_deposit = 5000 * 10 ** 18

        # Creates a deposit with 5000 ICX
        deposit_tx_result = self._deposit_icx(self.score_address, amount_deposit, 1_296_000)
        deposit_id1 = deposit_tx_result.tx_hash

        score_info = self._query_request("getDepositList", {"score": str(self.score_address)})
        self.assertEqual(score_info["scoreAddress"], self.score_address)
        self.assertEqual(deposit_id1, score_info["deposits"][0].id)
        self.assertEqual(len(score_info["deposits"]), 1)
        self.assertEqual(score_info["availableVirtualStep"], 0)
        self.assertEqual(score_info["availableDeposit"], amount_deposit * 90 // 100)

        # Creates a more deposit with 5000 * 2 ICX
        deposit_tx_result = self._deposit_icx(self.score_address, amount_deposit * 2, 1_296_000)
        deposit_id2 = deposit_tx_result.tx_hash

        score_info = self._query_request("getDepositList", {"score": str(self.score_address)})
        self.assertEqual(score_info["scoreAddress"], self.score_address)
        self.assertEqual(deposit_id1, score_info["deposits"][0].id)
        self.assertEqual(deposit_id2, score_info["deposits"][1].id)
        self.assertEqual(len(score_info["deposits"]), 2)
        self.assertEqual(score_info["availableVirtualStep"], 0)

        sum_of_available_deposit = 0
        for i in range(len(score_info["deposits"])):
            sum_of_available_deposit += score_info["deposits"][i].deposit_amount * 90 // 100
        self.assertEqual(score_info["availableDeposit"], sum_of_available_deposit)

    def test_add_multiple_deposits(self):
        """
        Given : The SCORE is deployed.
        When  : The SCORE has multiple deposits.
        Then  : Checks if SCORE has multiple deposits without any problem.
        """
        amount_deposit = FeeEngine._MIN_DEPOSIT_AMOUNT

        # Creates more deposit with 5000000 ICX
        for _ in range(100):
            _ = self._deposit_icx(self.score_address, amount_deposit, 1_296_000)

        score_info = self._query_request("getDepositList", {"score": str(self.score_address)})
        self.assertEqual(len(score_info["deposits"]), 100)
        self.assertEqual(score_info["availableDeposit"],
                         amount_deposit * 100 - amount_deposit * 10 // 100 * len(score_info['deposits']))

    def test_get_deposit_by_valid_id(self):
        """
        Given : The SCORE is deployed.
        When  : Tries to get deposit info by valid id.
        Then  : Returns deposit info correctly.
        """
        deposit_tx_result = self._deposit_icx(self.score_address, 5000 * 10 ** 18, 1_296_000)
        deposit_id = deposit_tx_result.tx_hash

        deposit_info = self._query_request('getDeposit', {"depositId": f"0x{bytes.hex(deposit_id)}"})
        self.assertTrue(deposit_info)

    def test_get_deposit_by_invalid_id(self):
        """
        Given : The SCORE is deployed.
        When  : Ties to get deposit info by invalid id.
        Then  : Raises exception(InvalidRequestException) before and after making a deposit.
        """
        # Before making a deposit, getting deposit with invalid ID failed.
        self.assertRaises(InvalidRequestException, self._query_request, 'getDeposit',
                          {"depositId": f"0x{bytes.hex(create_tx_hash())}"})

        deposit_tx_result = self._deposit_icx(self.score_address, 5000 * 10 ** 18, 1_296_000)
        deposit_id = deposit_tx_result.tx_hash

        deposit_info = self._query_request('getDeposit', {"depositId": f"0x{bytes.hex(deposit_id)}"})
        self.assertTrue(deposit_info)

        # After making a deposit, getting deposit with invalid ID failed, too.
        self.assertRaises(InvalidRequestException, self._query_request, 'getDeposit',
                          {"depositId": f"0x{bytes.hex(create_tx_hash())}"})

    def test_withdraw_deposit_after_deposit(self):
        """
        Given : The SCORE is deployed and deposit once.
        When  : Withdraws the deposit.
        Then  : Amount of availableDeposit is 0.
        """
        deposit_tx_result = self._deposit_icx(self.score_address, 5000 * 10 ** 18, 1_296_000)
        deposit_id = deposit_tx_result.tx_hash

        deposit_info = self._query_request('getDeposit', {"depositId": f"0x{bytes.hex(deposit_id)}"})
        self.assertTrue(deposit_info)

        withdraw_tx_result = self._withdraw_deposit(deposit_id)
        self.assertTrue(withdraw_tx_result.status)

        score_info = self._query_request("getDepositList", {"score": str(self.score_address)})
        self.assertEqual(len(score_info["deposits"]), 0)
        self.assertEqual(score_info["availableDeposit"], 0)

    def test_withdraw_deposit_after_charging_fee(self):
        """
        Given : The SCORE is deployed and deposit once. After setting proportion of SCORE, it happens to charge fee.
        When  : Withdraws the deposit.
        Then  : Return the left deposit after charging fee.
        """
        # deposit icx
        deposit_tx_result = self._deposit_icx(self.score_address, 5000 * 10 ** 18, 1_296_000)
        deposit_id = deposit_tx_result.tx_hash
        self.assertEqual(deposit_tx_result.status, 1)

        # invoke score method
        score_call_tx = self._make_score_call_tx(self._admin, self.score_address, 'set_value', {"value": hex(100),
                                                                                                "proportion": hex(100)})
        prev_block, tx_results = self._make_and_req_block([score_call_tx])
        self._write_precommit_state(prev_block)

        # check result
        available_deposit_after_call = self._query_request('getDepositList', {"score": str(self.score_address)})[
            'availableDeposit']

        user_balance_before_withdraw = self._query({"address": self._admin}, "icx_getBalance")

        # withdraw
        withdraw_tx_result = self._withdraw_deposit(deposit_id)
        self.assertTrue(withdraw_tx_result.status)

        user_balance_after_withdraw = self._query({"address": self._admin}, "icx_getBalance")

        score_info = self._query_request("getDepositList", {"score": str(self.score_address)})
        self.assertEqual(len(score_info["deposits"]), 0)
        self.assertEqual(score_info["availableDeposit"], 0)

        # check the owner balance
        validate_user_balance = user_balance_before_withdraw + available_deposit_after_call + 500 * 10 ** 18 - withdraw_tx_result.step_used * withdraw_tx_result.step_price
        self.assertEqual(user_balance_after_withdraw, validate_user_balance)

    def test_withdraw_deposit_by_not_owner(self):
        """
        Given : The SCORE is deployed and deposit.
        When  : Try to withdraw by not owner.
        Then  : Return tx result with failure and status is 0.
        """
        # deposit icx
        deposit_tx_result = self._deposit_icx(self.score_address, 5000 * 10 ** 18, 1_296_000)
        deposit_id = deposit_tx_result.tx_hash
        self.assertEqual(deposit_tx_result.status, 1)

        # withdraw by not owner
        withdraw_tx_result = self._withdraw_deposit(deposit_id, self._genesis)
        self.assertFalse(withdraw_tx_result.status)
        self.assertEqual(withdraw_tx_result.failure.message, "Invalid sender")

    def test_withdraw_deposit_again_after_already_withdraw_one(self):
        """
        Given : The SCORE is deployed and deposit. Sets proportion.
        When  : Withdraws twice from same deposit.
        Then  : Return tx result with failure and status is 0.
        """
        # deposit icx
        deposit_tx_result = self._deposit_icx(self.score_address, 5000 * 10 ** 18, 1_296_000)
        deposit_id = deposit_tx_result.tx_hash
        self.assertEqual(deposit_tx_result.status, 1)

        # withdraw
        withdraw_tx_result = self._withdraw_deposit(deposit_id)
        self.assertTrue(withdraw_tx_result.status)

        score_info = self._query_request("getDepositList", {"score": str(self.score_address)})
        self.assertEqual(len(score_info["deposits"]), 0)

        # withdraw again
        withdraw_tx_result = self._withdraw_deposit(deposit_id)
        self.assertFalse(withdraw_tx_result.status)
        self.assertEqual(withdraw_tx_result.failure.message, "Deposit info not found")

    def test_inter_call_fee_sharing_proportion100(self):
        # deposit icx
        deposit_tx_result = self._deposit_icx(self.score_address2, 15000 * 10 ** 18, 1_296_000)
        self.assertEqual(deposit_tx_result.status, 1)
        user_balance = self._query({"address": self._admin}, "icx_getBalance")
        initial_available_deposit = self._query_request('getDepositList', {"score": str(self.score_address2)})[
            'availableDeposit']

        # invoke score method
        score_call_tx = self._make_score_call_tx(self._admin, self.score_address2, 'set_other_score_value',
                                                 {"value": hex(100),
                                                  "proportion": hex(100), "other_score_proportion": hex(0)})
        prev_block, tx_results = self._make_and_req_block([score_call_tx])
        self._write_precommit_state(prev_block)

        # check result
        after_call_available_deposit = self._query_request('getDepositList', {"score": str(self.score_address2)})[
            'availableDeposit']
        score_used_fee = tx_results[0].step_used_details[self.score_address2] * tx_results[0].step_price
        after_call_user_balance = self._query({"address": self._admin}, "icx_getBalance")
        self.assertEqual(initial_available_deposit - score_used_fee, after_call_available_deposit)
        self.assertEqual(user_balance, after_call_user_balance)
        self.assertFalse(tx_results[0].step_used_details.get(self._admin))
        self.assertFalse(tx_results[0].step_used_details.get(self.score_address))

    # TODO Add tests for pre-validate
