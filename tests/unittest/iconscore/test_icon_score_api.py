# -*- coding: utf-8 -*-
#
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

import base64
import hashlib

import pytest

from iconservice.base.block import Block
from iconservice.icon_constant import PREP_MAIN_PREPS, PREP_MAIN_AND_SUB_PREPS
from iconservice.icon_constant import Revision
from iconservice.icon_network import INVEngine, INVContainer
from iconservice.icon_network.data.value import *
from iconservice.iconscore.context.context import ContextContainer
from iconservice.iconscore.icon_score_base2 import PRepInfo, get_main_prep_info, get_sub_prep_info
from iconservice.iconscore.icon_score_base2 import ScoreApiStepRatio
from iconservice.iconscore.icon_score_base2 import _create_address_with_key, _recover_key
from iconservice.iconscore.icon_score_base2 import create_address_with_key, recover_key
from iconservice.iconscore.icon_score_base2 import sha3_256, json_dumps, json_loads
from iconservice.iconscore.icon_score_context import IconScoreContext, IconScoreContextType, IconScoreContextFactory
from iconservice.iconscore.icon_score_step import StepType
from iconservice.prep import PRepEngine
from iconservice.prep.data import PRep, Term, PRepContainer
from iconservice.utils import ContextEngine
from tests import create_address


def create_msg_hash(tx: dict, excluded_keys: tuple) -> bytes:
    keys = [key for key in tx if key not in excluded_keys]
    keys.sort()

    msg = 'icx_sendTransaction'
    for key in keys:
        value: str = tx[key]
        msg += f'.{key}.{value}'
    msg_hash: bytes = hashlib.sha3_256(msg.encode('utf-8')).digest()
    assert msg_hash == bytes.fromhex(tx[excluded_keys[0]])
    return msg_hash


@pytest.fixture(scope="module")
def settable_inv_container():
    default_service_config: int = 0
    default_step_costs = {
        'default': 1_000_000,
        'contractCall': 15_000,
        'contractCreate': 200_000,
        'contractUpdate': 80_000,
        'contractDestruct': -70_000,
        'contractSet': 30_000,
        'get': 0,
        'set': 200,
        'replace': 50,
        'delete': -150,
        'input': 200,
        'eventLog': 100,
        'apiCall': 0
    }
    default_max_step_limits: dict = {
        IconScoreContextType.INVOKE: 2_500_000_000,
        IconScoreContextType.QUERY: 50_000_000
    }
    default_step_price: int = 0
    default_score_black_list: list = []
    default_import_white_list = {"iconservice": ['*']}
    inv_container = INVContainer(is_migrated=False)
    inv_container._icon_network_values = {
        IconNetworkValueType.REVISION_CODE: RevisionCode(0),
        IconNetworkValueType.SCORE_BLACK_LIST: ScoreBlackList(default_score_black_list),
        IconNetworkValueType.STEP_PRICE: StepPrice(default_step_price),
        IconNetworkValueType.STEP_COSTS: StepCosts(default_step_costs),
        IconNetworkValueType.MAX_STEP_LIMITS: MaxStepLimits(default_max_step_limits),
        IconNetworkValueType.SERVICE_CONFIG: ServiceConfig(default_service_config),
        IconNetworkValueType.IMPORT_WHITE_LIST: ImportWhiteList(default_import_white_list)
    }
    return inv_container


@pytest.fixture
def context(settable_inv_container: INVContainer):
    prep_engine = PRepEngine()
    inv_engine = INVEngine()
    settable_inv_container.set_by_icon_service(StepPrice(10 ** 10))
    settable_inv_container.set_by_icon_service(StepCosts(STEP_COSTS))
    settable_inv_container.set_by_icon_service(MaxStepLimits({IconScoreContextType.INVOKE: 2_500_000_000}))
    settable_inv_container.set_by_icon_service(RevisionCode(Revision.THREE.value))
    inv_engine._inv_container = settable_inv_container

    IconScoreContext.engine = ContextEngine(prep=prep_engine, inv=inv_engine)
    context_factory = IconScoreContextFactory()

    block = Block(block_height=1, block_hash=b"1" * 40, prev_hash=b"0" * 40, timestamp=0)
    context = context_factory.create(IconScoreContextType.INVOKE, block)

    step_limit = 1_000_000_000
    context.step_counter.reset(step_limit)

    ContextContainer._push_context(context)
    yield context
    ContextContainer._pop_context()


