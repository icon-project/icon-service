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

"""on_install parameters testcase"""
from typing import TYPE_CHECKING, List

from iconservice.base.address import SYSTEM_SCORE_ADDRESS, Address
from iconservice.base.exception import ExceptionCode
from tests import raise_exception_start_tag, raise_exception_end_tag
from tests.integrate_test.test_integrate_base import TestIntegrateBase

if TYPE_CHECKING:
    from iconservice.iconscore.icon_score_result import TransactionResult


class TestIntegrateOnInstallParameters(TestIntegrateBase):
    def test_oninstall_parameters_success(self):
        init_supply: int = 1000
        decimal: int = 18
        # deploy
        tx = self.create_deploy_score_tx(score_root="sample_deploy_scores",
                                         score_name=f"install/sample_token",
                                         from_=self._accounts[0],
                                         to_=SYSTEM_SCORE_ADDRESS,
                                         deploy_params={"init_supply": hex(init_supply), "decimal": hex(decimal)})
        tx_results: List['TransactionResult'] = self.process_confirm_block_tx([tx])
        score_addr1 = tx_results[0].score_address

        query_request = {
            "from": self._admin,
            "to": score_addr1,
            "dataType": "call",
            "data": {
                "method": "total_supply",
            }
        }

        total_supply = self._query(query_request)
        self.assertEqual(total_supply, init_supply * 10 ** decimal)

    def test_more_parameters_oninstall(self):
        init_supply: int = 1000
        decimal: int = 18

        tx = self.create_deploy_score_tx(score_root="sample_deploy_scores",
                                         score_name=f"install/sample_token",
                                         from_=self._accounts[0],
                                         to_=SYSTEM_SCORE_ADDRESS,
                                         deploy_params={"init_supply": hex(init_supply),
                                                        "decimal": hex(decimal),
                                                        "additional_param": hex(123)})
        tx_results: List['TransactionResult'] = self.process_confirm_block_tx([tx], expected_status=False)
        self.assertEqual(tx_results[0].failure.code, ExceptionCode.INVALID_PARAMETER)

    def test_missing_parameters_oninstall(self):
        tx1 = self.create_deploy_score_tx(score_root="sample_deploy_scores",
                                          score_name=f"install/sample_token",
                                          from_=self._accounts[0],
                                          to_=SYSTEM_SCORE_ADDRESS,
                                          deploy_params={"decimal": hex(18)})

        tx2 = self.create_deploy_score_tx(score_root="sample_deploy_scores",
                                          score_name=f"install/sample_token",
                                          from_=self._accounts[0],
                                          to_=SYSTEM_SCORE_ADDRESS,
                                          deploy_params={"init_supply": hex(1000)})

        tx3 = self.create_deploy_score_tx(score_root="sample_deploy_scores",
                                          score_name=f"install/sample_token",
                                          from_=self._accounts[0],
                                          to_=SYSTEM_SCORE_ADDRESS,
                                          deploy_params={})
        tx_results: List['TransactionResult'] = self.process_confirm_block_tx([tx1, tx2, tx3], expected_status=False)

        self.assertEqual(tx_results[0].failure.code, ExceptionCode.SYSTEM_ERROR)
        self.assertEqual(tx_results[1].failure.code, ExceptionCode.SYSTEM_ERROR)
        self.assertEqual(tx_results[2].failure.code, ExceptionCode.SYSTEM_ERROR)

        self.assertTrue(
            tx_results[0].failure.message.find("on_install() missing 1 required positional argument:") != -1)
        self.assertTrue(
            tx_results[1].failure.message.find("on_install() missing 1 required positional argument:") != -1)
        self.assertTrue(
            tx_results[2].failure.message.find("on_install() missing 2 required positional arguments:") != -1)

    def test_invalid_parameter_value_oninstall(self):
        tx1 = self.create_deploy_score_tx(score_root="sample_deploy_scores",
                                          score_name=f"install/sample_token",
                                          from_=self._accounts[0],
                                          to_=SYSTEM_SCORE_ADDRESS,
                                          deploy_params={"init_supply": str(self._accounts[0].address),
                                                         "decimal": hex(18)})

        tx2 = self.create_deploy_score_tx(score_root="sample_deploy_scores",
                                          score_name=f"install/sample_token",
                                          from_=self._accounts[0],
                                          to_=SYSTEM_SCORE_ADDRESS,
                                          deploy_params={"init_supply": str(self._accounts[0].address),
                                                         "decimal": hex(18)})

        tx3 = self.create_deploy_score_tx(score_root="sample_deploy_scores",
                                          score_name=f"install/sample_token",
                                          from_=self._accounts[0],
                                          to_=SYSTEM_SCORE_ADDRESS,
                                          deploy_params={"init_supply": hex(1000),
                                                         "decimal": hex(18),
                                                         "address_param": f"hx{'1234' * 5}"})

        tx_results: List['TransactionResult'] = self.process_confirm_block_tx([tx1, tx2, tx3], expected_status=False)

        self.assertEqual(tx_results[0].failure.code, ExceptionCode.SYSTEM_ERROR)
        self.assertEqual(tx_results[1].failure.code, ExceptionCode.SYSTEM_ERROR)
        self.assertEqual(tx_results[2].failure.code, ExceptionCode.INVALID_PARAMETER)

    def test_invalid_kwargs_parameter_value_oninstall(self):
        self.update_governance()

        tx_results: List['TransactionResult'] = self.deploy_score(score_root="sample_deploy_scores",
                                                                  score_name=f"install/sample_legacy_kwargs_params",
                                                                  from_=self._accounts[0],
                                                                  to_=SYSTEM_SCORE_ADDRESS)
        score_addr = tx_results[0].score_address

        query_request = {
            "from": self._admin,
            "to": score_addr,
            "dataType": "call",
            "data": {
                "method": "hello",
            }
        }
        self.assertEqual(self._query(query_request), "Hello")

        self.set_revision(3)

        raise_exception_start_tag("sample_invalid_kwargs_parameter_value_oninstall")
        self.deploy_score(score_root="sample_deploy_scores",
                          score_name=f"install/sample_legacy_kwargs_params",
                          from_=self._accounts[0],
                          to_=SYSTEM_SCORE_ADDRESS,
                          expected_status=False)
        raise_exception_end_tag("sample_invalid_kwargs_parameter_value_oninstall")

