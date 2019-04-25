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

from iconservice import ZERO_SCORE_ADDRESS, Address
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


class TestIntegrateExistentScores(TestIntegrateBase):

    # override setUp method for making directory before begin tests.
    def setUp(self):
        root_clear(self._score_root_path, self._state_db_root_path)
        self._block_height = 0
        self._prev_block_hash = None

        self.config = IconConfig("", default_icon_config)
        self.config.load()
        self.config.update_conf({ConfigKey.BUILTIN_SCORE_OWNER: str(self._admin)})
        self.config.update_conf({ConfigKey.SCORE_ROOT_PATH: self._score_root_path,
                                 ConfigKey.STATE_DB_ROOT_PATH: self._state_db_root_path})
        self.config.update_conf(self._make_init_config())

    def _setUp(self):
        self.config.update_conf({ConfigKey.SERVICE: {ConfigKey.SERVICE_AUDIT: False,
                                                     ConfigKey.SERVICE_FEE: False,
                                                     ConfigKey.SERVICE_DEPLOYER_WHITE_LIST: False,
                                                     ConfigKey.SERVICE_SCORE_PACKAGE_VALIDATOR: False}})
        self.icon_service_engine = IconServiceEngine()
        self.icon_service_engine.open(self.config)
        self._genesis_invoke()
        self.token_initial_params = {"init_supply": hex(1000), "decimal": "0x12"}

    def _update_governance(self, governance_path):
        tx = self._make_deploy_tx("sample_builtin", governance_path, self._admin, GOVERNANCE_SCORE_ADDRESS)
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))
        return tx['params']['txHash']

    def _set_revision(self, revision):
        set_revision_tx = self._make_score_call_tx(self._admin, GOVERNANCE_SCORE_ADDRESS, 'setRevision',
                                                   {"code": hex(revision), "name": f"1.1.{revision}"})
        prev_block, tx_results = self._make_and_req_block([set_revision_tx])
        self._write_precommit_state(prev_block)

    def _make_directories_in_builtin_score_path(self):
        for score_name, address in BUILTIN_SCORE_ADDRESS_MAPPER.items():
            os.makedirs(os.path.join(self._score_root_path, f'01{address[2:]}', f"0x{'0'*64}"), exist_ok=True)

    def _make_directory_using_address_and_hash(self, score_address: 'Address', tx_hash: bytes):
        tx_str = f"0x{bytes.hex(tx_hash)}"
        os.makedirs(os.path.join(self._score_root_path, f"01{str(score_address)[2:]}", tx_str))

    def _deploy_score(self, path: str, score_name: str, owner: 'Address', to: 'Address', deploy_params: dict):
        timestamp = int(time.time()*10**6)
        tx1 = self._make_deploy_tx(path, score_name, owner, to, deploy_params, timestamp)
        score_address = generate_score_address(owner, timestamp, nonce=0)
        tx_hash = tx1['params']['txHash']
        self._make_directory_using_address_and_hash(score_address, tx_hash)
        return tx1

    def _accept_score(self, tx_hash: bytes):
        tx = self._make_score_call_tx(self._admin, GOVERNANCE_SCORE_ADDRESS, 'acceptScore',
                                      params={"txHash": f'0x{bytes.hex(tx_hash)}'})
        prev_block, tx_results = self._make_and_req_block([tx])
        self._write_precommit_state(prev_block)
        return tx_results

    def test_existent_builtin_score(self):
        self._setUp()

        # original SCORE api
        query_request = {
            "address": GOVERNANCE_SCORE_ADDRESS,
        }
        original_governance_api = self._query(query_request, 'icx_getScoreApi')

        # update governance(revision2)
        self._update_governance('0_0_4')

        # updated SCORE api
        updated_governance_api = self._query(query_request, "icx_getScoreApi")

        self.assertNotEqual(original_governance_api, updated_governance_api)

    # test when revision <= 2
    def test_existent_score(self):
        self._setUp()

        # deploy SCORE
        tx1 = self._deploy_score('sample_deploy_scores/install', 'sample_token', self._addr_array[0], ZERO_SCORE_ADDRESS,
                                 self.token_initial_params)

        prev_block, tx_results = self._make_and_req_block([tx1])
        self._write_precommit_state(prev_block)
        self.assertTrue("is a directory. Check " in tx_results[0].failure.message)
        self.assertEqual(tx_results[0].status, int(False))

        # update governance SCORE(revision2)
        self._update_governance('0_0_4')
        # deploy
        tx2 = self._deploy_score("sample_deploy_scores/install", "sample_token", self._addr_array[0], ZERO_SCORE_ADDRESS,
                                 self.token_initial_params)

        prev_block, tx_results = self._make_and_req_block([tx2])
        self._write_precommit_state(prev_block)
        self.assertTrue("is a directory. Check " in tx_results[0].failure.message)
        self.assertEqual(tx_results[0].status, int(False))

    # test when revision > 2
    def test_existent_score_revision4(self):
        self._setUp()

        # set revision to 4(revision4)
        self._update_governance('0_0_4')
        self._set_revision(3)

        # deploy SCORE
        tx1 = self._deploy_score("sample_deploy_scores/install", "sample_token", self._addr_array[0], ZERO_SCORE_ADDRESS,
                                 self.token_initial_params)

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

        # deploy SCORE(update)
        tx2 = self._deploy_score("sample_deploy_scores/install", "sample_token", self._addr_array[0], score_addr1,
                                 {"update_supply": hex(3000), "decimal": "0x12"})
        prev_block, tx_results = self._make_and_req_block([tx2])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))

        # balance_of test(3000)
        query_request['data']['params']['addr_from'] = str(self._addr_array[0])
        response = self._query(query_request)
        self.assertEqual(response, 3000 * 10 ** 18)

    def test_rolling_update_deploy(self):
        # case revision 0
        self._setUp()

        # deploy (revision0 must be fail)
        tx1 = self._deploy_score("sample_deploy_scores/install", "sample_token", self._addr_array[0], ZERO_SCORE_ADDRESS,
                                 self.token_initial_params)

        prev_block, tx_results = self._make_and_req_block([tx1])
        self._write_precommit_state(prev_block)
        self.assertTrue("is a directory. Check " in tx_results[0].failure.message)
        self.assertEqual(tx_results[0].status, int(False))

        # update governance SCORE(revision 2)
        self._update_governance('0_0_4')
        # deploy (revision2 must be fail)
        tx2 = self._deploy_score("sample_deploy_scores/install", "sample_token", self._addr_array[0], ZERO_SCORE_ADDRESS,
                                 self.token_initial_params)

        prev_block, tx_results = self._make_and_req_block([tx2])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(False))

        # set revision to 4
        self._set_revision(3)

        # deploy(revision3 must be success)
        tx4 = self._deploy_score("sample_deploy_scores/install", "sample_token", self._addr_array[0], ZERO_SCORE_ADDRESS,
                                 self.token_initial_params)

        prev_block, tx_results = self._make_and_req_block([tx4])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(True))

    def test_exists_score_revision3_unnormal_scores(self):
        self._setUp()

        # set revision to 3
        self._set_revision(3)
        sample_score_init_params = {"value": hex(1000)}

        # deploy unnormal SCORE(not python)
        tx1 = self._deploy_score("sample_deploy_scores/install", "test_score_no_python", self._addr_array[0],
                                 ZERO_SCORE_ADDRESS, sample_score_init_params)

        prev_block, tx_results = self._make_and_req_block([tx1])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(False))

        # deploy SCORE(has no external function)
        tx2 = self._deploy_score("sample_deploy_scores/install", "test_score_no_external_func", self._addr_array[0],
                                 ZERO_SCORE_ADDRESS, sample_score_init_params)

        prev_block, tx_results = self._make_and_req_block([tx2])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(False))

        # deploy SCORE(no scorebase)
        tx3 = self._deploy_score("sample_deploy_scores/install", "test_score_no_scorebase", self._addr_array[0],
                                 ZERO_SCORE_ADDRESS, sample_score_init_params)
        prev_block, tx_results = self._make_and_req_block([tx3])

        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(False))

        # deploy SCORE(on install error)
        tx4 = self._deploy_score("sample_deploy_scores/install", "test_on_install_error", self._addr_array[0],
                                 ZERO_SCORE_ADDRESS, sample_score_init_params)

        prev_block, tx_results = self._make_and_req_block([tx4])
        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(False))

        # deploy SCORE(different encoding)
        tx5 = self._deploy_score("sample_deploy_scores/install", "test_score_with_korean_comment", self._addr_array[0],
                                 ZERO_SCORE_ADDRESS, sample_score_init_params)
        prev_block, tx_results = self._make_and_req_block([tx5])

        self._write_precommit_state(prev_block)
        self.assertEqual(tx_results[0].status, int(False))
