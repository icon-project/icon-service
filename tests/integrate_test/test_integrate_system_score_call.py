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
from typing import List

from iconservice.base.address import SYSTEM_SCORE_ADDRESS
from iconservice.icon_constant import ConfigKey
from iconservice.icon_constant import ICX_IN_LOOP, Revision
from iconservice.iconscore.icon_score_result import TransactionResult
from tests.integrate_test.iiss.test_iiss_base import TestIISSBase


class TestIntegrateSystemScoreCall(TestIISSBase):
    """ All cases for System SCORE are tested in unit and integrate test.

    In this test, only one success case per external method of System SCORE is checked
    through inter-call to confirm System SCORE inter-call functionality.
    """
    use_interface: int = 0

    def setUp(self):
        super().setUp()
        self.update_governance()
        self.set_revision(Revision.SYSTEM_SCORE_ENABLED.value)

        self.distribute_icx(accounts=self._accounts[:10],
                            init_balance=10000 * ICX_IN_LOOP)

    def test_burn_on_error(self):
        self.set_revision(Revision.BURN_V2_ENABLED.value - 1)

        amount_to_burn = 2 * ICX_IN_LOOP
        sender = self._accounts[0].address
        treasury_address = self.get_treasury_address()

        old_sender_balance: int = self.get_balance(sender)
        old_treasury_balance: int = self.get_balance(treasury_address)

        # Check whether the balance of system score is 0
        balance: int = self.get_balance(SYSTEM_SCORE_ADDRESS)
        self.assertEqual(0, balance)

        self.assertTrue(old_sender_balance > amount_to_burn)
        tx_results = self.score_call(
            from_=sender,
            to_=SYSTEM_SCORE_ADDRESS,
            value=amount_to_burn,
            func_name="burn",
            expected_status=False
        )

        tx_result = tx_results[0]
        self.assertEqual(1, len(tx_results))

        fee: int = tx_result.step_price * tx_result.step_used
        expected_sender_balance: int = old_sender_balance - fee
        balance: int = self.get_balance(sender)
        self.assertEqual(expected_sender_balance, balance)

        # Check whether fee is transferred to treasury_address
        treasury_balance: int = self.get_balance(treasury_address)
        expected_treasury_balance: int = old_treasury_balance + fee
        self.assertEqual(expected_treasury_balance, treasury_balance)

    def test_burn_on_success(self):
        self.set_revision(Revision.BURN_V2_ENABLED.value)
        amount_to_burn = 2 * ICX_IN_LOOP
        sender = self._accounts[0].address
        treasury_address = self.get_treasury_address()

        old_total_supply: int = self.get_total_supply()
        old_sender_balance: int = self.get_balance(sender)
        old_treasury_balance: int = self.get_balance(treasury_address)

        # Check whether the balance of system score is 0
        balance: int = self.get_balance(SYSTEM_SCORE_ADDRESS)
        self.assertEqual(0, balance)

        self.assertTrue(old_sender_balance > amount_to_burn)
        tx_results = self.score_call(
            from_=sender,
            to_=SYSTEM_SCORE_ADDRESS,
            value=amount_to_burn,
            func_name="burn"
        )
        tx_result = tx_results[0]
        self.assertEqual(1, tx_result.status)
        self.assertEqual(1, len(tx_result.event_logs))

        new_total_supply: int = self.get_total_supply()

        # Check for the balance of sender
        fee: int = tx_result.step_price * tx_result.step_used
        expected_balance = old_sender_balance - fee - amount_to_burn
        balance: int = self.get_balance(sender)
        self.assertEqual(expected_balance, balance)

        # Check whether the balance of system score is 0
        balance: int = self.get_balance(SYSTEM_SCORE_ADDRESS)
        self.assertEqual(0, balance)

        # Check if ICXBurnedV2 event_log is recorded
        event_log = tx_result.event_logs[0]
        self.assertEqual(
            ["ICXBurnedV2(Address,int,int)", sender],
            event_log.indexed
        )
        self.assertEqual([amount_to_burn, new_total_supply], event_log.data)
        self.assertEqual(SYSTEM_SCORE_ADDRESS, event_log.score_address)

        # Check whether total_supply is reduced by amount_to_burn
        self.assertEqual(old_total_supply - amount_to_burn, new_total_supply)

        # Check whether fee is transferred to treasury_address
        treasury_balance: int = self.get_balance(treasury_address)
        expected_treasury_balance: int = old_treasury_balance + fee
        self.assertEqual(expected_treasury_balance, treasury_balance)

    def test_register_prep(self):
        self.set_revision(Revision.BURN_V2_ENABLED.value)
        sender = self._accounts[0].address

        # success case: If input 2000 ICX as value when calling 'registerPRep' method, should be registered successfully
        prep_registration_fee: int = self._config[ConfigKey.PREP_REGISTRATION_FEE]
        self.assertTrue(prep_registration_fee > 0)
        old_total_supply: int = self.get_total_supply()

        old_balance: int = self.get_balance(sender)
        tx_results: List['TransactionResult'] = self.register_prep(
            from_=sender,
            value=prep_registration_fee
        )

        tx_result = tx_results[0]
        self.assertEqual(2, len(tx_result.event_logs))

        # Check for ICXBurnedV2 eventlog
        event_log = tx_result.event_logs[0]
        self.assertEqual(
            ["ICXBurnedV2(Address,int,int)", sender],
            event_log.indexed
        )
        self.assertEqual(SYSTEM_SCORE_ADDRESS, event_log.score_address)
        self.assertEqual([prep_registration_fee, old_total_supply - prep_registration_fee], event_log.data)

        # Check for PRepRegistered eventlog
        event_log = tx_result.event_logs[1]
        self.assertEqual(["PRepRegistered(Address)"], event_log.indexed)
        self.assertEqual(SYSTEM_SCORE_ADDRESS, event_log.score_address)
        self.assertEqual([sender], event_log.data)

        # Check for balance
        fee = tx_result.step_price * tx_result.step_used
        balance: int = self.get_balance(sender)
        self.assertEqual(old_balance - prep_registration_fee - fee, balance)

        # Check for total_supply
        self.assertEqual(old_total_supply - prep_registration_fee, self.get_total_supply())
