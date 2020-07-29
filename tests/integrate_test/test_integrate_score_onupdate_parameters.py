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

"""on_update parameters testcase"""

from typing import TYPE_CHECKING, List

from iconservice.base.address import SYSTEM_SCORE_ADDRESS, Address
from iconservice.base.exception import ExceptionCode
from tests.integrate_test.test_integrate_base import TestIntegrateBase

if TYPE_CHECKING:
    from iconservice.iconscore.icon_score_result import TransactionResult


class TestIntegrateOnUpdateParameters(TestIntegrateBase):

    def _deploy_score(self,
                      deploy_params: dict,
                      to_: 'Address' = SYSTEM_SCORE_ADDRESS,
                      expected_status: bool = True) -> List['TransactionResult']:
        return self.deploy_score(score_root="sample_deploy_scores",
                                 score_name=f"install/sample_token",
                                 from_=self._accounts[0],
                                 to_=to_,
                                 deploy_params=deploy_params,
                                 expected_status=expected_status)

    def _create_init_deploy_tx(self,
                               deploy_params: dict,
                               to_: 'Address' = SYSTEM_SCORE_ADDRESS,
                               count: int = 1) -> List[dict]:
        return [self.create_deploy_score_tx(score_root="sample_deploy_scores",
                                            score_name="install/sample_token",
                                            from_=self._accounts[0],
                                            to_=to_,
                                            deploy_params=deploy_params)
                for _ in range(count)]

    def test_onupdate_parameters_success(self):
        init_supply: int = 1000
        decimal: int = 18

        # deploy
        tx_results: List['TransactionResult'] = self._deploy_score(deploy_params={"init_supply": hex(init_supply),
                                                                                  "decimal": hex(decimal)})
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

        update_supply: int = 2000
        tx_results: List['TransactionResult'] = self._deploy_score(to_=score_addr1,
                                                                   deploy_params={"update_supply": hex(update_supply),
                                                                                  "decimal": hex(decimal)})
        total_supply = self._query(query_request)
        self.assertEqual(total_supply, update_supply * 10 ** decimal)

    def test_more_parameters_onupdate(self):
        init_supply: int = 1000
        decimal: int = 18

        # deploy
        tx_results: List['TransactionResult'] = self._deploy_score(deploy_params={"init_supply": hex(init_supply),
                                                                                  "decimal": hex(decimal)})
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

        update_supply: int = 2000
        tx_results: List['TransactionResult'] = self._deploy_score(to_=score_addr1,
                                                                   deploy_params={"update_supply": hex(update_supply),
                                                                                  "decimal": hex(decimal),
                                                                                  "additional_param": hex(123)},
                                                                   expected_status=False)
        self.assertEqual(tx_results[0].failure.code, ExceptionCode.INVALID_PARAMETER)

        total_supply = self._query(query_request)
        self.assertEqual(total_supply, init_supply * 10 ** decimal)

    def test_missing_parameters_onupdate(self):
        init_supply: int = 1000
        decimal: int = 18
        count: int = 3
        # deploy
        tx_list: List[dict] = self._create_init_deploy_tx(deploy_params={"init_supply": hex(init_supply),
                                                                         "decimal": hex(decimal)},
                                                          count=count)
        tx_results0: List['TransactionResult'] = self.process_confirm_block_tx(tx_list)

        for i in range(count):
            query_request = {
                "from": self._admin,
                "to": tx_results0[i].score_address,
                "dataType": "call",
                "data": {
                    "method": "total_supply",
                }
            }
            total_supply = self._query(query_request)
            self.assertEqual(total_supply, init_supply * 10 ** decimal)

        tx_list: List[dict] = []
        tx_list.extend(self._create_init_deploy_tx(deploy_params={"decimal": hex(18)},
                                                   to_=tx_results0[0].score_address))
        tx_list.extend(self._create_init_deploy_tx(deploy_params={"update_supply": hex(1000)},
                                                   to_=tx_results0[1].score_address))
        tx_list.extend(self._create_init_deploy_tx(deploy_params={},
                                                   to_=tx_results0[2].score_address))

        tx_results: List['TransactionResult'] = self.process_confirm_block_tx(tx_list,
                                                                              expected_status=False)

        self.assertEqual(ExceptionCode.INVALID_PARAMETER, tx_results[0].failure.code, ExceptionCode.SYSTEM_ERROR)
        self.assertEqual(ExceptionCode.INVALID_PARAMETER, tx_results[1].failure.code, ExceptionCode.SYSTEM_ERROR)
        self.assertEqual(ExceptionCode.INVALID_PARAMETER, tx_results[2].failure.code, ExceptionCode.SYSTEM_ERROR)

        for i in range(count):
            query_request = {
                "from": self._admin,
                "to": tx_results0[i].score_address,
                "dataType": "call",
                "data": {
                    "method": "total_supply",
                }
            }
            total_supply = self._query(query_request)
            self.assertEqual(total_supply, init_supply * 10 ** decimal)

    def test_invalid_parameter_value_onupdate(self):
        init_supply: int = 1000
        decimal: int = 18
        count: int = 2
        # deploy
        tx_list: List[dict] = self._create_init_deploy_tx(deploy_params={"init_supply": hex(init_supply),
                                                                         "decimal": hex(decimal)},
                                                          count=count)
        tx_results0: List['TransactionResult'] = self.process_confirm_block_tx(tx_list)

        for i in range(count):
            query_request = {
                "from": self._admin,
                "to": tx_results0[i].score_address,
                "dataType": "call",
                "data": {
                    "method": "total_supply",
                }
            }
            total_supply = self._query(query_request)
            self.assertEqual(total_supply, init_supply * 10 ** decimal)

        tx_list: List[dict] = []
        tx_list.extend(self._create_init_deploy_tx(deploy_params={"update_supply": str(self._accounts[0].address),
                                                                  "decimal": hex(18)},
                                                   to_=tx_results0[0].score_address))
        tx_list.extend(self._create_init_deploy_tx(deploy_params={"update_supply": hex(2000), "decimal": hex(18),
                                                                  "address_param": hex(12345)},
                                                   to_=tx_results0[1].score_address))

        tx_results: List['TransactionResult'] = self.process_confirm_block_tx(tx_list,
                                                                              expected_status=False)

        self.assertEqual(tx_results[0].failure.code, ExceptionCode.SYSTEM_ERROR)
        self.assertEqual(tx_results[1].failure.code, ExceptionCode.INVALID_PARAMETER)

        self.assertTrue(tx_results[0].failure.message.find("invalid literal for int()") != -1)
        self.assertTrue(tx_results[1].failure.message.find("Invalid address") != -1)

        for i in range(count):
            query_request = {
                "from": self._admin,
                "to": tx_results0[i].score_address,
                "dataType": "call",
                "data": {
                    "method": "total_supply",
                }
            }
            total_supply = self._query(query_request)
            self.assertEqual(total_supply, init_supply * 10 ** decimal)
