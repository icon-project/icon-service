# -*- coding: utf-8 -*-

import unittest
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
from typing import Any, Optional

from iconcommons import IconConfig

from iconservice import ZERO_SCORE_ADDRESS
from iconservice.base.address import Address, AddressPrefix, GOVERNANCE_SCORE_ADDRESS
from iconservice.base.exception import InvalidRequestException
from iconservice.fee import FeeEngine
from iconservice.fee.engine import FIXED_TERM
from iconservice.icon_config import default_icon_config
from iconservice.icon_constant import ConfigKey, REV_IISS
from iconservice.icon_service_engine import IconServiceEngine
from iconservice.iconscore.icon_score_result import TransactionResult
from tests import create_tx_hash
from tests.integrate_test import root_clear, create_timestamp
from tests.integrate_test.test_integrate_base import TestIntegrateBase, DEFAULT_BIG_STEP_LIMIT

STEP_PRICE = 10 ** 10

MAX_DEPOSIT_AMOUNT = FeeEngine._MAX_DEPOSIT_AMOUNT
MIN_DEPOSIT_AMOUNT = FeeEngine._MIN_DEPOSIT_AMOUNT
MAX_DEPOSIT_TERM = FeeEngine._MAX_DEPOSIT_TERM
MIN_DEPOSIT_TERM = FeeEngine._MIN_DEPOSIT_TERM