TX_V2 = {
    'from': 'hxdbc9f726ad776d9a43d5bad387eff01325178fa3',
    'to': 'hx0fb148785e4a5d77d16429c7ed2edae715a4453a',
    'value': '0x324e964b3eca80000',
    'fee': '0x2386f26fc10000',
    'timestamp': '1519709385120909',
    'tx_hash': '1257b9ea76e716b145463f0350f534f973399898a18a50d391e7d2815e72c950',
    'signature': 'WiRTA/tUNGVByc8fsZ7+U9BSDX4BcBuv2OpAuOLLbzUiCcovLPDuFE+PBaT8ovmz5wg+Bjr7rmKiu7Rl8v0DUQE=',
}
# The transaction in block 100000 of MainNet
TX_V3 = {
    'version': '0x3',
    'nid': '0x1',
    'from': 'hx522bff55a62e0c75a1b51855b0802cfec6a92e84',
    'to': 'hx11de4e28be4845de3ea392fd8d758655bf766ca7',
    'value': '0x71afd498d0000',
    'stepLimit': '0xf4240',
    'timestamp': '0x57a4e5556cc03',
    'signature': 'fcEMXqEGlqEivXXr7YtD/F1RXgxSXF+R4gVrGKxT1zxi3HukX4NzkSl9/Es1G+nyZx+kviTAtQFUrA+/T0NrfAA=',
    'txHash': '6c71ac77b2d130a1f81d234e814974e85cabb0a3ec462c66ff3f820502d0ded2'
}
STEP_LIMIT = 1_000_000_000
STEP_COSTS = {
    StepType.DEFAULT: 0,
    StepType.CONTRACT_CALL: 25_000,
    StepType.CONTRACT_CREATE: 1_000_000_000,
    StepType.CONTRACT_UPDATE: 1_600_000_000,
    StepType.CONTRACT_DESTRUCT: -70000,
    StepType.CONTRACT_SET: 30_000,
    StepType.GET: 0,
    StepType.SET: 320,
    StepType.REPLACE: 80,
    StepType.DELETE: -240,
    StepType.INPUT: 200,
    StepType.EVENT_LOG: 100,
    StepType.API_CALL: 10_000
}


def _calc_step_cost(ratio: ScoreApiStepRatio) -> int:
    step_cost: int = STEP_COSTS[StepType.API_CALL] * ratio // ScoreApiStepRatio.SHA3_256
    return step_cost


def _base64_decode_signature(str_sig: str):
    signature: bytes = base64.b64decode(str_sig)
    assert isinstance(signature, bytes)
    assert len(signature) > 0
    return signature


