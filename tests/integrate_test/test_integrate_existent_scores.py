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
from typing import TYPE_CHECKING, Union, List, Optional

from iconcommons import IconConfig
from iconservice import ZERO_SCORE_ADDRESS, Address
from iconservice.base.address import generate_score_address, GOVERNANCE_SCORE_ADDRESS
from iconservice.icon_config import default_icon_config
from iconservice.icon_constant import ConfigKey, BUILTIN_SCORE_ADDRESS_MAPPER
from iconservice.icon_service_engine import IconServiceEngine
from tests.integrate_test import root_clear
from tests.integrate_test.test_integrate_base import TestIntegrateBase

if TYPE_CHECKING:
    from iconservice.iconscore.icon_score_result import TransactionResult

FILE_PATH = os.path.dirname(__file__)
PROJECT_ROOT_PATH = os.path.join(FILE_PATH, '..', '..')
BUILTIN_SCORE_SRC_ROOT_PATH = os.path.join(PROJECT_ROOT_PATH, 'iconservice', 'builtin_scores')
GOVERNANCE_SCORE_PATH = os.path.join(BUILTIN_SCORE_SRC_ROOT_PATH, 'governance')


class TestIntegrateExistentScores(TestIntegrateBase):

    # override setUp method for making directory before begin tests.
    def setUp(self):
        root_clear(self._score_root_path, self._state_db_root_path, self._iiss_db_root_path)
        self._block_height = -1
        self._prev_block_hash = None

        self.config = IconConfig("", default_icon_config)
        self.config.load()
        self.config.update_conf({ConfigKey.BUILTIN_SCORE_OWNER: str(self._admin.address)})
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

    def _make_directories_in_builtin_score_path(self):
        for score_name, address in BUILTIN_SCORE_ADDRESS_MAPPER.items():
            os.makedirs(os.path.join(self._score_root_path, f'01{address[2:]}', f"0x{'0' * 64}"), exist_ok=True)

    def _make_directory_using_address_and_hash(self, score_address: 'Address', tx_hash: bytes):
        tx_str = f"0x{bytes.hex(tx_hash)}"
        os.makedirs(os.path.join(self._score_root_path, f"01{str(score_address)[2:]}", tx_str))

    def _create_deploy_score_tx(self,
                                score_root: str,
                                score_name: str,
                                from_: Union['EOAAccount', 'Address', None],
                                to_: Union['EOAAccount', 'Address'],
                                deploy_params: dict) -> dict:
        addr_from: Optional['Address'] = self._convert_address_from_address_type(from_)
        addr_to: 'Address' = self._convert_address_from_address_type(to_)

        timestamp = int(time.time() * 10 ** 6)
        tx: dict = self.create_deploy_score_tx(score_root=score_root,
                                               score_name=score_name,
                                               from_=addr_from,
                                               to_=addr_to,
                                               deploy_params=deploy_params,
                                               timestamp_us=timestamp)
        score_address: 'Address' = generate_score_address(addr_from, timestamp, nonce=0)
        tx_hash: bytes = tx['params']['txHash']
        self._make_directory_using_address_and_hash(score_address, tx_hash)
        return tx

    def _deploy_score(self,
                      score_root: str,
                      score_name: str,
                      from_: Union['EOAAccount', 'Address', None],
                      to_: Union['EOAAccount', 'Address'],
                      deploy_params: dict,
                      expected_status: bool = True) -> List['TransactionResult']:
        tx: dict = self._create_deploy_score_tx(score_root=score_root,
                                                score_name=score_name,
                                                from_=from_,
                                                to_=to_,
                                                deploy_params=deploy_params)

        tx_results: List['TransactionResult'] = self.process_confirm_block_tx([tx], expected_status)
        return tx_results

    def test_existent_builtin_score(self):
        self._setUp()

        # original SCORE api
        original_governance_api: dict = self.get_score_api(GOVERNANCE_SCORE_ADDRESS)

        # update governance(revision2)
        self.update_governance("0_0_4")

        # updated SCORE api
        updated_governance_api: dict = self.get_score_api(GOVERNANCE_SCORE_ADDRESS)

        self.assertNotEqual(original_governance_api, updated_governance_api)

    def test_exists_score_revision3_abnormal_scores(self):
        self._setUp()

        self.update_governance("0_0_4")

        # set revision to 3
        self.set_revision(3)
        sample_score_params = {"value": hex(1000)}

        # deploy abnormal SCORE(not python)
        self._deploy_score(score_root="sample_deploy_scores",
                           score_name="install/test_score_no_python",
                           from_=self._accounts[0],
                           to_=ZERO_SCORE_ADDRESS,
                           deploy_params=sample_score_params,
                           expected_status=False)

        # deploy SCORE(has no external function)
        self._deploy_score(score_root="sample_deploy_scores",
                           score_name="install/test_score_no_external_func",
                           from_=self._accounts[0],
                           to_=ZERO_SCORE_ADDRESS,
                           deploy_params=sample_score_params,
                           expected_status=False)

        # deploy SCORE(no scorebase)
        self._deploy_score(score_root="sample_deploy_scores",
                           score_name="install/test_score_no_scorebase",
                           from_=self._accounts[0],
                           to_=ZERO_SCORE_ADDRESS,
                           deploy_params=sample_score_params,
                           expected_status=False)

        # deploy SCORE(on install error)
        self._deploy_score(score_root="sample_deploy_scores",
                           score_name="install/test_on_install_error",
                           from_=self._accounts[0],
                           to_=ZERO_SCORE_ADDRESS,
                           deploy_params=sample_score_params,
                           expected_status=False)

        # deploy SCORE(different encoding)
        self._deploy_score(score_root="sample_deploy_scores",
                           score_name="install/test_score_with_korean_comment",
                           from_=self._accounts[0],
                           to_=ZERO_SCORE_ADDRESS,
                           deploy_params=sample_score_params,
                           expected_status=False)
