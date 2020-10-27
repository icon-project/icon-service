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

"""Test for icon_score_base.py and icon_score_base2.py"""
from typing import List

from iconservice.base.address import SYSTEM_SCORE_ADDRESS
from iconservice.base.exception import InvalidParamsException
from iconservice.icon_constant import DataType
from iconservice.icon_constant import ICX_IN_LOOP, Revision
from iconservice.iconscore.icon_score_result import TransactionResult
from tests.integrate_test.iiss.test_iiss_base import TestIISSBase


class TestDataTypeValidationInTx(TestIISSBase):
    def setUp(self):
        super().setUp()
        self.init_decentralized()
        self.init_inv()

        self.distribute_icx(
            accounts=self._accounts[:1],
            init_balance=2000 * ICX_IN_LOOP
        )

    def test_success_on_legacy_mode(self):
        _from = self._accounts[0]
        _to = self._accounts[1]
        value = 1 * ICX_IN_LOOP

        old_from_balance: int = self.get_balance(_from)
        self.assertTrue(old_from_balance > value)

        self.assertTrue(not _to.address.is_contract)
        old_to_balance: int = self.get_balance(_to)
        self.assertTrue(old_to_balance >= 0)

        tx_results: List['TransactionResult'] = self.score_call(
            from_=_from,
            to_=_to.address,
            value=value,
            func_name="test",
        )

        self.assertEqual(2, len(tx_results))
        tx_result = tx_results[1]
        self.assertEqual(1, tx_result.status)
        fee: int = tx_result.step_used * tx_result.step_price
        self.assertTrue(fee > 0)

        self.assertEqual(old_from_balance - fee - value, self.get_balance(_from))
        self.assertEqual(old_to_balance + value, self.get_balance(_to))

    def test_validate_data_type(self):
        self.set_revision(Revision.IMPROVED_PRE_VALIDATOR.value)

        _from = self._accounts[0]
        _to = SYSTEM_SCORE_ADDRESS
        value = 1 * ICX_IN_LOOP

        self.assertTrue(_to.is_contract)

        tx = self.create_transfer_icx_tx(
            from_=_from,
            to_=_to,
            value=value,
            disable_pre_validate=True
        )
        origin_params = {'params': self.make_origin_params(tx['params'])}
        self.icon_service_engine.validate_transaction(tx, origin_params)

        invalid_data_types = ("abc", 1, 1.1, b"call", b"deploy", b"deposit", b"message")
        for data_type in invalid_data_types:
            tx["params"]["dataType"] = data_type

            with self.assertRaises(InvalidParamsException):
                self.icon_service_engine.validate_transaction(tx, origin_params)

        for data_type in DataType._TYPES:
            params = tx["params"]

            if data_type:
                params["dataType"] = data_type
            if data_type == DataType.CALL:
                params["data"] = {
                    "method": "do"
                }
            else:
                continue

            self.icon_service_engine.validate_transaction(tx, origin_params)

    def test_invalid_score_call_failure_on_invoke(self):
        self.set_revision(Revision.IMPROVED_PRE_VALIDATOR.value)

        _from = self._accounts[0]
        _to = self._accounts[1]
        value = 1 * ICX_IN_LOOP

        old_from_balance: int = self.get_balance(_from)
        self.assertTrue(old_from_balance > value)

        self.assertTrue(not _to.address.is_contract)
        old_to_balance: int = self.get_balance(_to)
        self.assertTrue(old_to_balance >= 0)

        tx_results: List['TransactionResult'] = self.score_call(
            from_=self._accounts[0],
            to_=self._accounts[1].address,
            value=value,
            func_name="test",
            pre_validation_enabled=False,
            expected_status=False
        )

        self.assertEqual(2, len(tx_results))
        tx_result = tx_results[1]
        self.assertEqual(0, tx_result.status)
        fee: int = tx_result.step_used * tx_result.step_price
        self.assertTrue(fee > 0)

        self.assertEqual(old_from_balance - fee, self.get_balance(_from))
        self.assertEqual(old_to_balance, self.get_balance(_to))

    def test_invalid_deploy_call_failure_on_invoke(self):
        self.set_revision(Revision.IMPROVED_PRE_VALIDATOR.value)

        _from = self._accounts[0]
        _to = self._accounts[1]
        value = 1 * ICX_IN_LOOP

        old_from_balance: int = self.get_balance(_from)
        self.assertTrue(old_from_balance > value)

        self.assertTrue(not _to.address.is_contract)
        old_to_balance: int = self.get_balance(_to)
        self.assertTrue(old_to_balance >= 0)

        tx_results: List['TransactionResult'] = self.deploy_score(
            score_root="sample_deploy_scores",
            score_name="install/sample_score",
            from_=_from,
            to_=_to,
            step_limit=10 ** 10,
            deploy_params={'value': hex(1 * ICX_IN_LOOP)},
            pre_validation_enabled=False,
            expected_status=False
        )

        self.assertEqual(2, len(tx_results))
        tx_result = tx_results[1]
        self.assertEqual(0, tx_result.status)
        fee: int = tx_result.step_used * tx_result.step_price
        self.assertTrue(fee > 0)

        self.assertEqual(old_from_balance - fee, self.get_balance(_from))
        self.assertEqual(old_to_balance, self.get_balance(_to))

    def test_invalid_deposit_call_failure_on_invoke(self):
        self.set_revision(Revision.IMPROVED_PRE_VALIDATOR.value)

        _from = self._accounts[0]
        _to = self._accounts[1]
        value = 1000 * ICX_IN_LOOP

        old_from_balance: int = self.get_balance(_from)
        self.assertTrue(old_from_balance > value)

        self.assertTrue(not _to.address.is_contract)
        old_to_balance: int = self.get_balance(_to)
        self.assertTrue(old_to_balance >= 0)

        tx = self.create_deposit_tx(
            from_=_from,
            to_=_to,
            action="add",
            value=value,
            params={},
            pre_validation_enabled=False
        )

        tx_results = self.process_confirm_block_tx([tx], expected_status=False)

        self.assertEqual(2, len(tx_results))
        tx_result = tx_results[1]
        self.assertEqual(0, tx_result.status)
        fee: int = tx_result.step_used * tx_result.step_price
        self.assertTrue(fee > 0)

        self.assertEqual(old_from_balance - fee, self.get_balance(_from))
        self.assertEqual(old_to_balance, self.get_balance(_to))

    def test_valid_message_call_success_on_invoke(self):
        """
        Condition:
        - to: EOA
        - dataType: "message"

        Result:
        - Validation: success
        - Invoke: success
        """
        self.set_revision(Revision.IMPROVED_PRE_VALIDATOR.value)

        _from = self._accounts[0]
        _to = self._accounts[1]
        value = 2 * ICX_IN_LOOP

        old_from_balance: int = self.get_balance(_from)
        self.assertTrue(old_from_balance > value)

        self.assertTrue(not _to.address.is_contract)
        old_to_balance: int = self.get_balance(_to)
        self.assertTrue(old_to_balance >= 0)

        tx = self.create_message_tx(
            from_=_from,
            to_=_to,
            data=b"hello",
            value=value,
            pre_validation_enabled=True
        )

        tx_results = self.process_confirm_block_tx([tx], expected_status=True)

        self.assertEqual(2, len(tx_results))
        tx_result = tx_results[1]
        self.assertEqual(1, tx_result.status)
        fee: int = tx_result.step_used * tx_result.step_price
        self.assertTrue(fee > 0)

        self.assertEqual(old_from_balance - value - fee, self.get_balance(_from))
        self.assertEqual(old_to_balance + value, self.get_balance(_to))