class TestIconScoreApi:

    @pytest.mark.parametrize("tx, tx_hash_key", [
        (TX_V2, 'tx_hash'),
        (TX_V3, 'txHash')
    ])
    @pytest.mark.parametrize("compressed, expected_pubkey_len, expected_pubkey_prefix", [
        (True, 33, [0x02, 0x03]),
        (False, 65, [0x04])
    ])
    def test_recover_key_and_create_address_with_key(self,
                                                     tx, tx_hash_key,
                                                     compressed, expected_pubkey_len, expected_pubkey_prefix):
        # TEST: '_recover_key' method should return proper public key according to the compression flag
        signature: bytes = _base64_decode_signature(tx['signature'])
        msg_hash: bytes = create_msg_hash(tx, (tx_hash_key, 'signature'))

        public_key: bytes = _recover_key(msg_hash, signature, compressed=compressed)

        assert isinstance(public_key, bytes)
        assert len(public_key) == expected_pubkey_len
        assert public_key[0] in expected_pubkey_prefix

        # TEST: '_create_address_with_key' method should make same address no matter what public key format
        address: Address = _create_address_with_key(public_key)

        assert str(address) == tx['from']

    @pytest.mark.parametrize("compressed, expected_step_costs", [
        (True, _calc_step_cost(ScoreApiStepRatio.CREATE_ADDRESS_WITH_COMPRESSED_KEY)),
        (False, _calc_step_cost(ScoreApiStepRatio.CREATE_ADDRESS_WITH_UNCOMPRESSED_KEY))
    ])
    def test_create_address_with_key_step_with_tx_v3(self,
                                                     context,
                                                     compressed, expected_step_costs):
        tx_v3 = TX_V3.copy()
        signature: bytes = _base64_decode_signature(tx_v3['signature'])
        msg_hash: bytes = create_msg_hash(tx_v3, ('txHash', 'signature'))
        public_key: bytes = recover_key(msg_hash, signature, compressed=compressed)
        context.step_counter.reset(STEP_LIMIT)

        create_address_with_key(public_key)

        step_used: int = context.step_counter.step_used
        assert step_used == expected_step_costs

    def test_sha3_256_step(self, context):
        step_cost: int = _calc_step_cost(ScoreApiStepRatio.SHA3_256)

        for i in range(0, 512):
            chunks = i // 32
            if i % 32 > 0:
                chunks += 1

            sha3_256(b'\x00' * i)

            expected_step: int = step_cost + step_cost * chunks // 10
            step_used: int = context.step_counter.step_used
            assert step_used == expected_step
            context.step_counter.reset(STEP_LIMIT)

    def test_json_dumps_step(self, context):
        step_cost: int = _calc_step_cost(ScoreApiStepRatio.JSON_DUMPS)

        for i in range(1, 100):
            obj = {}
            for j in range(i):
                obj[f'key{j}'] = f'value{j}'
            text: str = json_dumps(obj)

            expected_step: int = step_cost + step_cost * len(text.encode('utf-8')) // 100
            step_used: int = context.step_counter.step_used
            assert step_used == expected_step

            obj2: dict = json_loads(text)
            assert obj2 == obj

            context.step_counter.reset(STEP_LIMIT)

    def test_json_loads_step(self, context):
        step_cost: int = _calc_step_cost(ScoreApiStepRatio.JSON_LOADS)

        for i in range(1, 100):
            obj = {}
            for j in range(i):
                obj[f'key{j}'] = f'value{j}'
            text: str = json_dumps(obj)
            context.step_counter.reset(STEP_LIMIT)

            obj2: dict = json_loads(text)
            assert obj2 == obj

            expected_step: int = step_cost + step_cost * len(text.encode('utf-8')) // 100
            step_used: int = context.step_counter.step_used
            assert step_used == expected_step

    # FIXME: Did not convert to pytest
    def test_get_prep_info(self, context):
        main_prep_list, end_block_height = get_main_prep_info()
        assert main_prep_list == []
        assert end_block_height == -1

        sub_prep_list, end_block_height = get_sub_prep_info()
        assert main_prep_list == []
        assert end_block_height == -1

        # term._preps to contexts
        prep_infos: List['PRepInfo'] = []
        preps: 'PRepContainer' = PRepContainer()
        for i in range(PREP_MAIN_AND_SUB_PREPS):
            delegated: int = PREP_MAIN_AND_SUB_PREPS - i
            prep_info = PRepInfo(address=create_address(), delegated=delegated, name=f"prep{i}")
            prep_infos.append(prep_info)

            prep = PRep(address=prep_info.address, delegated=prep_info.delegated, name=prep_info.name)
            preps.add(prep)

        term = Term(sequence=0,
                    start_block_height=61,
                    period=40,
                    irep=50_000,
                    total_supply=1_000_000_000,
                    total_delegated=1_000_000_000)
        term.set_preps(preps, PREP_MAIN_PREPS, PREP_MAIN_AND_SUB_PREPS)
        term.freeze()

        context.engine.prep.term = term
        context._term = term.copy()
        context._preps = preps.copy(mutable=True)

        # check main P-Rep info
        main_prep_list, end_block_height = get_main_prep_info()
        for i, prep_info in enumerate(main_prep_list):
            prep = preps.get_by_address(prep_info.address)
            assert prep.address == prep_infos[i].address
            assert prep.delegated == prep_infos[i].delegated
            assert prep.name == prep_infos[i].name

            assert prep.address == prep_info.address
            assert prep.delegated == prep_info.delegated
            assert prep.name == prep_info.name

        assert context.engine.prep.term.end_block_height == end_block_height

        # check sub P-Rep info
        for i, prep_info in enumerate(sub_prep_list):
            j = i + PREP_MAIN_PREPS
            prep = preps.get_by_address(prep_info.address)
            assert prep.address == prep_infos[j].address
            assert prep.delegated == prep_infos[j].delegated
            assert prep.name == prep_infos[j].name

            assert prep.address == prep_info.address
            assert prep.delegated == prep_info.delegated
            assert prep.name == prep_info.name

        # check end block height
        assert context.engine.prep.term.end_block_height == end_block_height
