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

from collections import namedtuple
from typing import List
from unittest.mock import Mock, patch

from iconcommons.icon_config import IconConfig

from iconservice.database.db import ContextDatabase
from iconservice.icon_config import default_icon_config
from iconservice.icon_constant import ConfigKey
from iconservice.icon_inner_service import IconScoreInnerTask
from iconservice.icon_service_engine import IconServiceEngine
from iconservice.iiss.database.db import Database as RCDatabase
from tests import create_block_hash, rmtree

SERVICE_ENGINE_PATH = 'iconservice.icon_service_engine.IconServiceEngine'
ICX_ENGINE_PATH = 'iconservice.icx.icx_engine.IcxEngine'
DB_FACTORY_PATH = 'iconservice.database.factory.ContextDatabaseFactory'
ReqData = namedtuple("ReqData", "tx_hash, from_, to_, value, data_type, data")
QueryData = namedtuple("QueryData", "from_, to_, data_type, data")
IISS_DB_PATH = 'iconservice.iiss.database.db'
IISS_RC_DATA_STORAGE_PATH = 'iconservice.iiss.reward_calc_data_storage'
IISS_VARIABLE_PATH = 'iconservice.iiss.variable.variable'
PREP_VARIABLE_PATH = 'iconservice.prep.prep_variable.prep_variable'


# noinspection PyProtectedMember
def generate_inner_task(revision=0):
    inner_task = _create_inner_task()

    _patch_service_engine(inner_task._icon_service_engine, revision)

    return inner_task


# noinspection PyProtectedMember
@patch(f'{SERVICE_ENGINE_PATH}._init_global_value_by_governance_score')
@patch(f'{SERVICE_ENGINE_PATH}._load_builtin_scores')
@patch(f'{SERVICE_ENGINE_PATH}._load_prep_candidate')
@patch(f'{ICX_ENGINE_PATH}.open')
@patch(f'{DB_FACTORY_PATH}.create_by_name')
@patch(f'{IISS_DB_PATH}.Database.from_path')
@patch(f'{IISS_RC_DATA_STORAGE_PATH}.RewardCalcDataStorage._load_last_transaction_index')
@patch(f'{IISS_VARIABLE_PATH}.Variable.init_config')
@patch(f'{PREP_VARIABLE_PATH}.PRepVariable.init_config')
def _create_inner_task(
        prep_init_config,
        iiss_init_config,
        load_last_tx_index,
        iiss_db_from_path,
        db_factory_create_by_name,
        icx_engine_open,
        service_engine_load_prep_candidate,
        service_engine_load_builtin_scores,
        service_engine_init_global_value_by_governance_score):
    state_db = {}
    iiss_db = {}

    def state_put(self, key, value):
        state_db[key] = value

    def state_get(self, key):
        return state_db.get(key)

    def iiss_put(key, value):
        iiss_db[key] = value

    def iiss_get(key):
        return iiss_db.get(key)

    context_db = Mock(spec=ContextDatabase)
    context_db.get = state_get
    context_db.put = state_put

    iiss_mock_db = Mock(spec=RCDatabase)
    iiss_mock_db.get = iiss_get
    iiss_mock_db.put = iiss_put

    db_factory_create_by_name.return_value = context_db
    iiss_db_from_path.return_value = iiss_mock_db
    load_last_tx_index.return_value = 0
    inner_task = IconScoreInnerTask(IconConfig("", default_icon_config))

    # Patches create_by_name to pass creating DB
    db_factory_create_by_name.assert_called()
    icx_engine_open.assert_called()
    service_engine_load_prep_candidate.assert_called()
    service_engine_load_builtin_scores.assert_called()
    service_engine_init_global_value_by_governance_score.assert_called()

    # Mocks _init_global_value_by_governance_score
    # to ignore initializing governance SCORE
    inner_task._icon_service_engine._init_global_value_by_governance_score = \
        service_engine_init_global_value_by_governance_score

    return inner_task


