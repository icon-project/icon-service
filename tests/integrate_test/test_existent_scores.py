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
import os
import time

from iconcommons import IconConfig

from iconservice import ZERO_SCORE_ADDRESS
from iconservice.base.address import generate_score_address, GOVERNANCE_SCORE_ADDRESS
from iconservice.icon_config import default_icon_config
from iconservice.icon_constant import ConfigKey, BUILTIN_SCORE_ADDRESS_MAPPER
from iconservice.icon_service_engine import IconServiceEngine
from tests.integrate_test import root_clear
from tests.integrate_test.test_integrate_base import TestIntegrateBase

FILE_PATH = os.path.dirname(__file__)
PROJECT_ROOT_PATH = os.path.join(FILE_PATH, '..', '..')
BUILTIN_SCORE_SRC_ROOT_PATH = os.path.join(PROJECT_ROOT_PATH, 'iconservice', 'builtin_scores')
GOVERNANCE_SCORE_PATH = os.path.join(BUILTIN_SCORE_SRC_ROOT_PATH, 'governance')


class TestA(TestIntegrateBase):

    def setUp(self):
        root_clear(self._score_root_path, self._state_db_root_path)

    def _setUp(self):
        self._block_height = 0
        self._prev_block_hash = None

        config = IconConfig("", default_icon_config)
        config.load()
        config.update_conf({ConfigKey.BUILTIN_SCORE_OWNER: str(self._admin)})
        config.update_conf({ConfigKey.SERVICE: {ConfigKey.SERVICE_AUDIT: False,
                                                ConfigKey.SERVICE_FEE: False,
                                                ConfigKey.SERVICE_DEPLOYER_WHITELIST: False,
                                                ConfigKey.SERVICE_SCORE_PACKAGE_VALIDATOR: False}})
        config.update_conf({ConfigKey.SCORE_ROOT_PATH: self._score_root_path,
                            ConfigKey.STATE_DB_ROOT_PATH: self._state_db_root_path})
        config.update_conf(self._make_init_config())

        self.icon_service_engine = IconServiceEngine()
        self.icon_service_engine.open(config)

        self._genesis_invoke()

    def test_exists_builtin_score(self):
        for score_name, address in BUILTIN_SCORE_ADDRESS_MAPPER.items():
            os.makedirs(os.path.join(self._score_root_path, f'01{address[2:]}', f"0x{'0'*64}"), exist_ok=True)

        self._setUp()

        # original score api
        query_request = {
            "address": GOVERNANCE_SCORE_ADDRESS,
        }
        original_governance_api = self._query(query_request, 'icx_getScoreApi')

        # update governance
        tx1 = self._make_deploy_tx("test_deploy_scores/install",
                                   "sample_token",
                                   self._admin,
                                   GOVERNANCE_SCORE_ADDRESS,
                                   deploy_params={"update_supply": hex(3000), "decimal": "0x12"})

        prev_block, tx_results = self._make_and_req_block([tx1])

        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))

        # updated score api
        query_request = {
            "address": GOVERNANCE_SCORE_ADDRESS
        }
        updated_governance_api = self._query(query_request, "icx_getScoreApi")

        self.assertNotEqual(original_governance_api, updated_governance_api)

    def test_exists_score(self):
        self._setUp()

        # deploy
        timestamp = int(time.time()*10**6)
        tx1 = self._make_deploy_tx("test_deploy_scores/install",
                                   "sample_token",
                                   self._addr_array[0],
                                   ZERO_SCORE_ADDRESS, deploy_params={"init_supply": hex(1000), "decimal": "0x12"},
                                   timestamp_us=timestamp)

        score_address = generate_score_address(self._addr_array[0], timestamp, nonce=0)
        tx_str = f"0x{bytes.hex(tx1['params']['txHash'])}"
        os.makedirs(os.path.join(self._score_root_path, f"01{str(score_address)[2:]}", tx_str))

        prev_block, tx_results = self._make_and_req_block([tx1])

        self._write_precommit_state(prev_block)

        self.assertEqual(tx_results[0].status, int(True))
        score_addr1 = tx_results[0].score_address

        # balance_of test(1000)
        query_request = {
            "from": self._admin,
            "to": score_addr1,
            "dataType": "call",
            "data": {
                "method": "balance_of",
                "params": {
                    "addr_from": str(self._addr_array[0])
                }
            }
        }
        response = self._query(query_request)
        self.assertEqual(response, 1000 * 10 ** 18)

        # deploy(update)
        tx1 = self._make_deploy_tx("test_deploy_scores/install",
                                   "sample_token",
                                   self._addr_array[0],
                                   score_addr1, deploy_params={"update_supply": hex(3000), "decimal": "0x12"})

        prev_block, tx_results = self._make_and_req_block([tx1])

        self._write_precommit_state(prev_block)

        self.assertEqual(tx_results[0].status, int(True))
        score_addr1 = tx_results[0].score_address

        # balance_of test(3000)
        query_request = {
            "from": self._admin,
            "to": score_addr1,
            "dataType": "call",
            "data": {
                "method": "balance_of",
                "params": {
                    "addr_from": str(self._addr_array[0])
                }
            }
        }
        response = self._query(query_request)
        self.assertEqual(response, 3000 * 10 ** 18)
