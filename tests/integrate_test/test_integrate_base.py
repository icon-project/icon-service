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
import copy
from typing import TYPE_CHECKING, Union, Optional, Any, List, Tuple
from unittest import TestCase
from unittest.mock import Mock

from iconcommons import IconConfig
from iconsdk.wallet.wallet import KeyWallet

from iconservice.base.address import ZERO_SCORE_ADDRESS, GOVERNANCE_SCORE_ADDRESS, Address, MalformedAddress
from iconservice.base.block import Block
from iconservice.fee.engine import FIXED_TERM
from iconservice.icon_config import default_icon_config
from iconservice.icon_constant import ConfigKey, IconScoreContextType, RCCalculateResult
from iconservice.icon_service_engine import IconServiceEngine
from iconservice.iconscore.icon_score_context import IconScoreContext
from iconservice.iiss.reward_calc.ipc.reward_calc_proxy import RewardCalcProxy, CalculateDoneNotification
from iconservice.utils import bytes_to_hex
from iconservice.utils import icx_to_loop
from tests import create_address, create_tx_hash, create_block_hash
from tests.integrate_test import root_clear, create_timestamp, get_score_path
from tests.integrate_test.in_memory_zip import InMemoryZip

if TYPE_CHECKING:
    from iconservice.iconscore.icon_score_result import TransactionResult

LATEST_GOVERNANCE = "0_0_6"

TOTAL_SUPPLY = 800_460_000
MINIMUM_STEP_LIMIT = 1 * 10 ** 6
DEFAULT_STEP_LIMIT = 2 * 10 ** 6
DEFAULT_BIG_STEP_LIMIT = 1 * 10 ** 8
DEFAULT_DEPLOY_STEP_LIMIT = 1 * 10 ** 12