def clear_inner_task():
    rmtree(default_icon_config[ConfigKey.SCORE_ROOT_PATH])
    rmtree(default_icon_config[ConfigKey.STATE_DB_ROOT_PATH])
    rmtree(default_icon_config[ConfigKey.IISS_DB_ROOT_PATH])


def generate_service_engine(revision=0):
    service_engine = _create_service_engine()

    _patch_service_engine(service_engine, revision)

    return service_engine


# noinspection PyProtectedMember,PyUnresolvedReferences
@patch(f'{SERVICE_ENGINE_PATH}._load_prep_candidate')
@patch(f'{ICX_ENGINE_PATH}.open')
@patch(f'{DB_FACTORY_PATH}.create_by_name')
@patch(f'{IISS_DB_PATH}.Database.from_path')
@patch(f'{IISS_VARIABLE_PATH}.Variable.init_config')
@patch(f'{PREP_VARIABLE_PATH}.PRepVariable.init_config')
def _create_service_engine(
        prep_init_config,
        iiss_init_config,
        iiss_db_from_path,
        db_factory_create_by_name,
        icx_engine_open,
        service_engine_load_prep_candidate):
    service_engine = IconServiceEngine()

    service_engine._load_builtin_scores = Mock()

    # Mocks _init_global_value_by_governance_score
    # to ignore initializing governance SCORE
    service_engine._init_global_value_by_governance_score = Mock()

    service_engine.open(IconConfig("", default_icon_config))

    # Patches create_by_name to pass creating DB
    iiss_db_from_path.assert_called()
    db_factory_create_by_name.assert_called()
    icx_engine_open.assert_called()

    service_engine._load_builtin_scores.assert_called()
    service_engine._init_global_value_by_governance_score.assert_called()

    # Ignores icx transfer
    service_engine._icx_engine._transfer = Mock()

    service_engine._icon_pre_validator._is_inactive_score = Mock()

    # Mocks get_balance so, it returns always 100 icx
    service_engine._icx_engine.get_balance = Mock(return_value=100 * 10 ** 18)

    return service_engine


# noinspection PyProtectedMember
def _patch_service_engine(icon_service_engine, revision):
    # Mocks get_balance so, it returns always 100 icx
    icon_service_engine._icx_engine.get_balance = \
        Mock(return_value=100 * 10 ** 18)

    # Ignores icx transfer
    icon_service_engine._icx_engine._transfer = Mock()

    # Patch revision
    def set_revision_to_context(context):
        context.revision = revision

    icon_service_engine._set_revision_to_context = \
        Mock(side_effect=set_revision_to_context)

    return icon_service_engine


def create_request(requests: List[ReqData]):
    transactions = []
    for request in requests:
        transactions.append({
            'method': 'icx_sendTransaction',
            'params': {
                'txHash': request.tx_hash,
                'version': hex(3),
                'from': str(request.from_),
                'to': str(request.to_),
                'value': hex(request.value),
                'stepLimit': hex(1234567),
                'timestamp': hex(123456),
                'dataType': request.data_type,
                'data': request.data,
            }
        })

    return {
        'block': {
            'blockHash': bytes.hex(create_block_hash(b'block')),
            'blockHeight': hex(100),
            'timestamp': hex(1234),
            'prevBlockHash': bytes.hex(create_block_hash(b'prevBlock'))
        },
        'transactions': transactions
    }


def create_transaction_req(request: ReqData):
    return {
        'method': 'icx_sendTransaction',
        'params': {
            'txHash': request.tx_hash,
            'version': hex(3),
            'from': str(request.from_),
            'to': str(request.to_),
            'stepLimit': hex(1234567),
            'timestamp': hex(123456),
            'dataType': request.data_type,
            'data': request.data,
        }
    }


def create_query_request(request: QueryData):
    return {
        "method": "icx_call",
        "params": {
            "from": str(request.from_),
            "to": str(request.to_),
            "dataType": request.data_type,
            "data": request.data
        }
    }
