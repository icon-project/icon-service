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
from iconservice.deploy import DeployEngine, DeployStorage
from iconservice.fee import FeeEngine, FeeStorage
from iconservice.icon_config import default_icon_config
from iconservice.icon_constant import ConfigKey
from iconservice.icon_inner_service import IconScoreInnerTask
from iconservice.icon_service_engine import IconServiceEngine
from iconservice.iconscore.icon_score_context import IconScoreContext
from iconservice.icx import IcxEngine, IcxStorage
from iconservice.icx.issue import IssueEngine, IssueStorage
from iconservice.iiss import IISSEngine, IISSStorage
from iconservice.iiss.reward_calc import RewardCalcStorage
from iconservice.iiss.reward_calc.db import Database as RewardCalcDatabase
from iconservice.prep import PRepEngine, PRepStorage
from iconservice.utils import ContextEngine, ContextStorage
from tests import create_block_hash, rmtree

SERVICE_ENGINE_PATH = 'iconservice.icon_service_engine.IconServiceEngine'
ICX_ENGINE_PATH = 'iconservice.icx.engine'
ICX_STORAGE_PATH = 'iconservice.icx.storage'
DB_FACTORY_PATH = 'iconservice.database.factory.ContextDatabaseFactory'
ReqData = namedtuple("ReqData", "tx_hash, from_, to_, value, data_type, data")
QueryData = namedtuple("QueryData", "from_, to_, data_type, data")
IISS_DB_PATH = 'iconservice.iiss.reward_calc.db'
IISS_RC_DATA_STORAGE_PATH = 'iconservice.iiss.reward_calc.storage'
IISS_ENGINE_PATH = 'iconservice.iiss.engine'
IISS_STORAGE_PATH = 'iconservice.iiss.storage'
PREP_ENGINE_PATH = 'iconservice.prep.engine'
PREP_STORAGE_PATH = 'iconservice.prep.storage'


# noinspection PyProtectedMember
def generate_inner_task(revision=0):
    inner_task = _create_inner_task()

    _patch_service_engine(inner_task._icon_service_engine, revision)

    return inner_task


# noinspection PyProtectedMember
@patch(f'{SERVICE_ENGINE_PATH}._init_global_value_by_governance_score')
@patch(f'{SERVICE_ENGINE_PATH}._load_builtin_scores')
@patch(f'{ICX_ENGINE_PATH}.Engine.open')
@patch(f'{DB_FACTORY_PATH}.create_by_name')
@patch(f'{IISS_DB_PATH}.Database.from_path')
@patch(f'{IISS_RC_DATA_STORAGE_PATH}.Storage._load_last_transaction_index')
@patch(f'{IISS_ENGINE_PATH}.Engine.open')
@patch(f'{IISS_STORAGE_PATH}.Storage.open')
@patch(f'{PREP_ENGINE_PATH}.Engine.open')
@patch(f'{PREP_STORAGE_PATH}.Storage.open')
def _create_inner_task(
        prep_storage_open,
        prep_engine_open,
        iiss_storage_open,
        iiss_engine_open,
        load_last_tx_index,
        iiss_db_from_path,
        db_factory_create_by_name,
        icx_engine_open,
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

    iiss_mock_db = Mock(spec=RewardCalcDatabase)
    iiss_mock_db.get = iiss_get
    iiss_mock_db.put = iiss_put

    db_factory_create_by_name.return_value = context_db
    iiss_db_from_path.return_value = iiss_mock_db
    load_last_tx_index.return_value = 0
    inner_task = IconScoreInnerTask(IconConfig("", default_icon_config))

    # Patches create_by_name to pass creating DB
    db_factory_create_by_name.assert_called()
    icx_engine_open.assert_called()
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


def generate_service_engine(revision=0):
    service_engine = _create_service_engine()

    _patch_service_engine(service_engine, revision)

    return service_engine


# noinspection PyProtectedMember,PyUnresolvedReferences
@patch(f'{PREP_ENGINE_PATH}.Engine.open')
@patch(f'{IISS_STORAGE_PATH}.Storage.open')
@patch(f'{IISS_ENGINE_PATH}.Engine.open')
@patch(f'{ICX_STORAGE_PATH}.Storage.open')
@patch(f'{ICX_ENGINE_PATH}.Engine.open')
@patch(f'{DB_FACTORY_PATH}.create_by_name')
@patch(f'{IISS_DB_PATH}.Database.from_path')
def _create_service_engine(
        iiss_db_from_path,
        db_factory_create_by_name,
        icx_engine_open,
        icx_storage_open,
        iiss_engine_open,
        iiss_storage_open,
        prep_engine_open):
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

    service_engine._icon_pre_validator._is_inactive_score = Mock()

    return service_engine


# noinspection PyProtectedMember
def _patch_service_engine(icon_service_engine, revision):
    # Mocks get_balance so, it returns always 100 icx
    # TODO : patch when use get_balance or transfer
    IconScoreContext.engine = ContextEngine(
        deploy=DeployEngine(),
        fee=FeeEngine(),
        icx=IcxEngine(),
        iiss=IISSEngine(),
        prep=PRepEngine(),
        issue=IssueEngine()
    )

    db = icon_service_engine._icx_context_db
    IconScoreContext.storage = ContextStorage(
        deploy=DeployStorage(db),
        fee=FeeStorage(db),
        icx=IcxStorage(db),
        iiss=IISSStorage(db),
        prep=PRepStorage(db),
        issue=IssueStorage(db),
        rc=RewardCalcStorage()
    )

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
