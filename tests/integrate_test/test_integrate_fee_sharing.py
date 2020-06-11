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

import unittest
from typing import TYPE_CHECKING, List

from iconcommons import IconConfig
from iconservice.base.address import Address, AddressPrefix, GOVERNANCE_SCORE_ADDRESS
from iconservice.base.exception import InvalidRequestException
from iconservice.fee import FeeEngine
from iconservice.icon_config import default_icon_config
from iconservice.icon_constant import ConfigKey, Revision, ICX_IN_LOOP
from iconservice.icon_service_engine import IconServiceEngine
from tests import root_clear
from tests.integrate_test.test_integrate_base import TestIntegrateBase

if TYPE_CHECKING:
    from iconservice.iconscore.icon_score_result import TransactionResult

STEP_PRICE = 10 ** 10

MAX_DEPOSIT_AMOUNT = FeeEngine._MAX_DEPOSIT_AMOUNT
MIN_DEPOSIT_AMOUNT = FeeEngine._MIN_DEPOSIT_AMOUNT
MAX_DEPOSIT_TERM = FeeEngine._MAX_DEPOSIT_TERM
MIN_DEPOSIT_TERM = FeeEngine._MIN_DEPOSIT_TERM


class TestIntegrateFeeSharing(TestIntegrateBase):
    def setUp(self):
        root_clear(self._score_root_path, self._state_db_root_path, self._iiss_db_root_path, self._precommit_log_path)

        self._block_height = -1
        self._prev_block_hash = None

        config = IconConfig("", default_icon_config)
        config.load()
        config.update_conf({ConfigKey.BUILTIN_SCORE_OWNER: str(self._admin.address)})
        config.update_conf({ConfigKey.SERVICE: {ConfigKey.SERVICE_AUDIT: False,
                                                ConfigKey.SERVICE_FEE: True,
                                                ConfigKey.SERVICE_SCORE_PACKAGE_VALIDATOR: False}})
        config.update_conf({ConfigKey.SCORE_ROOT_PATH: self._score_root_path,
                            ConfigKey.STATE_DB_ROOT_PATH: self._state_db_root_path})
        config.update_conf(self._make_init_config())

        self._mock_ipc()

        self.icon_service_engine = IconServiceEngine()
        self.icon_service_engine.open(config)

        self._genesis_invoke()

        self.update_governance(version="governance_for_fee2")

        tx_results: List['TransactionResult'] = self.deploy_score(
            score_root="sample_deploy_scores",
            score_name="install/sample_score_fee_sharing",
            from_=self._admin,
            deploy_params={"value": hex(100)})
        self.score_address = tx_results[0].score_address

        tx_results: List['TransactionResult'] = self.deploy_score(
            score_root="sample_deploy_scores",
            score_name="install/sample_score_fee_sharing_inter_call",
            from_=self._admin,
            deploy_params={"value": hex(100), "score_address": str(self.score_address)})
        self.score_address2 = tx_results[0].score_address

    def tearDown(self):
        super().tearDown()

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

    def test_deposit_fee(self):
        before_balance: int = self.get_balance(self._admin)
        tx_results: List['TransactionResult'] = self.deposit_icx(score_address=self.score_address,
                                                                 amount=MIN_DEPOSIT_AMOUNT,
                                                                 period=MIN_DEPOSIT_TERM)
        deposit_fee = tx_results[0].step_price * tx_results[0].step_used

        deposit_id = tx_results[0].tx_hash
        score_info = self._query_score_info(self.score_address)
        self.assertIn('depositInfo', score_info)
        self.assertIn(deposit_id, map(lambda d: d['id'], score_info['depositInfo']['deposits']))
        after_balance: int = self.get_balance(self._admin)

        self.assertEqual(before_balance - MIN_DEPOSIT_AMOUNT - deposit_fee, after_balance)

    def test_deposit_fee_eventlog(self):
        # deploy same score for
        tx_results: List['TransactionResult'] = self.deploy_score(
            score_root="sample_deploy_scores",
            score_name="install/sample_score_fee_sharing",
            from_=self._admin,
            deploy_params={"value": hex(100)})
        same_score_address = tx_results[0].score_address

        # set revision 4
        self.set_revision(Revision.FOUR.value)

        # success case: before IISS_REV revision, should charge fee about event log
        tx_results: List['TransactionResult'] = self.deposit_icx(score_address=self.score_address,
                                                                 amount=MIN_DEPOSIT_AMOUNT,
                                                                 period=MIN_DEPOSIT_TERM)
        step_used_before_iiss_rev = tx_results[0].step_used

        # set revision 5 (IISS_REV)
        self.set_revision(Revision.IISS.value)

        tx_results: List['TransactionResult'] = self.deposit_icx(score_address=same_score_address,
                                                                 amount=MIN_DEPOSIT_AMOUNT,
                                                                 period=MIN_DEPOSIT_TERM)
        step_used_after_iiss_rev = tx_results[0].step_used

        # event log count: 101 , event log step:100
        event_log_fee = 101 * 100
        self.assertEqual(step_used_before_iiss_rev, step_used_after_iiss_rev + event_log_fee)

    def test_deposit_fee_icx_range(self):
        self.deposit_icx(score_address=self.score_address,
                         amount=MAX_DEPOSIT_AMOUNT,
                         period=MIN_DEPOSIT_TERM)

        self.deposit_icx(score_address=self.score_address,
                         amount=MAX_DEPOSIT_AMOUNT + 1,
                         period=MIN_DEPOSIT_TERM,
                         expected_status=False)

        self.deposit_icx(score_address=self.score_address,
                         amount=MIN_DEPOSIT_AMOUNT,
                         period=MIN_DEPOSIT_TERM)

        self.deposit_icx(score_address=self.score_address,
                         amount=MIN_DEPOSIT_AMOUNT - 1,
                         period=MIN_DEPOSIT_TERM,
                         expected_status=False)

    def test_deposit_fee_term_range(self):
        self.deposit_icx(score_address=self.score_address,
                         amount=MIN_DEPOSIT_AMOUNT,
                         period=MAX_DEPOSIT_TERM)

        # self.deposit_icx(score_address=self.score_address,
        #                  amount=MIN_DEPOSIT_AMOUNT,
        #                  period=MAX_DEPOSIT_TERM + 1,
        #                  expected_status=False)

        self.deposit_icx(score_address=self.score_address,
                         amount=MIN_DEPOSIT_AMOUNT,
                         period=MIN_DEPOSIT_TERM)

        # self.deposit_icx(score_address=self.score_address,
        #                  amount=MIN_DEPOSIT_AMOUNT,
        #                  period=MIN_DEPOSIT_TERM - 1,
        #                  expected_status=False)

    def test_sharing_fee_case_score_0(self):
        # deposit icx
        self.deposit_icx(score_address=self.score_address,
                         amount=3 * MIN_DEPOSIT_AMOUNT,
                         period=MIN_DEPOSIT_TERM)
        user_balance: int = self.get_balance(self._admin)
        score_info: dict = self._query_score_info(self.score_address)
        self.assertIn('depositInfo', score_info)
        deposit_info: dict = score_info['depositInfo']
        initial_available_deposit: int = deposit_info['availableDeposit']

        tx_results: List['TransactionResult'] = self.score_call(from_=self._admin,
                                                                to_=self.score_address,
                                                                func_name="set_value",
                                                                params={"value": hex(100)})
        fee_used = tx_results[0].step_used * tx_results[0].step_price

        after_call_user_balance: int = self.get_balance(self._admin)

        score_info = self._query_score_info(self.score_address)
        self.assertIn('depositInfo', score_info)
        deposit_info: dict = score_info['depositInfo']
        after_call_available_deposit: int = deposit_info['availableDeposit']
        self.assertEqual(user_balance - fee_used, after_call_user_balance)
        self.assertEqual(initial_available_deposit, after_call_available_deposit)
        self.assertFalse(tx_results[0].to_dict().get('detailed_step_used'))

    def test_sharing_fee_case_score_50(self):
        # deposit icx
        self.deposit_icx(score_address=self.score_address,
                         amount=3 * MIN_DEPOSIT_AMOUNT,
                         period=MIN_DEPOSIT_TERM)
        user_balance: int = self.get_balance(self._admin)

        score_info: dict = self._query_score_info(self.score_address)
        self.assertIn('depositInfo', score_info)
        deposit_info: dict = score_info['depositInfo']
        initial_available_deposit: int = deposit_info['availableDeposit']
        initial_available_virtual_step: int = deposit_info['availableVirtualStep']
        proportion: int = 50

        # invoke score method
        tx_results: List['TransactionResult'] = self.score_call(
            from_=self._admin,
            to_=self.score_address,
            func_name="set_value",
            params={"value": hex(100), "proportion": hex(proportion)})

        # check result
        score_info: dict = self._query_score_info(self.score_address)
        self.assertIn('depositInfo', score_info)
        deposit_info: dict = score_info['depositInfo']
        after_call_available_deposit: int = deposit_info['availableDeposit']
        admin_addr: 'Address' = self._admin.address
        user_used_fee: int = tx_results[0].step_used_details[admin_addr] * tx_results[0].step_price
        score_used_fee: int = tx_results[0].step_used_details[self.score_address] * tx_results[0].step_price
        after_call_user_balance: int = self.get_balance(self._admin)
        remaining_step: int = score_used_fee - initial_available_virtual_step * STEP_PRICE
        remaining_step: int = 0 if remaining_step <= 0 else remaining_step
        self.assertEqual(initial_available_deposit - remaining_step, after_call_available_deposit)
        self.assertEqual(user_balance - user_used_fee, after_call_user_balance)
        self.assertEqual(score_used_fee, user_used_fee)

    def test_sharing_fee_case_score_100(self):
        # deposit icx
        self.deposit_icx(score_address=self.score_address,
                         amount=3 * MIN_DEPOSIT_AMOUNT,
                         period=MIN_DEPOSIT_TERM)
        user_balance: int = self.get_balance(self._admin)

        score_info: dict = self._query_score_info(self.score_address)
        self.assertIn('depositInfo', score_info)
        deposit_info: dict = score_info['depositInfo']
        initial_available_deposit: int = deposit_info['availableDeposit']
        initial_available_virtual_step: int = deposit_info['availableVirtualStep']

        # invoke score method
        tx_results: List['TransactionResult'] = self.score_call(from_=self._admin,
                                                                to_=self.score_address,
                                                                func_name="set_value",
                                                                params={"value": hex(100), "proportion": hex(100)})

        # check result
        score_info: dict = self._query_score_info(self.score_address)
        self.assertIn('depositInfo', score_info)
        deposit_info: dict = score_info['depositInfo']
        after_call_available_deposit: int = deposit_info['availableDeposit']
        score_used_fee: int = tx_results[0].step_used_details[self.score_address] * tx_results[0].step_price
        after_call_user_balance: int = self.get_balance(self._admin)
        remaining_step: int = score_used_fee - initial_available_virtual_step * STEP_PRICE
        remaining_step: int = 0 if remaining_step <= 0 else remaining_step
        self.assertEqual(initial_available_deposit - remaining_step, after_call_available_deposit)
        self.assertEqual(user_balance, after_call_user_balance)
        self.assertFalse(tx_results[0].step_used_details.get(self._admin))

    @unittest.skip("Will take over 8 minutes")
    def test_score_call_after_deposit_expired(self):
        # deposit icx
        self.deposit_icx(score_address=self.score_address,
                         amount=3 * MIN_DEPOSIT_AMOUNT,
                         period=1)

        score_info: dict = self._query_score_info(self.score_address)
        self.assertIn('depositInfo', score_info)
        deposit_info: dict = score_info['depositInfo']
        initial_available_deposit: int = deposit_info['availableDeposit']
        self.assertGreater(initial_available_deposit, 0)

        # increase block_height
        for i in range(MIN_DEPOSIT_TERM):
            self.transfer_icx(from_=self._admin,
                              to_=self._accounts[0],
                              value=10 ** 8)

        # invoke score method
        with self.assertRaises(InvalidRequestException) as e:
            self.create_score_call_tx(from_=self._admin,
                                      to_=self.score_address,
                                      func_name="set_value",
                                      params={"value": hex(100), "proportion": hex(100)})
        self.assertEqual(e.exception.message, "Out of deposit balance")

        # check result
        score_info: dict = self._query_score_info(self.score_address)
        self.assertIn('depositInfo', score_info)
        deposit_info: dict = score_info['depositInfo']
        after_destroyed_available_deposit: int = deposit_info['availableDeposit']
        self.assertEqual(after_destroyed_available_deposit, 0)

    def test_deposit_unauthorized_account(self):
        # give icx to tester
        self.transfer_icx(from_=self._admin,
                          to_=self._accounts[0],
                          value=10000 * ICX_IN_LOOP)

        # unauthorized account deposit 5000icx in SCORE
        tx_results: List['TransactionResult'] = self.deposit_icx(score_address=self.score_address,
                                                                 amount=MIN_DEPOSIT_AMOUNT,
                                                                 period=MIN_DEPOSIT_TERM,
                                                                 sender=self._accounts[0],
                                                                 expected_status=False)

        self.assertTrue(tx_results[0].failure)

    def test_deposit_nonexistent_score(self):
        # give icx to tester
        self.transfer_icx(from_=self._admin,
                          to_=self._accounts[0],
                          value=10000 * ICX_IN_LOOP)

        # deposit icx in nonexistent SCORE
        with self.assertRaises(InvalidRequestException) as e:
            self.deposit_icx(score_address=Address.from_prefix_and_int(AddressPrefix.CONTRACT, 3),
                             amount=MIN_DEPOSIT_AMOUNT,
                             period=MIN_DEPOSIT_TERM)

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
        amount_deposit = 5000 * ICX_IN_LOOP
        virtual_step_issuance1 = 40_000_000_000
        virtual_step_issuance2 = 80_000_000_000

        # Creates a deposit with 5000 ICX
        tx_results: List['TransactionResult'] = self.deposit_icx(score_address=self.score_address,
                                                                 amount=amount_deposit,
                                                                 period=MIN_DEPOSIT_TERM)
        deposit_id1 = tx_results[0].tx_hash

        score_info: dict = self._query_score_info(self.score_address)
        self.assertIn('depositInfo', score_info)
        deposit_info: dict = score_info['depositInfo']
        self.assertEqual(deposit_info["scoreAddress"], self.score_address)
        self.assertEqual(deposit_id1, deposit_info["deposits"][0]['id'])
        self.assertEqual(len(deposit_info["deposits"]), 1)
        self.assertEqual(deposit_info["availableVirtualStep"], virtual_step_issuance1)
        self.assertEqual(deposit_info["availableDeposit"], amount_deposit * 90 // 100)

        # Creates a more deposit with 5000 * 2 ICX
        tx_results: List['TransactionResult'] = self.deposit_icx(score_address=self.score_address,
                                                                 amount=amount_deposit * 2,
                                                                 period=MIN_DEPOSIT_TERM)
        deposit_id2 = tx_results[0].tx_hash

        score_info: dict = self._query_score_info(self.score_address)
        self.assertIn('depositInfo', score_info)
        deposit_info: dict = score_info['depositInfo']
        self.assertEqual(deposit_info["scoreAddress"], self.score_address)
        self.assertEqual(deposit_id1, deposit_info["deposits"][0]['id'])
        self.assertEqual(deposit_id2, deposit_info["deposits"][1]['id'])
        self.assertEqual(len(deposit_info["deposits"]), 2)
        self.assertEqual(deposit_info["availableVirtualStep"], virtual_step_issuance1 + virtual_step_issuance2)

        sum_of_available_deposit: int = 0
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
            self.deposit_icx(score_address=self.score_address,
                             amount=amount_deposit,
                             period=MIN_DEPOSIT_TERM)

        score_info = self._query_score_info(self.score_address)
        self.assertIn('depositInfo', score_info)

        deposit_info: dict = score_info['depositInfo']
        self.assertEqual(len(deposit_info["deposits"]), 99)
        self.assertEqual(deposit_info["availableDeposit"],
                         (amount_deposit - amount_deposit * 10 // 100) * len(deposit_info['deposits']))

    def test_get_deposit_by_valid_id(self):
        """
        Given : The SCORE is deployed.
        When  : Tries to get deposit info by valid id.
        Then  : Returns deposit info correctly.
        """
        tx_results: List['TransactionResult'] = self.deposit_icx(score_address=self.score_address,
                                                                 amount=MIN_DEPOSIT_AMOUNT,
                                                                 period=MIN_DEPOSIT_TERM)
        deposit_id: bytes = tx_results[0].tx_hash

        score_info: dict = self._query_score_info(self.score_address)
        self.assertIn('depositInfo', score_info)
        self.assertIn(deposit_id, map(lambda d: d['id'], score_info['depositInfo']['deposits']))

    def test_withdraw_deposit_after_deposit(self):
        """
        Given : The SCORE is deployed and deposit once.
        When  : Withdraws the deposit.
        Then  : Amount of availableDeposit is 0.
        """
        tx_results: List['TransactionResult'] = self.deposit_icx(score_address=self.score_address,
                                                                 amount=MIN_DEPOSIT_AMOUNT,
                                                                 period=MIN_DEPOSIT_TERM)
        deposit_id: bytes = tx_results[0].tx_hash

        score_info: dict = self._query_score_info(self.score_address)
        self.assertIn('depositInfo', score_info)
        self.assertIn(deposit_id, map(lambda d: d['id'], score_info['depositInfo']['deposits']))

        tx_results: List['TransactionResult'] = self.withdraw_deposit(deposit_id=deposit_id,
                                                                      score_address=self.score_address)
        self.assertTrue(tx_results[0].status)
        event_log = tx_results[0].event_logs[0]
        self.assertEqual('DepositWithdrawn(bytes,Address,int,int)', event_log.indexed[0])
        self.assertEqual(event_log.data[0], MIN_DEPOSIT_AMOUNT) # withdraw amount
        self.assertEqual(event_log.data[1], 0)  # penalty amount

        score_info: dict = self._query_score_info(self.score_address)
        self.assertNotIn('depositInfo', score_info)

    def test_withdraw_deposit_with_penalty(self):
        """
        Given : The SCORE is deployed, deposit once and .
        When  : Withdraws the deposit.
        Then  : Amount of availableDeposit is 0.
        """
        tx_results: List['TransactionResult'] = self.deposit_icx(score_address=self.score_address,
                                                                 amount=MIN_DEPOSIT_AMOUNT,
                                                                 period=MIN_DEPOSIT_TERM)
        deposit_id: bytes = tx_results[0].tx_hash

        score_info: dict = self._query_score_info(self.score_address)
        self.assertIn('depositInfo', score_info)
        self.assertIn(deposit_id, map(lambda d: d['id'], score_info['depositInfo']['deposits']))

        # invoke score method to use virtual step
        self.score_call(from_=self._admin,
                        to_=self.score_address,
                        func_name="set_value",
                        params={"value": hex(100), "proportion": hex(100)})

        tx_results: List['TransactionResult'] = self.withdraw_deposit(deposit_id=deposit_id,
                                                                      score_address=self.score_address)
        self.assertTrue(tx_results[0].status)
        event_log = tx_results[0].event_logs[0]
        self.assertEqual('DepositWithdrawn(bytes,Address,int,int)', event_log.indexed[0])
        self.assertTrue(event_log.data[0] < MIN_DEPOSIT_AMOUNT) # withdraw amount
        self.assertTrue(event_log.data[1] > 0)  # penalty amount

        score_info: dict = self._query_score_info(self.score_address)
        self.assertNotIn('depositInfo', score_info)

    def test_withdraw_deposit_by_not_owner(self):
        """
        Given : The SCORE is deployed and deposit.
        When  : Try to withdraw by not owner.
        Then  : Return tx result with failure and status is 0.
        """

        self.transfer_icx(from_=self._admin,
                          to_=self._accounts[0],
                          value=10000 * ICX_IN_LOOP)
        # deposit icx
        tx_results: List['TransactionResult'] = self.deposit_icx(score_address=self.score_address,
                                                                 amount=MIN_DEPOSIT_AMOUNT,
                                                                 period=MIN_DEPOSIT_TERM)
        deposit_id: bytes = tx_results[0].tx_hash

        # withdraw by not owner
        tx_results: List['TransactionResult'] = self.withdraw_deposit(deposit_id=deposit_id,
                                                                      score_address=self.score_address,
                                                                      sender=self._accounts[0],
                                                                      expected_status=False)
        self.assertEqual(tx_results[0].failure.message, "Invalid sender")

    def test_withdraw_deposit_again_after_already_withdraw_one(self):
        """
        Given : The SCORE is deployed and deposit. Sets proportion.
        When  : Withdraws twice from same deposit.
        Then  : Return tx result with failure and status is 0.
        """
        # deposit icx
        tx_results: List['TransactionResult'] = self.deposit_icx(score_address=self.score_address,
                                                                 amount=MIN_DEPOSIT_AMOUNT,
                                                                 period=MIN_DEPOSIT_TERM)
        deposit_id: bytes = tx_results[0].tx_hash

        # withdraw
        self.withdraw_deposit(deposit_id=deposit_id,
                              score_address=self.score_address)

        score_info: dict = self._query_score_info(self.score_address)
        self.assertNotIn('depositInfo', score_info)

        # withdraw again
        tx_results: List['TransactionResult'] = self.withdraw_deposit(deposit_id=deposit_id,
                                                                      score_address=self.score_address,
                                                                      expected_status=False)
        self.assertEqual(tx_results[0].failure.message, "Deposit not found")

    def test_inter_call_fee_sharing_proportion100(self):
        # deposit icx
        self.deposit_icx(score_address=self.score_address2,
                         amount=3 * MIN_DEPOSIT_AMOUNT,
                         period=MIN_DEPOSIT_TERM)
        user_balance: int = self.get_balance(self._admin)
        score_info: dict = self._query_score_info(self.score_address2)
        self.assertIn('depositInfo', score_info)
        deposit_info: dict = score_info['depositInfo']
        initial_available_deposit: int = deposit_info['availableDeposit']
        initial_available_virtual_step: int = deposit_info['availableVirtualStep']

        # invoke score method
        tx_results: List['TransactionResult'] = self.score_call(
            from_=self._admin,
            to_=self.score_address2,
            func_name="set_other_score_value",
            params={"value": hex(100),
                    "proportion": hex(100),
                    "other_score_proportion": hex(0)})

        # check result
        score_info: dict = self._query_score_info(self.score_address2)
        self.assertIn('depositInfo', score_info)
        deposit_info: dict = score_info['depositInfo']
        after_call_available_deposit: int = deposit_info['availableDeposit']
        score_used_fee: int = tx_results[0].step_used_details[self.score_address2] * tx_results[0].step_price
        after_call_user_balance: int = self.get_balance(self._admin)
        remaining_step: int = score_used_fee - initial_available_virtual_step * STEP_PRICE
        remaining_step: int = 0 if remaining_step <= 0 else remaining_step
        self.assertEqual(initial_available_deposit - remaining_step, after_call_available_deposit)
        self.assertEqual(user_balance, after_call_user_balance)
        self.assertFalse(tx_results[0].step_used_details.get(self._admin))
        self.assertFalse(tx_results[0].step_used_details.get(self.score_address))
