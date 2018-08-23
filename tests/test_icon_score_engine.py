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
import unittest
from typing import TYPE_CHECKING
from unittest.mock import Mock

from iconservice.base.address import AddressPrefix
from iconservice.base.address import ZERO_SCORE_ADDRESS
from iconservice.base.block import Block
from iconservice.base.message import Message
from iconservice.base.transaction import Transaction
from iconservice.database.factory import ContextDatabaseFactory
from iconservice.deploy.icon_score_deploy_engine import IconScoreDeployEngine, IconDeployFlag
from iconservice.deploy.icon_score_deploy_storage import IconScoreDeployStorage
from iconservice.deploy.icon_score_manager import IconScoreManager
from iconservice.iconscore.icon_score_context import IconScoreContextFactory, \
    ContextContainer
from iconservice.iconscore.icon_score_context import IconScoreContextType, \
    IconScoreContext
from iconservice.iconscore.icon_score_engine import IconScoreEngine
from iconservice.iconscore.icon_score_mapper import IconScoreMapper
from iconservice.iconscore.icon_score_loader import IconScoreLoader
from iconservice.iconscore.icon_score_step import IconScoreStepCounter
from iconservice.iconscore.icon_score_step import IconScoreStepCounterFactory
from iconservice.icx.icx_engine import IcxEngine
from iconservice.icx.icx_storage import IcxStorage
from iconservice.utils.bloom import BloomFilter
from tests import create_address, create_tx_hash, create_block_hash, rmtree, TEST_ROOT_PATH

if TYPE_CHECKING:
    from iconservice.base.address import Address


class TestContextContainer(ContextContainer):
    pass


# have to score.zip unpack and proj_name = test_score
class TestIconScoreEngine(unittest.TestCase):
    _ROOT_SCORE_PATH = '.score'
    _TEST_DB_PATH = '.statedb'

    def setUp(self):
        self._tx_index = 0

        rmtree(self._ROOT_SCORE_PATH)
        rmtree(self._TEST_DB_PATH)

        ContextDatabaseFactory.open(self._TEST_DB_PATH, ContextDatabaseFactory.Mode.SINGLE_DB)
        self.__ensure_dir(self._TEST_DB_PATH)

        icx_db = ContextDatabaseFactory.create_by_name('icon_dex')
        self.icx_storage = IcxStorage(icx_db)
        deploy_storage = IconScoreDeployStorage(icx_db)
        deploy_storage.is_score_active = Mock(return_value=True)
        self.score_deploy_engine = IconScoreDeployEngine()
        icon_score_loader = IconScoreLoader(self._ROOT_SCORE_PATH)
        self._icon_score_manager = IconScoreManager(self.score_deploy_engine)

        IconScoreMapper.icon_score_loader = icon_score_loader
        IconScoreMapper.deploy_storage = deploy_storage
        self._icon_score_mapper = IconScoreMapper()

        self._context_container = TestContextContainer()

        self.score_deploy_engine.open(
            score_root_path=self._ROOT_SCORE_PATH,
            flag=IconDeployFlag.ENABLE_TBEARS_MODE.value,
            icon_deploy_storage=deploy_storage)

        self.engine = IconScoreEngine()
        self.engine.open(
            self.icx_storage, self._icon_score_mapper)

        self._addr1 = create_address(AddressPrefix.EOA)
        self._addr2 = create_address(AddressPrefix.EOA)
        self._addr3 = create_address(AddressPrefix.EOA)

        self._addr_token_score = create_address(AddressPrefix.CONTRACT)
        self._addr_crowd_sale_score = create_address(AddressPrefix.CONTRACT)

        self.factory = IconScoreContextFactory(max_size=1)
        IconScoreContext.icon_score_manager = self._icon_score_manager
        IconScoreContext.icon_score_mapper = self._icon_score_mapper
        self.make_context()

        self._total_supply = 1000 * 10 ** 18
        self._one_icx = 1 * 10 ** 18
        self._one_icx_to_token = 1

    def make_context(self):
        self._tx_index += 1
        self._context = self.factory.create(IconScoreContextType.DIRECT)
        self._context.msg = Message(self._addr1, 0)

        tx_hash = create_tx_hash()
        self._context.tx = Transaction(tx_hash=tx_hash, origin=self._addr1)
        self._context.block = Block(1, create_block_hash(), 0, None)
        self._context.icon_score_mapper = self._icon_score_mapper
        self._context.icx = IcxEngine()
        self._context.new_icon_score_mapper = IconScoreMapper()
        self.__step_counter_factory = IconScoreStepCounterFactory()
        self._step_counter: IconScoreStepCounter =\
            self.__step_counter_factory.create(100)
        self._context.step_counter = self._step_counter
        self._context.icx.open(self.icx_storage)
        self._context.event_logs = Mock(spec=list)
        self._context.logs_bloom = Mock(spec=BloomFilter)
        self._context.traces = Mock(spec=list)
        self._context_container._push_context(self._context)
        self._context.validate_score_blacklist = Mock()

    def tearDown(self):
        self.engine = None
        self._context.type = IconScoreContextType.DIRECT
        self.icx_storage.close(self._context)
        self.factory.destroy(self._context)
        ContextDatabaseFactory.close()

        rmtree(self._ROOT_SCORE_PATH)
        rmtree(self._TEST_DB_PATH)

    @staticmethod
    def __ensure_dir(dir_path):
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)

    def __request_install(self, project_name: str, score_address: 'Address'):
        self.make_context()
        self.score_deploy_engine.icon_deploy_storage.get_next_tx_hash = Mock(return_value=self._context.tx.hash)
        self.__ensure_dir(self._ROOT_SCORE_PATH)
        path = os.path.join(TEST_ROOT_PATH, f'sample/{project_name}')
        install_data = {'contentType': 'application/tbears', 'content': path}

        self.score_deploy_engine.invoke(
            context=self._context,
            to=ZERO_SCORE_ADDRESS,
            icon_score_address=score_address,
            data=install_data)

    def test_call_get_api(self):
        self.__request_install('sample_token', self._addr_token_score)
        self._context.type = IconScoreContextType.QUERY

        api = self.engine.get_score_api(
            self._context, self._addr_token_score)
        print(api)

    def test_call_balance_of1(self):
        self.__request_install('sample_token', self._addr_token_score)
        self._context.type = IconScoreContextType.QUERY
        call_data = {
            'method': 'balance_of',
            'params': {'addr_from': str(self._addr1)}
        }

        value = self.engine.query(
            self._context, self._addr_token_score, 'call', call_data)
        self.assertEqual(self._total_supply, value)
