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
from unittest.mock import Mock, patch

from typing import List

from iconcommons.icon_config import IconConfig
from iconservice.database.db import ContextDatabase
from iconservice.icon_config import default_icon_config
from iconservice.icon_constant import ConfigKey
from iconservice.icon_inner_service import IconScoreInnerTask
from iconservice.icon_service_engine import IconServiceEngine
from tests import create_block_hash, rmtree

SERVICE_ENGINE_PATH = 'iconservice.icon_service_engine.IconServiceEngine'
ICX_ENGINE_PATH = 'iconservice.icx.icx_engine.IcxEngine'
DB_FACTORY_PATH = 'iconservice.database.factory.ContextDatabaseFactory'
ReqData = namedtuple("ReqData", "tx_hash, from_, to_, data_type, data")


# noinspection PyProtectedMember
@patch(f'{SERVICE_ENGINE_PATH}._init_global_value_by_governance_score')
@patch(f'{SERVICE_ENGINE_PATH}._load_builtin_scores')
@patch(f'{ICX_ENGINE_PATH}.open')
@patch(f'{DB_FACTORY_PATH}.create_by_name')
def generate_inner_task(
        db_factory_create_by_name,
        icx_engine_open,
        service_engine_load_builtin_scores,
        service_engine_init_global_value_by_governance_score):
    memory_db = {}

    def put(self, key, value):
        memory_db[key] = value

    def get(self, key):
        return memory_db.get(key)

    context_db = Mock(spec=ContextDatabase)
    context_db.get = get
    context_db.put = put

    db_factory_create_by_name.return_value = context_db
    inner_task = IconScoreInnerTask(IconConfig("", default_icon_config))

    # Patches create_by_name to pass creating DB
    db_factory_create_by_name.assert_called()
    icx_engine_open.assert_called()
    service_engine_load_builtin_scores.assert_called()
    service_engine_init_global_value_by_governance_score.assert_called()

    # Mocks get_balance so, it returns always 100 icx
    inner_task._icon_service_engine._icx_engine.get_balance = \
        Mock(return_value=100 * 10 ** 18)

    # Mocks _init_global_value_by_governance_score
    # to ignore initializing governance SCORE
    inner_task._icon_service_engine._init_global_value_by_governance_score = \
        service_engine_init_global_value_by_governance_score

    # Ignores icx transfer
    inner_task._icon_service_engine._icx_engine._transfer = Mock()

    return inner_task


def clear_inner_task():
    rmtree(default_icon_config[ConfigKey.SCORE_ROOT_PATH])
    rmtree(default_icon_config[ConfigKey.STATE_DB_ROOT_PATH])


# noinspection PyProtectedMember
@patch(f'{ICX_ENGINE_PATH}.open')
@patch(f'{DB_FACTORY_PATH}.create_by_name')
def generate_service_engine(
        db_factory_create_by_name,
        icx_engine_open):
    service_engine = IconServiceEngine()

    service_engine._load_builtin_scores = Mock()

    # Mocks _init_global_value_by_governance_score
    # to ignore initializing governance SCORE
    service_engine._init_global_value_by_governance_score = Mock()

    service_engine.open(IconConfig("", default_icon_config))

    # Patches create_by_name to pass creating DB
    db_factory_create_by_name.assert_called()
    icx_engine_open.assert_called()

    service_engine._load_builtin_scores.assert_called()
    service_engine._init_global_value_by_governance_score.assert_called()

    # Ignores icx transfer
    service_engine._icx_engine._transfer = Mock()

    # Mocks get_balance so, it returns always 100 icx
    service_engine._icx_engine.get_balance = Mock(return_value=100 * 10 ** 18)

    return service_engine


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
