# -*- coding: utf-8 -*-

# Copyright 2017-2018 theloop Inc.
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
from unittest.mock import Mock

from iconservice.base.address import AddressPrefix
from iconservice.base.address import ICX_ENGINE_ADDRESS, ZERO_SCORE_ADDRESS
from iconservice.base.block import Block
from iconservice.base.message import Message
from iconservice.base.transaction import Transaction
from iconservice.database.factory import DatabaseFactory
from iconservice.deploy.icon_score_deploy_engine import IconScoreDeployEngine
from iconservice.deploy.icon_score_deploy_storage import IconScoreDeployStorage
from iconservice.deploy.icon_score_manager import IconScoreManager
from iconservice.iconscore.icon_score_context import IconScoreContextFactory
from iconservice.iconscore.icon_score_context import IconScoreContextType, IconScoreContext
from iconservice.iconscore.icon_score_engine import IconScoreEngine
from iconservice.iconscore.icon_score_info_mapper import IconScoreInfoMapper
from iconservice.iconscore.icon_score_loader import IconScoreLoader
from iconservice.iconscore.icon_score_step import IconScoreStepCounter
from iconservice.iconscore.icon_score_step import IconScoreStepCounterFactory
from iconservice.icx.icx_account import Account, AccountType
from iconservice.icx.icx_engine import IcxEngine
from iconservice.icx.icx_storage import IcxStorage
from iconservice.utils.bloom import BloomFilter
from iconservice.icon_config import DATA_BYTE_ORDER
from tests import rmtree, create_address, create_tx_hash, create_block_hash

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from iconservice.base.address import Address

TEST_ROOT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../'))


