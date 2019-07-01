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

"""IconServiceEngine testcase
"""

from typing import TYPE_CHECKING, Union, Optional, Any, List
from unittest import TestCase
from unittest.mock import Mock

from iconcommons import IconConfig

from iconservice.base.address import Address
from iconservice.base.block import Block
from iconservice.icon_config import default_icon_config
from iconservice.icon_constant import ConfigKey, IconScoreContextType, REV_DECENTRALIZATION
from iconservice.icon_service_engine import IconServiceEngine
from iconservice.iconscore.icon_score_context import IconScoreContext
from iconservice.iiss.reward_calc.ipc.reward_calc_proxy import RewardCalcProxy, CalculateResponse
from tests import create_address, create_tx_hash, create_block_hash
from tests.integrate_test import root_clear, create_timestamp, get_score_path
from tests.integrate_test.in_memory_zip import InMemoryZip

if TYPE_CHECKING:
    from iconservice.base.address import Address, MalformedAddress

LATEST_GOVERNANCE = "0_0_6/governance"


class TestIntegrateBase(TestCase):
    @classmethod
    def setUpClass(cls):
        cls._score_root_path = '.score'
        cls._state_db_root_path = '.statedb'
        cls._iiss_db_root_path = '.iissdb'

        cls._test_sample_root = "samples"
        cls._signature = "VAia7YZ2Ji6igKWzjR2YsGa2m53nKPrfK7uXYW78QLE+ATehAVZPC40szvAiA6NEU5gCYB4c4qaQzqDh2ugcHgA="

        cls._version = 3
        cls._step_limit = 1 * 10 ** 12
        cls._icx_factor = 10 ** 18

        cls._admin: 'Address' = create_address()
        cls._genesis: 'Address' = create_address()
        cls._fee_treasury: 'Address' = create_address()

        cls._addr_array = [create_address() for _ in range(20)]

    def setUp(self):
        root_clear(self._score_root_path, self._state_db_root_path, self._iiss_db_root_path)

        self._block_height = 0
        self._prev_block_hash = None

        config = IconConfig("", default_icon_config)
        config.load()
        config.update_conf({ConfigKey.BUILTIN_SCORE_OWNER: str(self._admin)})
        config.update_conf({ConfigKey.SERVICE: {ConfigKey.SERVICE_AUDIT: False,
                                                ConfigKey.SERVICE_FEE: False,
                                                ConfigKey.SERVICE_DEPLOYER_WHITE_LIST: False,
                                                ConfigKey.SERVICE_SCORE_PACKAGE_VALIDATOR: False}})
        config.update_conf({ConfigKey.SCORE_ROOT_PATH: self._score_root_path,
                            ConfigKey.STATE_DB_ROOT_PATH: self._state_db_root_path})
        config.update_conf(self._make_init_config())

        self.icon_service_engine = IconServiceEngine()

        self._mock_ipc()
        self.icon_service_engine.open(config)

        self._genesis_invoke()

    def mock_calculate(self, path, block_height):
        response = CalculateResponse(0, True, 1, 0, b'mocked_response')
        self._calculation_callback(response)

    def _mock_ipc(self, mock_calculate: callable = mock_calculate):
        RewardCalcProxy.open = Mock()
        RewardCalcProxy.start = Mock()
        RewardCalcProxy.stop = Mock()
        RewardCalcProxy.close = Mock()
        RewardCalcProxy.get_version = Mock()
        RewardCalcProxy.calculate = mock_calculate
        RewardCalcProxy.claim_iscore = Mock()
        RewardCalcProxy.query_iscore = Mock()
        RewardCalcProxy.commit_block = Mock()

    def tearDown(self):
        self.icon_service_engine.close()
        root_clear(self._score_root_path, self._state_db_root_path, self._iiss_db_root_path)

    def _make_init_config(self) -> dict:
        return {}

    def _genesis_invoke(self) -> tuple:
        tx_hash = create_tx_hash()
        timestamp_us = create_timestamp()
        request_params = {
            'txHash': tx_hash,
            'version': self._version,
            'timestamp': timestamp_us
        }

        tx = {
            'method': 'icx_sendTransaction',
            'params': request_params,
            'genesisData': {
                "accounts": [
                    {
                        "name": "genesis",
                        "address": self._genesis,
                        "balance": 1_000_000 * self._icx_factor
                    },
                    {
                        "name": "fee_treasury",
                        "address": self._fee_treasury,
                        "balance": 0
                    },
                    {
                        "name": "_admin",
                        "address": self._admin,
                        "balance": 1_000_000 * self._icx_factor
                    }
                ]
            },
        }

        block_hash = create_block_hash()
        block = Block(self._block_height, block_hash, timestamp_us, None, 0)
        invoke_response: tuple = self.icon_service_engine.invoke(
            block,
            [tx]
        )
        self.icon_service_engine.commit(block.height, block.hash, None)
        self._block_height += 1
        self._prev_block_hash = block_hash

        return invoke_response

    def _make_deploy_tx(self, score_root: str,
                        score_name: str,
                        addr_from: Union['Address', None],
                        addr_to: 'Address',
                        deploy_params: dict = None,
                        timestamp_us: int = None,
                        data: bytes = None,
                        is_sys: bool = False,
                        pre_validation_enabled: bool = True):

        if deploy_params is None:
            deploy_params = {}

        score_path = get_score_path(score_root, score_name)

        if is_sys:
            deploy_data = {'contentType': 'application/tbears', 'content': score_path, 'params': deploy_params}
        else:
            if data is None:
                mz = InMemoryZip()
                mz.zip_in_memory(score_path)
                data = f'0x{mz.data.hex()}'
            else:
                data = f'0x{bytes.hex(data)}'
            deploy_data = {'contentType': 'application/zip', 'content': data, 'params': deploy_params}

        if timestamp_us is None:
            timestamp_us = create_timestamp()
        nonce = 0

        request_params = {
            "version": self._version,
            "from": addr_from,
            "to": addr_to,
            "stepLimit": self._step_limit,
            "timestamp": timestamp_us,
            "nonce": nonce,
            "signature": self._signature,
            "dataType": "deploy",
            "data": deploy_data
        }

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

    def _make_score_call_tx(self,
                            addr_from: Optional['Address'],
                            addr_to: 'Address',
                            method: str,
                            params: dict,
                            value: int = 0,
                            pre_validation_enabled: bool = True):

        timestamp_us = create_timestamp()
        nonce = 0

        request_params = {
            "version": self._version,
            "from": addr_from,
            "to": addr_to,
            "value": value,
            "stepLimit": self._step_limit,
            "timestamp": timestamp_us,
            "nonce": nonce,
            "signature": self._signature,
            "dataType": "call",
            "data": {
                "method": method,
                "params": params
            }
        }

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

    def _make_icx_send_tx(self,
                          addr_from: Optional['Address'],
                          addr_to: Union['Address', 'MalformedAddress'],
                          value: int,
                          disable_pre_validate: bool = False,
                          support_v2: bool = False,
                          step_limit: int = -1):

        timestamp_us = create_timestamp()
        nonce = 0

        if step_limit < 0:
            step_limit = self._step_limit

        request_params = {
            "from": addr_from,
            "to": addr_to,
            "value": value,
            "stepLimit": step_limit,
            "timestamp": timestamp_us,
            "nonce": nonce,
            "signature": self._signature
        }

        if support_v2:
            request_params["fee"] = 10 ** 16
        else:
            request_params["version"] = self._version

        method = 'icx_sendTransaction'
        # Insert txHash into request params
        request_params['txHash'] = create_tx_hash()
        tx = {
            'method': method,
            'params': request_params
        }

        if not disable_pre_validate:
            self.icon_service_engine.validate_transaction(tx)
        return tx

    def _make_issue_tx(self,
                       data: dict):
        timestamp_us = create_timestamp()

        request_params = {
            "version": self._version,
            "timestamp": timestamp_us,
            "dataType": "issue",
            "data": data
        }
        method = 'icx_sendTransaction'
        request_params['txHash'] = create_tx_hash()
        tx = {
            'method': method,
            'params': request_params
        }

        return tx

    def _make_and_req_block(self,
                            tx_list: list,
                            block_height: int = None,
                            prev_block_generator: Optional['Address'] = None,
                            prev_block_validators: Optional[List['Address']] = None) -> tuple:
        if block_height is None:
            block_height: int = self._block_height
        block_hash = create_block_hash()
        timestamp_us = create_timestamp()

        block = Block(block_height, block_hash, timestamp_us, self._prev_block_hash, 0)
        context = IconScoreContext(IconScoreContextType.DIRECT)

        is_block_editable = False
        governance_score = self.icon_service_engine._get_governance_score(context)
        if hasattr(governance_score, 'revision_code') and governance_score.revision_code >= REV_DECENTRALIZATION:
            is_block_editable = True

        invoke_response, _, added_transactions, main_prep_as_dict = \
            self.icon_service_engine.invoke(block=block,
                                            tx_requests=tx_list,
                                            prev_block_generator=prev_block_generator,
                                            prev_block_validators=prev_block_validators,
                                            is_block_editable=is_block_editable)

        return block, invoke_response

    def _make_and_req_block_for_issue_test(self,
                                           tx_list: list,
                                           block_height: int = None,
                                           prev_block_generator: Optional['Address'] = None,
                                           prev_block_validators: Optional[List['Address']] = None,
                                           is_block_editable=False,
                                           cumulative_fee: int = 0) -> tuple:
        if block_height is None:
            block_height: int = self._block_height
        block_hash = create_block_hash()
        timestamp_us = create_timestamp()

        block = Block(block_height, block_hash, timestamp_us, self._prev_block_hash, cumulative_fee)

        invoke_response, _, added_transactions, main_prep_as_dict = \
            self.icon_service_engine.invoke(block=block,
                                            tx_requests=tx_list,
                                            prev_block_generator=prev_block_generator,
                                            prev_block_validators=prev_block_validators,
                                            is_block_editable=is_block_editable)

        return block, invoke_response

    def _make_and_req_block_for_prep_test(self,
                                          tx_list: list,
                                          block_height: int = None,
                                          prev_block_generator: Optional['Address'] = None,
                                          prev_block_validators: Optional[List['Address']] = None) -> tuple:
        if block_height is None:
            block_height: int = self._block_height
        block_hash = create_block_hash()
        timestamp_us = create_timestamp()

        block = Block(block_height, block_hash, timestamp_us, self._prev_block_hash, 0)
        context = IconScoreContext(IconScoreContextType.DIRECT)

        is_block_editable = False
        governance_score = self.icon_service_engine._get_governance_score(context)
        if hasattr(governance_score, 'revision_code') and governance_score.revision_code >= REV_DECENTRALIZATION:
            is_block_editable = True

        invoke_response, _, added_transactions, main_prep_as_dict = \
            self.icon_service_engine.invoke(block=block,
                                            tx_requests=tx_list,
                                            prev_block_generator=prev_block_generator,
                                            prev_block_validators=prev_block_validators,
                                            is_block_editable=is_block_editable)

        return block, invoke_response, main_prep_as_dict

    def _write_precommit_state(self, block: 'Block') -> None:
        self.icon_service_engine.commit(block.height, block.hash, None)
        self._block_height += 1
        self._prev_block_hash = block.hash

    def _remove_precommit_state(self, block: 'Block') -> None:
        self.icon_service_engine.rollback(block.height, block.hash)

    def _query(self, request: dict, method: str = 'icx_call') -> Any:
        response = self.icon_service_engine.query(method, request)
        return response

    def _create_invalid_block(self, block_height: int = None) -> 'Block':
        if block_height is None:
            block_height: int = self._block_height
        block_hash = create_block_hash()
        timestamp_us = create_timestamp()

        return Block(block_height, block_hash, timestamp_us, self._prev_block_hash, 0)