class TestIntegrateFeeSharing(TestIntegrateBase):
    def update_governance(self):
        tx = self._make_deploy_tx("sample_builtin",
                                  "latest_version/governance",
                                  self._admin,
                                  GOVERNANCE_SCORE_ADDRESS)
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)

    def setUp(self):
        root_clear(self._score_root_path, self._state_db_root_path, self._iiss_db_root_path)

        self._block_height = -1
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

        self._mock_ipc()

        self.icon_service_engine = IconServiceEngine()
        self.icon_service_engine.open(config)

        self._genesis_invoke()

        governance_tx_result = self._update_governance(self._admin)
        self.assertEqual(governance_tx_result.status, int(True))

        deploy_tx_hash = self._deploy_score('install/sample_score_fee_sharing', 0, self._admin, {"value": hex(100)})
        self.assertEqual(deploy_tx_hash.status, int(True))
        self.score_address = deploy_tx_hash.score_address

        deploy_tx_hash2 = self._deploy_score('install/sample_score_fee_sharing_inter_call', 0, self._admin,
                                             {"value": hex(100), "score_address": str(self.score_address)})
        self.assertEqual(deploy_tx_hash2.status, int(True))
        self.score_address2 = deploy_tx_hash2.score_address

    def tearDown(self):
        super().tearDown()

    def _update_governance(self, from_address: 'Address') -> Any:
        tx = self._make_deploy_tx("sample_builtin",
                                  "governance_for_fee2/governance",
                                  from_address,
                                  GOVERNANCE_SCORE_ADDRESS)
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        return tx_results[0]

    def _deploy_score(self, score_path: str,
                      value: int,
                      from_address: 'Address',
                      deploy_params: dict) -> Any:
        address = ZERO_SCORE_ADDRESS

        tx = self._make_deploy_tx("sample_deploy_scores",
                                  score_path,
                                  from_address,
                                  address, deploy_params)

        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        return tx_results[0]

    # noinspection PyDefaultArgument
    def _query_score_info(self, address: Address):
        query_request = {
            "version": self._version,
            "from": self._admin,
            "to": GOVERNANCE_SCORE_ADDRESS,
            "dataType": "call",
            "data": {
                "method": "getScoreStatus",
                "params": {
                    "address": str(address)
                }
            }
        }
        response = self._query(query_request)
        return response

    def _make_deposit_tx(self,
                         addr_from: Optional['Address'],
                         addr_to: 'Address',
                         action: str,
                         params: dict,
                         value: int = 0,
                         pre_validation_enabled: bool = True,
                         step_limit: int = DEFAULT_BIG_STEP_LIMIT):

        timestamp_us = create_timestamp()
        nonce = 0

        request_params = {
            "version": self._version,
            "from": addr_from,
            "to": addr_to,
            "value": value,
            "stepLimit": step_limit,
            "timestamp": timestamp_us,
            "nonce": nonce,
            "signature": self._signature,
            "dataType": "deposit",
            "data": {
                "action": action,
            }
        }

        for k, v in params.items():
            request_params["data"][k] = v

        method = 'icx_sendTransaction'
        # Insert txHash into request params
        request_params['txHash'] = create_tx_hash()
        tx = {
            'method': method,
            'params': request_params
        }

        if pre_validation_enabled:
            self.icon_service_engine.validate_transaction(tx)

        return tx

    def _deposit_icx(self, score_address: Address, amount: int, period: int,
                     sender: Address = None) -> TransactionResult:
        if sender is None:
            sender = self._admin
        if FIXED_TERM:
            deposit_req = self._make_deposit_tx(sender, score_address, "add", {})
        else:
            deposit_req = self._make_deposit_tx(sender, score_address, "add", {"term": hex(period)})
        deposit_req['params']['value'] = amount
        prev_block, tx_results = self._make_and_req_block([deposit_req])
        self._write_precommit_state(prev_block)
        return tx_results[0]

    def _withdraw_deposit(self, deposit_id: bytes, score_address: Address,
                          sender: Address = None) -> TransactionResult:
        if sender is None:
            sender = self._admin
        withdraw_tx_hash = self._make_deposit_tx(sender, score_address, "withdraw",
                                                 {"id": f"0x{bytes.hex(deposit_id)}"})
        prev_block, tx_results = self._make_and_req_block([withdraw_tx_hash])
        self._write_precommit_state(prev_block)
        return tx_results[0]

    def test_deposit_fee(self):
        before_balance = self._query({"address": self._admin}, "icx_getBalance")
        deposit_tx_result = self._deposit_icx(self.score_address, MIN_DEPOSIT_AMOUNT, MIN_DEPOSIT_TERM)
        deposit_fee = deposit_tx_result.step_price * deposit_tx_result.step_used

        deposit_id = deposit_tx_result.tx_hash
        score_info = self._query_score_info(self.score_address)
        self.assertIn('depositInfo', score_info)
        self.assertIn(deposit_id, map(lambda d: d['id'], score_info['depositInfo']['deposits']))
        after_balance = self._query({"address": self._admin}, "icx_getBalance")

        self.assertEqual(before_balance - MIN_DEPOSIT_AMOUNT - deposit_fee, after_balance)

    def test_deposit_fee_eventlog(self):
        self.update_governance()
        # success case: before IISS_REV revision, should charge fee about event log
        deposit_tx_result = self._deposit_icx(self.score_address, MIN_DEPOSIT_AMOUNT, MIN_DEPOSIT_TERM)

        step_used_before_iiss_rev = deposit_tx_result.step_used
        tx = self._make_score_call_tx(self._admin,
                                      GOVERNANCE_SCORE_ADDRESS,
                                      'setRevision',
                                      {
                                          "code": hex(REV_IISS),
                                          "name": f"1.1.{REV_IISS}"
                                      })

        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)

        deposit_tx_result = self._deposit_icx(self.score_address, MIN_DEPOSIT_AMOUNT, MIN_DEPOSIT_TERM)

        step_used_after_iiss_rev = deposit_tx_result.step_used

        self.assertTrue(step_used_before_iiss_rev > step_used_after_iiss_rev)

    def test_deposit_fee_icx_range(self):
        deposit_tx_result = self._deposit_icx(self.score_address,
                                              MAX_DEPOSIT_AMOUNT, MIN_DEPOSIT_TERM)
        self.assertTrue(deposit_tx_result.status)
        deposit_tx_result = self._deposit_icx(self.score_address,
                                              MAX_DEPOSIT_AMOUNT + 1, MIN_DEPOSIT_TERM)
        self.assertFalse(deposit_tx_result.status)

        deposit_tx_result = self._deposit_icx(self.score_address,
                                              MIN_DEPOSIT_AMOUNT, MIN_DEPOSIT_TERM)
        self.assertTrue(deposit_tx_result.status)
        deposit_tx_result = self._deposit_icx(self.score_address,
                                              MIN_DEPOSIT_AMOUNT - 1, MIN_DEPOSIT_TERM)
        self.assertFalse(deposit_tx_result.status)

    def test_deposit_fee_term_range(self):
        deposit_tx_result = self._deposit_icx(self.score_address,
                                              MIN_DEPOSIT_AMOUNT, MAX_DEPOSIT_TERM)
        self.assertTrue(deposit_tx_result.status)
        # deposit_tx_result = self._deposit_icx(self.score_address,
        #                                       MIN_DEPOSIT_AMOUNT, MAX_DEPOSIT_TERM + 1)
        # self.assertFalse(deposit_tx_result.status)

        deposit_tx_result = self._deposit_icx(self.score_address,
                                              MIN_DEPOSIT_AMOUNT, MIN_DEPOSIT_TERM)
        self.assertTrue(deposit_tx_result.status)
        # deposit_tx_result = self._deposit_icx(self.score_address,
        #                                       MIN_DEPOSIT_AMOUNT, MIN_DEPOSIT_TERM - 1)
        # self.assertFalse(deposit_tx_result.status)

    def test_sharing_fee_case_score_0(self):
        # deposit icx
        deposit_tx_result = self._deposit_icx(self.score_address, 3 * MIN_DEPOSIT_AMOUNT, MIN_DEPOSIT_TERM)
        self.assertEqual(deposit_tx_result.status, 1)
        user_balance = self._query({"address": self._admin}, "icx_getBalance")
        score_info = self._query_score_info(self.score_address)
        self.assertIn('depositInfo', score_info)
        deposit_info = score_info['depositInfo']
        initial_available_deposit = deposit_info['availableDeposit']

        score_call_tx = self._make_score_call_tx(self._admin, self.score_address, 'set_value', {"value": hex(100)})
        prev_block, tx_results = self._make_and_req_block([score_call_tx])
        self._write_precommit_state(prev_block)

        fee_used = tx_results[0].step_used * tx_results[0].step_price

        after_call_user_balance = self._query({"address": self._admin}, "icx_getBalance")

        score_info = self._query_score_info(self.score_address)
        self.assertIn('depositInfo', score_info)
        deposit_info = score_info['depositInfo']
        after_call_available_deposit = deposit_info['availableDeposit']
        self.assertEqual(user_balance - fee_used, after_call_user_balance)
        self.assertEqual(initial_available_deposit, after_call_available_deposit)
        self.assertFalse(tx_results[0].to_dict().get('detailed_step_used'))

    def test_sharing_fee_case_score_50(self):
        # deposit icx
        deposit_tx_result = self._deposit_icx(self.score_address, 3 * MIN_DEPOSIT_AMOUNT, MIN_DEPOSIT_TERM)
        self.assertEqual(deposit_tx_result.status, 1)
        user_balance = self._query({"address": self._admin}, "icx_getBalance")

        score_info = self._query_score_info(self.score_address)
        self.assertIn('depositInfo', score_info)
        deposit_info = score_info['depositInfo']
        initial_available_deposit = deposit_info['availableDeposit']
        initial_available_virtual_step = deposit_info['availableVirtualStep']
        proportion = 50

        # invoke score method
        score_call_tx = self._make_score_call_tx(self._admin, self.score_address, 'set_value',
                                                 {"value": hex(100), "proportion": hex(proportion)})
        prev_block, tx_results = self._make_and_req_block([score_call_tx])
        self._write_precommit_state(prev_block)

        # check result
        score_info = self._query_score_info(self.score_address)
        self.assertIn('depositInfo', score_info)
        deposit_info = score_info['depositInfo']
        after_call_available_deposit = deposit_info['availableDeposit']
        user_used_fee = tx_results[0].step_used_details[self._admin] * tx_results[0].step_price
        score_used_fee = tx_results[0].step_used_details[self.score_address] * tx_results[0].step_price
        after_call_user_balance = self._query({"address": self._admin}, "icx_getBalance")
        remaining_step = score_used_fee - initial_available_virtual_step * STEP_PRICE
        remaining_step = 0 if remaining_step <= 0 else remaining_step
        self.assertEqual(initial_available_deposit - remaining_step, after_call_available_deposit)
        self.assertEqual(user_balance - user_used_fee, after_call_user_balance)
        self.assertEqual(score_used_fee, user_used_fee)

    def test_sharing_fee_case_score_100(self):
        # deposit icx
        deposit_tx_result = self._deposit_icx(self.score_address, 3 * MIN_DEPOSIT_AMOUNT, MIN_DEPOSIT_TERM)
        self.assertEqual(deposit_tx_result.status, 1)
        user_balance = self._query({"address": self._admin}, "icx_getBalance")

        score_info = self._query_score_info(self.score_address)
        self.assertIn('depositInfo', score_info)
        deposit_info = score_info['depositInfo']
        initial_available_deposit = deposit_info['availableDeposit']
        initial_available_virtual_step = deposit_info['availableVirtualStep']

        # invoke score method
        score_call_tx = self._make_score_call_tx(self._admin, self.score_address, 'set_value',
                                                 {"value": hex(100), "proportion": hex(100)})
        prev_block, tx_results = self._make_and_req_block([score_call_tx])
        self._write_precommit_state(prev_block)

        # check result
        score_info = self._query_score_info(self.score_address)
        self.assertIn('depositInfo', score_info)
        deposit_info = score_info['depositInfo']
        after_call_available_deposit = deposit_info['availableDeposit']
        score_used_fee = tx_results[0].step_used_details[self.score_address] * tx_results[0].step_price
        after_call_user_balance = self._query({"address": self._admin}, "icx_getBalance")
        remaining_step = score_used_fee - initial_available_virtual_step * STEP_PRICE
        remaining_step = 0 if remaining_step <= 0 else remaining_step
        self.assertEqual(initial_available_deposit - remaining_step, after_call_available_deposit)
        self.assertEqual(user_balance, after_call_user_balance)
        self.assertFalse(tx_results[0].step_used_details.get(self._admin))

    @unittest.skip("Will take over 8 minutes")
    def test_score_call_after_deposit_expired(self):
        # deposit icx
        deposit_tx_result = self._deposit_icx(self.score_address, 3 * MIN_DEPOSIT_AMOUNT, 1)
        self.assertEqual(deposit_tx_result.status, 1)

        score_info = self._query_score_info(self.score_address)
        self.assertIn('depositInfo', score_info)
        deposit_info = score_info['depositInfo']
        initial_available_deposit = deposit_info['availableDeposit']
        self.assertGreater(initial_available_deposit, 0)

        # increase block_height
        for i in range(MIN_DEPOSIT_TERM):
            send_icx_tx = self._make_icx_send_tx(self._genesis, self._addr_array[0], 10 ** 8)
            prev_block, tx_results = self._make_and_req_block([send_icx_tx])
            self._write_precommit_state(prev_block)

        # invoke score method
        with self.assertRaises(InvalidRequestException) as e:
            self._make_score_call_tx(self._admin, self.score_address, 'set_value',
                                     {"value": hex(100), "proportion": hex(100)})
        self.assertEqual(e.exception.message, "Out of deposit balance")

        # check result
        score_info = self._query_score_info(self.score_address)
        self.assertIn('depositInfo', score_info)
        deposit_info = score_info['depositInfo']
        after_destroyed_available_deposit = deposit_info['availableDeposit']
        self.assertEqual(after_destroyed_available_deposit, 0)

    def test_deposit_unauthorized_account(self):
        # give icx to tester
        send_icx_tx = self._make_icx_send_tx(self._genesis, self._addr_array[0], 10000 * 10 ** 18)
        prev_block, tx_results = self._make_and_req_block([send_icx_tx])
        self._write_precommit_state(prev_block)

        # unauthorized account deposit 5000icx in SCORE
        set_proportion_tx_result = self._deposit_icx(self.score_address, MIN_DEPOSIT_AMOUNT, MIN_DEPOSIT_TERM,
                                                     self._addr_array[0])

        self.assertEqual(set_proportion_tx_result.status, 0)
        self.assertTrue(set_proportion_tx_result.failure)

    def test_deposit_nonexistent_score(self):
        # give icx to tester
        send_icx_tx = self._make_icx_send_tx(self._genesis, self._addr_array[0], 10000 * 10 ** 18)
        prev_block, tx_results = self._make_and_req_block([send_icx_tx])
        self._write_precommit_state(prev_block)

        # deposit icx in nonexistent SCORE
        with self.assertRaises(InvalidRequestException) as e:
            self._deposit_icx(Address.from_prefix_and_int(AddressPrefix.CONTRACT, 3),
                              MIN_DEPOSIT_AMOUNT, MIN_DEPOSIT_TERM)

    def test_get_score_info_without_deposit(self):
        """
        Given : The SCORE is deployed.
        When  : The SCORE does not have any deposit yet.
        Then  : There is not no deposit list
                and all of values like sharing proportion, available virtual step and available deposit is 0.
        """
        score_info = self._query_score_info(self.score_address)
        self.assertNotIn('depositInfo', score_info)

    def test_get_score_info_with_deposits(self):
        """
        Given : The SCORE is deployed.
        When  : The SCORE has one or two deposits.
        Then  : Checks if values like sharing proportion, available virtual step and available deposit is correct.
        """
        amount_deposit = 5000 * 10 ** 18
        virtual_step_issuance1 = 40_000_000_000
        virtual_step_issuance2 = 80_000_000_000

        # Creates a deposit with 5000 ICX
        deposit_tx_result = self._deposit_icx(self.score_address, amount_deposit, MIN_DEPOSIT_TERM)
        deposit_id1 = deposit_tx_result.tx_hash

        score_info = self._query_score_info(self.score_address)
        self.assertIn('depositInfo', score_info)
        deposit_info = score_info['depositInfo']
        self.assertEqual(deposit_info["scoreAddress"], self.score_address)
        self.assertEqual(deposit_id1, deposit_info["deposits"][0]['id'])
        self.assertEqual(len(deposit_info["deposits"]), 1)
        self.assertEqual(deposit_info["availableVirtualStep"], virtual_step_issuance1)
        self.assertEqual(deposit_info["availableDeposit"], amount_deposit * 90 // 100)

        # Creates a more deposit with 5000 * 2 ICX
        deposit_tx_result = self._deposit_icx(self.score_address, amount_deposit * 2, MIN_DEPOSIT_TERM)
        deposit_id2 = deposit_tx_result.tx_hash

        score_info = self._query_score_info(self.score_address)
        self.assertIn('depositInfo', score_info)
        deposit_info = score_info['depositInfo']
        self.assertEqual(deposit_info["scoreAddress"], self.score_address)
        self.assertEqual(deposit_id1, deposit_info["deposits"][0]['id'])
        self.assertEqual(deposit_id2, deposit_info["deposits"][1]['id'])
        self.assertEqual(len(deposit_info["deposits"]), 2)
        self.assertEqual(deposit_info["availableVirtualStep"], virtual_step_issuance1 + virtual_step_issuance2)

        sum_of_available_deposit = 0
        for i in range(len(deposit_info["deposits"])):
            sum_of_available_deposit += deposit_info["deposits"][i]['depositAmount'] * 90 // 100
        self.assertEqual(deposit_info["availableDeposit"], sum_of_available_deposit)

    def test_add_multiple_deposits(self):
        """
        Given : The SCORE is deployed.
        When  : The SCORE has multiple deposits.
        Then  : Checks if SCORE has multiple deposits without any problem.
        """
        amount_deposit = MIN_DEPOSIT_AMOUNT

        # Creates more deposit with 5000000 ICX
        for _ in range(99):
            _ = self._deposit_icx(self.score_address, amount_deposit, MIN_DEPOSIT_TERM)

        score_info = self._query_score_info(self.score_address)
        self.assertIn('depositInfo', score_info)

        deposit_info = score_info['depositInfo']
        self.assertEqual(len(deposit_info["deposits"]), 99)
        self.assertEqual(deposit_info["availableDeposit"],
                         (amount_deposit - amount_deposit * 10 // 100) * len(deposit_info['deposits']))

    def test_get_deposit_by_valid_id(self):
        """
        Given : The SCORE is deployed.
        When  : Tries to get deposit info by valid id.
        Then  : Returns deposit info correctly.
        """
        deposit_tx_result = self._deposit_icx(self.score_address, MIN_DEPOSIT_AMOUNT, MIN_DEPOSIT_TERM)
        deposit_id = deposit_tx_result.tx_hash

        score_info = self._query_score_info(self.score_address)
        self.assertIn('depositInfo', score_info)
        self.assertIn(deposit_id, map(lambda d: d['id'], score_info['depositInfo']['deposits']))

    def test_withdraw_deposit_after_deposit(self):
        """
        Given : The SCORE is deployed and deposit once.
        When  : Withdraws the deposit.
        Then  : Amount of availableDeposit is 0.
        """
        deposit_tx_result = self._deposit_icx(self.score_address, MIN_DEPOSIT_AMOUNT, MIN_DEPOSIT_TERM)
        deposit_id = deposit_tx_result.tx_hash

        score_info = self._query_score_info(self.score_address)
        self.assertIn('depositInfo', score_info)
        self.assertIn(deposit_id, map(lambda d: d['id'], score_info['depositInfo']['deposits']))

        withdraw_tx_result = self._withdraw_deposit(deposit_id, self.score_address)
        self.assertTrue(withdraw_tx_result.status)

        score_info = self._query_score_info(self.score_address)
        self.assertNotIn('depositInfo', score_info)

    def test_withdraw_deposit_by_not_owner(self):
        """
        Given : The SCORE is deployed and deposit.
        When  : Try to withdraw by not owner.
        Then  : Return tx result with failure and status is 0.
        """
        # deposit icx
        deposit_tx_result = self._deposit_icx(self.score_address, MIN_DEPOSIT_AMOUNT, MIN_DEPOSIT_TERM)
        deposit_id = deposit_tx_result.tx_hash
        self.assertEqual(deposit_tx_result.status, 1)

        # withdraw by not owner
        withdraw_tx_result = self._withdraw_deposit(deposit_id, self.score_address, self._genesis)
        self.assertFalse(withdraw_tx_result.status)
        self.assertEqual(withdraw_tx_result.failure.message, "Invalid sender")

    def test_withdraw_deposit_again_after_already_withdraw_one(self):
        """
        Given : The SCORE is deployed and deposit. Sets proportion.
        When  : Withdraws twice from same deposit.
        Then  : Return tx result with failure and status is 0.
        """
        # deposit icx
        deposit_tx_result = self._deposit_icx(self.score_address, MIN_DEPOSIT_AMOUNT, MIN_DEPOSIT_TERM)
        deposit_id = deposit_tx_result.tx_hash
        self.assertEqual(deposit_tx_result.status, 1)

        # withdraw
        withdraw_tx_result = self._withdraw_deposit(deposit_id, self.score_address)
        self.assertTrue(withdraw_tx_result.status)

        score_info = self._query_score_info(self.score_address)
        self.assertNotIn('depositInfo', score_info)

        # withdraw again
        withdraw_tx_result = self._withdraw_deposit(deposit_id, self.score_address)
        self.assertFalse(withdraw_tx_result.status)
        self.assertEqual(withdraw_tx_result.failure.message, "Deposit not found")

    def test_inter_call_fee_sharing_proportion100(self):
        # deposit icx
        deposit_tx_result = self._deposit_icx(self.score_address2, 3 * MIN_DEPOSIT_AMOUNT, MIN_DEPOSIT_TERM)
        self.assertEqual(deposit_tx_result.status, 1)
        user_balance = self._query({"address": self._admin}, "icx_getBalance")
        score_info = self._query_score_info(self.score_address2)
        self.assertIn('depositInfo', score_info)
        deposit_info = score_info['depositInfo']
        initial_available_deposit = deposit_info['availableDeposit']
        initial_available_virtual_step = deposit_info['availableVirtualStep']

        # invoke score method
        score_call_tx = self._make_score_call_tx(self._admin, self.score_address2, 'set_other_score_value',
                                                 {"value": hex(100),
                                                  "proportion": hex(100), "other_score_proportion": hex(0)})
        prev_block, tx_results = self._make_and_req_block([score_call_tx])
        self._write_precommit_state(prev_block)

        # check result
        score_info = self._query_score_info(self.score_address2)
        self.assertIn('depositInfo', score_info)
        deposit_info = score_info['depositInfo']
        after_call_available_deposit = deposit_info['availableDeposit']
        score_used_fee = tx_results[0].step_used_details[self.score_address2] * tx_results[0].step_price
        after_call_user_balance = self._query({"address": self._admin}, "icx_getBalance")
        remaining_step = score_used_fee - initial_available_virtual_step * STEP_PRICE
        remaining_step = 0 if remaining_step <= 0 else remaining_step
        self.assertEqual(initial_available_deposit - remaining_step, after_call_available_deposit)
        self.assertEqual(user_balance, after_call_user_balance)
        self.assertFalse(tx_results[0].step_used_details.get(self._admin))
        self.assertFalse(tx_results[0].step_used_details.get(self.score_address))