class TestIntegrateBase(TestCase):

    @classmethod
    def setUpClass(cls):
        cls._score_root_path = '.score'
        cls._state_db_root_path = '.statedb'
        cls._iiss_db_root_path = '.iissdb'

        cls._test_sample_root = "samples"
        cls._signature = "VAia7YZ2Ji6igKWzjR2YsGa2m53nKPrfK7uXYW78QLE+ATehAVZPC40szvAiA6NEU5gCYB4c4qaQzqDh2ugcHgA="

        cls._version = 3

        cls._admin: 'EOAAccount' = cls.create_eoa_accounts(1)[0]
        cls._genesis: 'Address' = create_address()
        cls._fee_treasury: 'Address' = create_address()

        cls._accounts = cls.create_eoa_accounts(100)

        cls._tx_results: dict = {}

    def setUp(self):
        root_clear(self._score_root_path, self._state_db_root_path, self._iiss_db_root_path)

        self._block_height = -1
        self._prev_block_hash = None

        config = IconConfig("", copy.deepcopy(default_icon_config))

        config.load()
        config.update_conf({ConfigKey.BUILTIN_SCORE_OWNER: str(self._admin.address)})
        config.update_conf({ConfigKey.SERVICE: {ConfigKey.SERVICE_AUDIT: False,
                                                ConfigKey.SERVICE_FEE: False,
                                                ConfigKey.SERVICE_DEPLOYER_WHITE_LIST: False,
                                                ConfigKey.SERVICE_SCORE_PACKAGE_VALIDATOR: False}})
        config.update_conf({ConfigKey.SCORE_ROOT_PATH: self._score_root_path,
                            ConfigKey.STATE_DB_ROOT_PATH: self._state_db_root_path})
        config.update_conf(self._make_init_config())

        self._config: 'IconConfig' = config

        self.icon_service_engine = IconServiceEngine()

        self._mock_ipc()
        self.icon_service_engine.open(config)

        self._genesis_invoke()

    def get_block_height(self) -> int:
        return self._block_height

    def mock_calculate(self, _path, _block_height):
        context: 'IconScoreContext' = IconScoreContext(IconScoreContextType.QUERY)
        end_block_height_of_calc: int = context.storage.iiss.get_end_block_height_of_calc(context)
        calc_period: int = context.storage.iiss.get_calc_period(context)
        response = CalculateDoneNotification(0, True, end_block_height_of_calc - calc_period, 0, b'mocked_response')
        self._calculate_done_callback(response)

    def _calculate_done_callback(self, response: 'CalculateDoneNotification'):
        pass

    @classmethod
    def _mock_ipc(cls, mock_calculate: callable = mock_calculate):
        RewardCalcProxy.open = Mock()
        RewardCalcProxy.start = Mock()
        RewardCalcProxy.stop = Mock()
        RewardCalcProxy.close = Mock()
        RewardCalcProxy.get_version = Mock()
        RewardCalcProxy.calculate = mock_calculate
        RewardCalcProxy.claim_iscore = Mock()
        RewardCalcProxy.query_iscore = Mock()
        RewardCalcProxy.commit_block = Mock()
        RewardCalcProxy.commit_claim = Mock()
        RewardCalcProxy.query_calculate_result = Mock(return_value=(RCCalculateResult.SUCCESS, 0, 0, bytes()))

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
                        "balance": 0
                    },
                    {
                        "name": "fee_treasury",
                        "address": self._fee_treasury,
                        "balance": 0
                    },
                    {
                        "name": "_admin",
                        "address": self._admin.address,
                        "balance": icx_to_loop(TOTAL_SUPPLY)
                    }
                ]
            },
        }

        block_hash = create_block_hash()
        block = Block(self._block_height + 1, block_hash, timestamp_us, None, 0)
        invoke_response: tuple = self.icon_service_engine.invoke(
            block,
            [tx]
        )
        self.icon_service_engine.commit(block.height, block.hash, None)
        self._block_height += 1
        self._prev_block_hash = block_hash

        return invoke_response

    def get_tx_results(self, hash_list: List[bytes]):
        tx_results: List['TransactionResult'] = []
        for tx_hash in hash_list:
            tx_results.append(self._tx_results[tx_hash])
        return tx_results

    @classmethod
    def get_hash_list_from_tx_list(cls, tx_list: list) -> List[bytes]:
        hash_list: list = []
        for tx in tx_list:
            hash_list.append(tx['params']['txHash'])
        return hash_list

    def add_tx_result(self, tx_results: List['TransactionResult']):
        for tx_result in tx_results:
            self._tx_results[tx_result.tx_hash] = tx_result

    def make_and_req_block(self,
                           tx_list: list,
                           block_height: int = None,
                           prev_block_generator: Optional['Address'] = None,
                           prev_block_validators: Optional[List['Address']] = None,
                           prev_block_votes: Optional[List[Tuple['Address', int]]] = None,
                           block_hash: bytes = None) \
            -> Tuple['Block', List[bytes]]:
        if block_height is None:
            block_height: int = self._block_height + 1
        if block_hash is None:
            block_hash = create_block_hash()
        timestamp_us = create_timestamp()

        block = Block(block_height, block_hash, timestamp_us, self._prev_block_hash, 0)
        context = IconScoreContext(IconScoreContextType.DIRECT)
        context._system_value = context.engine.system.system_value
        context._term = context.engine.prep.term
        is_block_editable = False
        if context.is_decentralized():
            is_block_editable = True

        tx_results, state_root_hash, added_transactions, main_prep_as_dict = \
            self.icon_service_engine.invoke(block=block,
                                            tx_requests=tx_list,
                                            prev_block_generator=prev_block_generator,
                                            prev_block_validators=prev_block_validators,
                                            prev_block_votes=prev_block_votes,
                                            is_block_editable=is_block_editable)

        self.add_tx_result(tx_results)
        return block, self.get_hash_list_from_tx_list(tx_list)

    def debug_make_and_req_block(self,
                                 tx_list: list,
                                 prev_block_generator: Optional['Address'] = None,
                                 prev_block_validators: Optional[List['Address']] = None,
                                 prev_block_votes: Optional[List[Tuple['Address', int]]] = None,
                                 block: 'Block' = None) -> tuple:

        # Prevent a base transaction from being added to the original tx_list
        tx_list = copy.copy(tx_list)

        if block is None:
            block_height: int = self._block_height + 1
            block_hash = create_block_hash()
            timestamp_us = create_timestamp()
            block = Block(block_height, block_hash, timestamp_us, self._prev_block_hash, 0)

        context = IconScoreContext(IconScoreContextType.DIRECT)
        context._system_value = context.engine.system.system_value
        context._term = context.engine.prep.term
        is_block_editable = False
        if context.is_decentralized():
            is_block_editable = True

        tx_results, state_root_hash, added_transactions, main_prep_as_dict = \
            self.icon_service_engine.invoke(block=block,
                                            tx_requests=tx_list,
                                            prev_block_generator=prev_block_generator,
                                            prev_block_validators=prev_block_validators,
                                            prev_block_votes=prev_block_votes,
                                            is_block_editable=is_block_editable)

        return block, tx_results, state_root_hash, added_transactions, main_prep_as_dict

    def _make_and_req_block_for_issue_test(self,
                                           tx_list: list,
                                           block_height: int = None,
                                           prev_block_generator: Optional['Address'] = None,
                                           prev_block_validators: Optional[List['Address']] = None,
                                           prev_block_votes: Optional[List[Tuple['Address', int]]] = None,
                                           is_block_editable=False,
                                           cumulative_fee: int = 0) -> Tuple['Block', List[bytes]]:
        if block_height is None:
            block_height: int = self._block_height + 1
        block_hash = create_block_hash()
        timestamp_us = create_timestamp()

        block = Block(block_height, block_hash, timestamp_us, self._prev_block_hash, cumulative_fee)

        tx_results, _, added_transactions, main_prep_as_dict = \
            self.icon_service_engine.invoke(block=block,
                                            tx_requests=tx_list,
                                            prev_block_generator=prev_block_generator,
                                            prev_block_validators=prev_block_validators,
                                            prev_block_votes=prev_block_votes,
                                            is_block_editable=is_block_editable)

        self.add_tx_result(tx_results)

        return block, self.get_hash_list_from_tx_list(tx_list)

    def _write_precommit_state(self, block: 'Block') -> None:
        self.icon_service_engine.commit(block.height, block.hash, None)
        self._block_height += 1
        assert block.height == self._block_height
        self._prev_block_hash = block.hash

    def _remove_precommit_state(self, block: 'Block') -> None:
        """Revoke to commit the precommit data to db

        """
        self.icon_service_engine.remove_precommit_state(block.height, block.hash)

    def rollback(self, block_height: int = -1, block_hash: Optional[bytes] = None):
        """Rollback the current state to the old one indicated by a given block

        :param block_height: the final block height after rollback
        :param block_hash: the final block hash after rollback
        """
        self.icon_service_engine.rollback(block_height, block_hash)

        self._block_height = block_height
        self._prev_block_hash = block_hash

    def _query(self, request: dict, method: str = 'icx_call') -> Any:
        response = self.icon_service_engine.query(method, request)
        return response

    def inner_call(self, request: dict) -> Any:
        response = self.icon_service_engine.inner_call(request)
        return response

    def _create_invalid_block(self, block_height: int = None) -> 'Block':
        if block_height is None:
            block_height: int = self._block_height
        block_hash = create_block_hash()
        timestamp_us = create_timestamp()

        return Block(block_height, block_hash, timestamp_us, self._prev_block_hash, 0)

    @classmethod
    def _convert_address_from_address_type(cls,
                                           from_: Union[
                                               'EOAAccount',
                                               'Address',
                                               'MalformedAddress',
                                               None]
                                           ) -> Union['Address', 'MalformedAddress', None]:
        if isinstance(from_, EOAAccount):
            return from_.address
        elif isinstance(from_, (Address, MalformedAddress)):
            return from_
        else:
            return None

    # ====== API ===== #
    def process_confirm_block_tx(self,
                                 tx_list: list,
                                 expected_status: bool = True,
                                 prev_block_generator: Optional['Address'] = None,
                                 prev_block_validators: Optional[List['Address']] = None,
                                 prev_block_votes: Optional[List[Tuple['Address', int]]] = None,
                                 block_height: int = None) -> List['TransactionResult']:

        prev_block, hash_list = self.make_and_req_block(tx_list,
                                                        block_height,
                                                        prev_block_generator,
                                                        prev_block_validators,
                                                        prev_block_votes)
        self._write_precommit_state(prev_block)
        tx_results: List['TransactionResult'] = self.get_tx_results(hash_list)
        for tx_result in tx_results:
            self.assertEqual(int(expected_status), tx_result.status)
        return tx_results

    def process_confirm_block(self,
                              tx_list: list,
                              prev_block_generator: Optional['Address'] = None,
                              prev_block_validators: Optional[List['Address']] = None,
                              prev_block_votes: Optional[List[Tuple['Address', int]]] = None,
                              block_height: int = None) -> List['TransactionResult']:

        prev_block, hash_list = self.make_and_req_block(tx_list,
                                                        block_height,
                                                        prev_block_generator,
                                                        prev_block_validators,
                                                        prev_block_votes)
        self._write_precommit_state(prev_block)
        tx_results: List['TransactionResult'] = self.get_tx_results(hash_list)
        return tx_results

    def create_deploy_score_tx(self,
                               score_root: str,
                               score_name: str,
                               from_: Union['EOAAccount', 'Address', None],
                               to_: Union['EOAAccount', 'Address'],
                               deploy_params: dict = None,
                               timestamp_us: int = None,
                               data: bytes = None,
                               is_sys: bool = False,
                               pre_validation_enabled: bool = True,
                               step_limit: int = DEFAULT_DEPLOY_STEP_LIMIT) -> dict:

        addr_from: Optional['Address'] = self._convert_address_from_address_type(from_)
        addr_to: 'Address' = self._convert_address_from_address_type(to_)

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
            "stepLimit": step_limit,
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

    def create_score_call_tx(self,
                             from_: Union['EOAAccount', 'Address', None],
                             to_: 'Address',
                             func_name: str,
                             params: Optional[dict] = None,
                             value: int = 0,
                             pre_validation_enabled: bool = True,
                             step_limit: int = DEFAULT_BIG_STEP_LIMIT) -> dict:

        from_: Optional['Address'] = self._convert_address_from_address_type(from_)
        if params is None:
            params: dict = {}

        timestamp_us = create_timestamp()
        nonce = 0

        request_params = {
            "version": self._version,
            "from": from_,
            "to": to_,
            "value": value,
            "stepLimit": step_limit,
            "timestamp": timestamp_us,
            "nonce": nonce,
            "signature": self._signature,
            "dataType": "call",
            "data": {
                "method": func_name,
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

    def create_transfer_icx_tx(self,
                               from_: Union['EOAAccount', 'Address', None],
                               to_: Union['EOAAccount', 'Address', 'MalformedAddress'],
                               value: int,
                               disable_pre_validate: bool = False,
                               support_v2: bool = False,
                               step_limit: int = DEFAULT_STEP_LIMIT) -> dict:

        addr_from: Optional['Address'] = self._convert_address_from_address_type(from_)
        addr_to: Optional['Address', 'MalformedAddress'] = self._convert_address_from_address_type(to_)

        timestamp_us = create_timestamp()
        nonce = 0

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

    def create_message_tx(self,
                          from_: Union['EOAAccount', 'Address', None],
                          to_: Union['EOAAccount', 'Address', 'MalformedAddress'],
                          data: bytes = None,
                          value: int = 0) -> dict:

        addr_from: Optional['Address'] = self._convert_address_from_address_type(from_)
        addr_to: Optional['Address', 'MalformedAddress'] = self._convert_address_from_address_type(to_)

        timestamp_us = create_timestamp()
        nonce = 0

        request_params = {
            "version": self._version,
            "from": addr_from,
            "to": addr_to,
            "value": value,
            "stepLimit": DEFAULT_BIG_STEP_LIMIT,
            "timestamp": timestamp_us,
            "nonce": nonce,
            "signature": self._signature,
            "dataType": "message",
            "data": '0x' + data.hex(),
        }

        method = 'icx_sendTransaction'
        # Inserts txHash into request params
        request_params['txHash'] = create_tx_hash()
        tx = {
            'method': method,
            'params': request_params
        }

        self.icon_service_engine.validate_transaction(tx)
        return tx

    def create_deposit_tx(self,
                          from_: Union['EOAAccount', 'Address', None],
                          to_: 'Address',
                          action: str,
                          params: dict,
                          value: int = 0,
                          pre_validation_enabled: bool = True,
                          step_limit: int = DEFAULT_BIG_STEP_LIMIT) -> dict:

        addr_from: Optional['Address'] = self._convert_address_from_address_type(from_)
        addr_to: 'Address' = self._convert_address_from_address_type(to_)

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

    def create_register_proposal_tx(self,
                                    from_: 'Address',
                                    title: str,
                                    description: str,
                                    type_: int,
                                    value: Union[str, int, 'Address'],
                                    step_limit: int = DEFAULT_BIG_STEP_LIMIT) -> dict:
        text = '{"address":"%s"}' % value
        json_data: bytes = text.encode("utf-8")

        method = "registerProposal"
        score_params = {
            "title": title,
            "description": description,
            "type": hex(type_),
            "value": bytes_to_hex(json_data)
        }

        return self.create_score_call_tx(from_=from_,
                                         to_=GOVERNANCE_SCORE_ADDRESS,
                                         func_name=method,
                                         params=score_params,
                                         step_limit=step_limit)

    def create_vote_proposal_tx(self,
                                from_: 'Address',
                                id_: bytes,
                                vote: bool,
                                step_limit=DEFAULT_BIG_STEP_LIMIT) -> dict:
        method = "voteProposal"
        score_params = {
            "id": bytes_to_hex(id_, "0x"),
            "vote": hex(vote)
        }

        return self.create_score_call_tx(from_=from_,
                                         to_=GOVERNANCE_SCORE_ADDRESS,
                                         func_name=method,
                                         params=score_params,
                                         step_limit=step_limit)

    @staticmethod
    def _convert_tx_for_estimating_step_from_origin_tx(tx: dict):
        tx = copy.deepcopy(tx)
        tx["method"] = "debug_estimateStep"
        del tx["params"]["nonce"]
        del tx["params"]["stepLimit"]
        del tx["params"]["timestamp"]
        del tx["params"]["txHash"]
        del tx["params"]["signature"]
        return tx

    # ===== wrapping API ===== #
    def estimate_step(self, tx: dict):
        converted_tx = self._convert_tx_for_estimating_step_from_origin_tx(tx)
        return self.icon_service_engine.estimate_step(request=converted_tx)

    def update_governance(self,
                          version: str = "latest_version",
                          expected_status: bool = True) -> List['TransactionResult']:

        tx = self.create_deploy_score_tx("sample_builtin",
                                         f"{version}/governance",
                                         self._admin,
                                         GOVERNANCE_SCORE_ADDRESS)
        return self.process_confirm_block_tx([tx], expected_status)

    def transfer_icx(self,
                     from_: Union['EOAAccount', 'Address', None],
                     to_: Union['EOAAccount', 'Address', 'MalformedAddress'],
                     value: int,
                     disable_pre_validate: bool = False,
                     support_v2: bool = False,
                     step_limit: int = DEFAULT_STEP_LIMIT,
                     expected_status: bool = True) -> List['TransactionResult']:
        tx = self.create_transfer_icx_tx(from_=from_,
                                         to_=to_,
                                         value=value,
                                         disable_pre_validate=disable_pre_validate,
                                         support_v2=support_v2,
                                         step_limit=step_limit)
        return self.process_confirm_block_tx([tx], expected_status)

    def deploy_score(self,
                     score_root: str,
                     score_name: str,
                     from_: Union['EOAAccount', 'Address', None],
                     deploy_params: dict = None,
                     step_limit: int = DEFAULT_DEPLOY_STEP_LIMIT,
                     expected_status: bool = True,
                     to_: Union['EOAAccount', 'Address'] = ZERO_SCORE_ADDRESS,
                     data: bytes = None) -> List['TransactionResult']:

        tx = self.create_deploy_score_tx(score_root=score_root,
                                         score_name=score_name,
                                         from_=from_,
                                         to_=to_,
                                         deploy_params=deploy_params,
                                         step_limit=step_limit,
                                         data=data)
        return self.process_confirm_block_tx([tx], expected_status)

    def score_call(self,
                   from_: Union['EOAAccount', 'Address', None],
                   to_: 'Address',
                   func_name: str,
                   params: dict = None,
                   value: int = 0,
                   step_limit: int = DEFAULT_BIG_STEP_LIMIT,
                   expected_status: bool = True) -> List['TransactionResult']:

        tx = self.create_score_call_tx(from_=from_,
                                       to_=to_,
                                       func_name=func_name,
                                       params=params,
                                       value=value,
                                       step_limit=step_limit)
        return self.process_confirm_block_tx([tx], expected_status)

    def set_revision(self,
                     revision: int,
                     expected_status: bool = True) -> List['TransactionResult']:

        return self.score_call(from_=self._admin,
                               to_=GOVERNANCE_SCORE_ADDRESS,
                               func_name="setRevision",
                               params={"code": hex(revision), "name": f"1.1.{revision}"},
                               expected_status=expected_status)

    def accept_score(self,
                     tx_hash: Union[bytes, str],
                     warning_message: str = None,
                     expected_status: bool = True) -> List['TransactionResult']:
        if isinstance(tx_hash, bytes):
            tx_hash_str = f'0x{bytes.hex(tx_hash)}'
        else:
            tx_hash_str = tx_hash

        params: dict = {"txHash": tx_hash_str}
        if warning_message is not None:
            params["warning"] = warning_message

        return self.score_call(from_=self._admin,
                               to_=GOVERNANCE_SCORE_ADDRESS,
                               func_name="acceptScore",
                               params=params,
                               expected_status=expected_status)

    def reject_score(self,
                     tx_hash: Union[bytes, str],
                     reason: str = "reason",
                     expected_status: bool = True) -> List['TransactionResult']:

        if isinstance(tx_hash, bytes):
            tx_hash_str = f'0x{bytes.hex(tx_hash)}'
        else:
            tx_hash_str = tx_hash

        return self.score_call(from_=self._admin,
                               to_=GOVERNANCE_SCORE_ADDRESS,
                               func_name="rejectScore",
                               params={"txHash": tx_hash_str,
                                       "reason": reason},
                               expected_status=expected_status)

    def deposit_icx(self,
                    score_address: 'Address',
                    amount: int,
                    period: int,
                    sender: Union['EOAAccount', 'Address', None] = None,
                    expected_status: bool = True) -> List['TransactionResult']:

        if sender is None:
            sender = self._admin
        if FIXED_TERM:
            tx: dict = self.create_deposit_tx(from_=sender,
                                              to_=score_address,
                                              action="add",
                                              params={},
                                              value=amount)
        else:
            tx: dict = self.create_deposit_tx(from_=sender,
                                              to_=score_address,
                                              action="add",
                                              params={"term": hex(period)},
                                              value=amount)
        return self.process_confirm_block_tx([tx], expected_status)

    def withdraw_deposit(self,
                         deposit_id: bytes,
                         score_address: 'Address',
                         sender: Union['EOAAccount', 'Address', None] = None,
                         expected_status: bool = True) -> List['TransactionResult']:
        if sender is None:
            sender = self._admin
        tx: dict = self.create_deposit_tx(from_=sender,
                                          to_=score_address,
                                          action="withdraw",
                                          params={"id": f"0x{bytes.hex(deposit_id)}"})
        return self.process_confirm_block_tx([tx], expected_status)

    def register_proposal(self,
                          from_: 'Address',
                          title: str,
                          description: str,
                          type_: int,
                          value: Union[str, int, 'Address'],
                          expected_status: bool = True) -> 'TransactionResult':
        tx: dict = self.create_register_proposal_tx(from_, title, description, type_, value)

        # 0: base transaction, 1: register proposal
        tx_results = self.process_confirm_block_tx([tx], expected_status)

        return tx_results[1]

    def vote_proposal(self,
                      from_: 'Address',
                      id_: bytes,
                      vote: bool,
                      expected_status: bool = True) -> List['TransactionResult']:
        tx: dict = self.create_vote_proposal_tx(from_, id_, vote)
        return self.process_confirm_block_tx([tx], expected_status)

    def get_balance(self,
                    account: Union['EOAAccount', 'Address']) -> int:

        address: Optional['Address'] = self._convert_address_from_address_type(account)

        return self._query(
            request={
                "address": address
            },
            method="icx_getBalance"
        )

    def get_total_supply(self) -> int:
        return self._query(request={}, method="icx_getTotalSupply")

    def get_score_api(self, address: 'Address'):
        return self._query(
            request={
                "address": address
            },
            method='icx_getScoreApi'
        )

    def query_score(self,
                    from_: Union['EOAAccount', 'Address', None],
                    to_: 'Address',
                    func_name: str,
                    params: dict = None):
        query_request = {
            "version": self._version,
            "from": from_,
            "to": to_,
            "dataType": "call",
            "data": {
                "method": func_name,
                "params": {} if params is None else params
            }
        }
        return self._query(query_request)

    def get_score_status(self, to_: 'Address'):
        query_request = {
            "version": self._version,
            "from": self._admin,
            "to": GOVERNANCE_SCORE_ADDRESS,
            "dataType": "call",
            "data": {
                "method": "getScoreStatus",
                "params": {"address": str(to_)}
            }
        }
        return self._query(query_request)

    def get_step_price(self) -> int:
        query_request = {
            "version": self._version,
            "from": self._admin,
            "to": GOVERNANCE_SCORE_ADDRESS,
            "dataType": "call",
            "data": {
                "method": "getStepPrice",
                "params": {}
            }
        }
        return self._query(query_request)

    @classmethod
    def create_eoa_account(cls) -> 'EOAAccount':
        return EOAAccount(KeyWallet.create())

    @classmethod
    def create_eoa_accounts(cls, count: int) -> List['EOAAccount']:
        return [cls.create_eoa_account() for _ in range(count)]


class EOAAccount:
    def __init__(self, wallet: 'KeyWallet', balance: int = 0):
        self._wallet: 'KeyWallet' = wallet
        self.balance: int = balance

        self._address: 'Address' = Address.from_string(self._wallet.get_address())

    @property
    def public_key(self) -> bytes:
        return self._wallet.bytes_public_key

    @property
    def address(self) -> 'Address':
        return self._address

    def __str__(self):
        return f"name.{self._address}"

    def __repr__(self):
        return self.__str__()