# have to score.zip unpack and proj_name = test_score
class TestIconScoreEngine2(unittest.TestCase):
    _ROOT_SCORE_PATH = 'tests/score'
    _TEST_DB_PATH = 'tests/test_db'

    def setUp(self):
        db_path = os.path.join(TEST_ROOT_PATH, self._TEST_DB_PATH)
        score_path = os.path.join(TEST_ROOT_PATH, self._ROOT_SCORE_PATH)

        self._tx_index = 0

        self.__ensure_dir(db_path)
        self._db_factory = DatabaseFactory(db_path)
        self._icx_db = self._db_factory.create_by_name('icon_dex')
        self._icx_db.address = ICX_ENGINE_ADDRESS
        self._icx_storage = IcxStorage(self._icx_db)
        self._score_deploy_engine = IconScoreDeployEngine()
        self._deploy_storage = IconScoreDeployStorage(self._icx_db)

        self._icon_score_loader = IconScoreLoader(score_path)
        self._icon_score_manager = IconScoreManager(self._score_deploy_engine)
        self._icon_score_mapper = IconScoreInfoMapper(
            self._db_factory, self._icon_score_manager, self._icon_score_loader)

        self._score_deploy_engine.open(
            icon_score_root_path=score_path,
            flags=IconScoreDeployEngine.Flag.NONE,
            icon_score_mapper=self._icon_score_mapper,
            icon_deploy_storage=self._deploy_storage)

        self.score_engine = IconScoreEngine()
        self.score_engine.open(
            self._icx_storage, self._icon_score_mapper)

        self._addr1 = create_address(AddressPrefix.EOA, b'addr1')
        self._addr2 = create_address(AddressPrefix.EOA, b'addr2')
        self._addr3 = create_address(AddressPrefix.EOA, b'addr3')

        self._addr_token_score = create_address(
            AddressPrefix.CONTRACT, b'sample_token')
        self._addr_crowd_sale_score = create_address(
            AddressPrefix.CONTRACT, b'sample_crowd_sale')

        self._factory = IconScoreContextFactory(max_size=1)
        IconScoreContext.icon_score_manager = self._icon_score_manager
        self.make_context()

        self._total_supply = 1000 * 10 ** 18
        self._one_icx = 1 * 10 ** 18
        self._one_icx_to_token = 1

    def make_context(self):
        self._tx_index += 1
        self._context = self._factory.create(IconScoreContextType.DIRECT)
        self._context.msg = Message(self._addr1, 0)
        self._context.tx = Transaction(
            create_tx_hash(b'txHash' + self._tx_index.to_bytes(10, DATA_BYTE_ORDER)), origin=self._addr1)
        self._context.block = Block(1, create_block_hash(b'block'), 0, None)
        self._context.icon_score_mapper = self._icon_score_mapper
        self._context.icx = IcxEngine()
        self.__step_counter_factory = IconScoreStepCounterFactory()
        self._step_counter: IconScoreStepCounter =\
            self.__step_counter_factory.create(100, step_price=0)
        self._context.step_counter = self._step_counter
        self._context.icx.open(self._icx_storage)
        self._context.event_logs = Mock(spec=list)
        self._context.logs_bloom = Mock(spec=BloomFilter)
        self._context.traces = Mock(spec=list)

    def tearDown(self):
        try:
            self._icon_score_mapper.close()
            self._context.type = IconScoreContextType.DIRECT
            self._factory.destroy(self._context)
            self._icx_storage.close(self._context)
        finally:
            remove_path = os.path.join(TEST_ROOT_PATH, self._ROOT_SCORE_PATH)
            rmtree(remove_path)
            remove_path = os.path.join(TEST_ROOT_PATH, self._TEST_DB_PATH)
            rmtree(remove_path)

    @staticmethod
    def __ensure_dir(dir_path):
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)

    def __request_install(self, project_name: str, score_address: 'Address'):
        self.make_context()
        self.__ensure_dir(self._icon_score_loader.score_root_path)
        path = os.path.join(TEST_ROOT_PATH, f'tests/sample/{project_name}')
        install_data = {'contentType': 'application/tbears', 'content': path}

        self._score_deploy_engine.invoke(
            context=self._context,
            to=ZERO_SCORE_ADDRESS,
            icon_score_address=score_address,
            data=install_data)

        self._score_deploy_engine.commit(self._context)

    def test_call_get_api(self):
        self.__request_install('sample_token', self._addr_token_score)
        self._context.type = IconScoreContextType.QUERY

        api = self.score_engine.get_score_api(
            self._context, self._addr_token_score)
        print(api)

    def test_call_balance_of1(self):
        self.__request_install('sample_token', self._addr_token_score)
        self._context.type = IconScoreContextType.QUERY
        call_data = {
            'method': 'balance_of',
            'params': {'addr_from': str(self._addr1)}
        }

        value = self.score_engine.query(
            self._context, self._addr_token_score, 'call', call_data)
        self.assertEqual(self._total_supply, value)

    def test_call_ico(self):
        self.__request_install('sample_token', self._addr_token_score)
        self.__request_install('sample_crowd_sale', self._addr_crowd_sale_score)

        # 인스톨 잘 되었나 확인1
        call_data = {
            'method': 'balance_of',
            'params': {'addr_from': str(self._addr1)}
        }
        self._context.type = IconScoreContextType.QUERY

        ret = self.score_engine.query(
            self._context, self._addr_token_score, 'call', call_data)
        self.assertEqual(self._total_supply, ret)

        # 인스톨 잘 되었나 확인2
        call_data = {'method': 'total_joiner_count', 'params': {}}
        self._context.type = IconScoreContextType.QUERY

        ret = self.score_engine.query(
            self._context, self._addr_crowd_sale_score, 'call', call_data)
        self.assertEqual(0, ret)

        # 토큰 발행자가 ICO스코어 주소로 토큰 이체

        call_data = {
            'method': 'transfer',
            'params': {
                'addr_to': str(self._addr_crowd_sale_score),
                'value': hex(self._total_supply)
            }
        }
        self._context.type = IconScoreContextType.DIRECT
        self.score_engine.invoke(
            self._context, self._addr_token_score, 'call', call_data)

        # ICO스코어 주소에 토큰이체 확인
        self._context.type = IconScoreContextType.QUERY
        call_data = {
            'method': 'balance_of',
            'params': {'addr_from': str(self._addr_crowd_sale_score)}
        }

        ret = self.score_engine.query(
            self._context, self._addr_token_score, 'call', call_data)
        self.assertEqual(self._total_supply, ret)

        # addr1이 1ICX로 sample ICO참가
        join_icx = 1
        self._context.msg = Message(self._addr1, join_icx * self._one_icx)
        self._context.tx = Transaction(create_tx_hash(), origin=self._addr1)
        self._context.block = Block(1, create_block_hash(), 0, None)
        self._context.type = IconScoreContextType.DIRECT
        self.score_engine.invoke(
            self._context, self._addr_crowd_sale_score, '', {})

        # ICO score와 addr1의 토큰량 확인
        self._context.type = IconScoreContextType.QUERY
        self._context.msg = Message(self._addr1, 0)
        self._context.tx = Transaction(create_tx_hash(), origin=self._addr1)
        self._context.block = Block(1, create_block_hash(), 0, None)
        call_data = {
            'method': 'balance_of',
            'params': {'addr_from': str(self._addr_crowd_sale_score)}
        }
        expected = self._total_supply - join_icx
        ret = self.score_engine.query(
            self._context, self._addr_token_score, 'call', call_data)
        self.assertEqual(expected, ret)

        call_data = {
            'method': 'balance_of',
            'params': {'addr_from': str(self._addr1)}
        }
        ret = self.score_engine.query(
            self._context, self._addr_token_score, 'call', call_data)
        self.assertEqual(join_icx * self._one_icx_to_token, ret)

        # ICO 조인한 사람 확인
        call_data = {'method': 'total_joiner_count', 'params': {}}
        self._context.type = IconScoreContextType.QUERY
        ret = self.score_engine.query(
            self._context, self._addr_crowd_sale_score, 'call', call_data)
        self.assertEqual(1, ret)

        # addr2이 100ICX로 sample ICO참가
        self._context.type = IconScoreContextType.DIRECT
        join_icx = 100
        self._context.msg = Message(self._addr2, join_icx * self._one_icx)
        self._context.tx = Transaction(create_tx_hash(), origin=self._addr2)
        self._context.block = Block(1, create_block_hash(), 0, None)
        self.score_engine.invoke(
            self._context, self._addr_crowd_sale_score, '', {})

        # ICO score와 addr2의 토큰량 확인
        self._context.type = IconScoreContextType.QUERY
        self._context.msg = Message(self._addr2, 0)
        self._context.tx = Transaction(create_tx_hash(), origin=self._addr2)
        self._context.block = Block(1, create_block_hash(), 0, None)
        expected = expected - join_icx * self._one_icx_to_token
        call_data = {
            'method': 'balance_of',
            'params': {'addr_from': str(self._addr_crowd_sale_score)}
        }
        ret = self.score_engine.query(
            self._context, self._addr_token_score, 'call', call_data)
        self.assertEqual(expected, ret)

        call_data = {
            'method': 'balance_of',
            'params': {'addr_from': str(self._addr2)}
        }
        ret = self.score_engine.query(
            self._context, self._addr_token_score, 'call', call_data)
        self.assertEqual(join_icx * self._one_icx_to_token, ret)

        # ICO 조인한 사람 확인
        call_data = {'method': 'total_joiner_count', 'params': {}}
        self._context.type = IconScoreContextType.QUERY
        ret = self.score_engine.query(
            self._context, self._addr_crowd_sale_score, 'call', call_data)
        self.assertEqual(2, ret)

        # addr1이 ICO끝났는지 확인
        self._context.msg = Message(self._addr1, 0)
        self._context.tx = Transaction(create_tx_hash(), origin=self._addr2)
        one_minute_to_sec = 1 * 60
        one_second_to_microsec = 1 * 10 ** 6

        self._context.block = Block(
            2, create_block_hash(), 1 * one_minute_to_sec * one_second_to_microsec, None)

        self._context.type = IconScoreContextType.DIRECT
        call_data = {'method': 'check_goal_reached', 'params': {}}
        self.score_engine.invoke(
            self._context, self._addr_crowd_sale_score, 'call', call_data)

        default_icx = 101 * self._one_icx
        account = Account(
            AccountType.CONTRACT, self._addr_crowd_sale_score, default_icx)
        self._icx_storage.put_account(
            self._context, self._addr_crowd_sale_score, account)

        self._context.type = IconScoreContextType.DIRECT
        call_data = {'method': 'safe_withdrawal', 'params': {}}
        self.score_engine.invoke(
            self._context, self._addr_crowd_sale_score, 'call', call_data)
