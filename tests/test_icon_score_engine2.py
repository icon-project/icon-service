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


import unittest
import os
from iconservice.base.address import Address, AddressPrefix, create_address, ICX_ENGINE_ADDRESS
from iconservice.base.block import Block
from iconservice.base.message import Message
from iconservice.base.transaction import Transaction
from iconservice.database.factory import DatabaseFactory
from iconservice.iconscore.icon_score_context import IconScoreContextFactory, IconScoreContextType
from iconservice.iconscore.icon_score_engine import IconScoreEngine
from iconservice.iconscore.icon_score_info_mapper import IconScoreInfoMapper
from iconservice.iconscore.icon_score_loader import IconScoreLoader
from iconservice.iconscore.icon_score_deployer import IconScoreDeployer
from iconservice.iconscore.icon_score_step import IconScoreStepCounter, IconScoreStepCounterFactory
from iconservice.icx.icx_storage import IcxStorage
from iconservice.icx.icx_engine import IcxEngine
from iconservice.icx.icx_account import Account, AccountType

TEST_ROOT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../'))


# have to score.zip unpack and proj_name = test_score
class TestIconScoreEngine2(unittest.TestCase):
    _ROOT_SCORE_PATH = 'tests/score'
    _TEST_DB_PATH = 'tests/test_db'

    def setUp(self):
        db_path = os.path.join(TEST_ROOT_PATH, self._TEST_DB_PATH)
        score_path = os.path.join(TEST_ROOT_PATH, self._ROOT_SCORE_PATH)

        self.__ensure_dir(db_path)
        self._db_factory = DatabaseFactory(db_path)
        self._icx_db = self._db_factory.create_by_name('icon_dex')
        self._icx_db.address = ICX_ENGINE_ADDRESS
        self._icx_storage = IcxStorage(self._icx_db)

        self._icon_score_loader = IconScoreLoader(score_path)
        self._icon_score_mapper = IconScoreInfoMapper(self._icx_storage, self._db_factory, self._icon_score_loader)
        self._icon_score_deployer = IconScoreDeployer('./')

        self._engine = IconScoreEngine(self._icx_storage, self._icon_score_mapper, self._icon_score_deployer)

        self._addr1 = create_address(AddressPrefix.EOA, b'addr1')
        self._addr2 = create_address(AddressPrefix.EOA, b'addr2')
        self._addr3 = create_address(AddressPrefix.EOA, b'addr3')

        self._addr_token_score = create_address(AddressPrefix.CONTRACT, b'sample_token')
        self._addr_crowd_sale_score = create_address(AddressPrefix.CONTRACT, b'sample_crowd_sale')

        self._factory = IconScoreContextFactory(max_size=1)
        self._context = self._factory.create(IconScoreContextType.GENESIS)
        self._context.msg = Message(self._addr1, 0)
        self._context.tx = Transaction('test_01', origin=self._addr1)
        self._context.block = Block(1, 'block_hash', 0)
        self._context.icon_score_mapper = self._icon_score_mapper
        self._context.icx = IcxEngine()
        self.__step_counter_factory = IconScoreStepCounterFactory()
        self._step_counter: IconScoreStepCounter = self.__step_counter_factory.create(100)
        self._context.step_counter = self._step_counter
        self._context.icx.open(self._icx_storage)

        self._totalsupply = 1000 * 10 ** 18
        self._one_icx = 1 * 10 ** 18
        self._one_icx_to_token = 1

    def tearDown(self):
        self._engine = None
        info = self._icon_score_mapper.get(self._addr_token_score)
        if info is not None and not self._context.readonly:
            score = info.icon_score
            score.db._context_db.close(self._context)
        self._factory.destroy(self._context)

        remove_path = os.path.join(TEST_ROOT_PATH, self._ROOT_SCORE_PATH)
        IconScoreDeployer.remove_existing_score(remove_path)
        remove_path = os.path.join(TEST_ROOT_PATH, self._TEST_DB_PATH)
        IconScoreDeployer.remove_existing_score(remove_path)

    @staticmethod
    def __ensure_dir(dir_path):
        if not os.path.exists(dir_path):
            os.makedirs(dir_path)

    def __request_install(self, proj_name: str, addr_score: Address):
        self.__ensure_dir(self._icon_score_loader.score_root_path)
        path = os.path.join(TEST_ROOT_PATH, 'tests/sample/{}'.format(proj_name))
        install_data = {'contentType': 'application/tbears', 'content': path}
        self._engine.invoke(self._context, addr_score, 'install', install_data)
        self._engine.commit(self._context)

    def test_call_balance_of1(self):
        self.__request_install('sample_token', self._addr_token_score)
        self._context.type = IconScoreContextType.QUERY
        call_data = {'method': 'balance_of', 'params': {'addr_from': self._addr1}}
        self.assertEqual(self._totalsupply, self._engine.query(self._context, self._addr_token_score,
                                                                    'call', call_data))

    def test_call_balance_of2(self):
        self.__request_install('sample_token', self._addr_token_score)
        self._context.type = IconScoreContextType.QUERY
        call_data = {'method': 'balance_of', 'params': {'addr_from': str(self._addr1)}}
        self.assertEqual(self._totalsupply, self._engine.query(self._context, self._addr_token_score,
                                                                    'call', call_data))

    def test_call_ico(self):
        self.__request_install('sample_token', self._addr_token_score)
        self.__request_install('sample_crowd_sale', self._addr_crowd_sale_score)

        # 인스톨 잘 되었나 확인1
        call_data = {'method': 'balance_of', 'params': {'addr_from': str(self._addr1)}}
        self._context.type = IconScoreContextType.QUERY
        self.assertEqual(self._totalsupply, self._engine.query(self._context, self._addr_token_score,
                                                                    'call', call_data))
        # 인스톨 잘 되었나 확인2
        call_data = {'method': 'total_joiner_count', 'params': {}}
        self._context.type = IconScoreContextType.QUERY
        self.assertEqual(0, self._engine.query(self._context, self._addr_crowd_sale_score, 'call', call_data))

        # 토큰 발행자가 ICO스코어 주소로 토큰 이체

        call_data = {'method': 'transfer', 'params': {'addr_to': str(self._addr_crowd_sale_score),
                                                      'value': self._totalsupply}}
        self._context.type = IconScoreContextType.GENESIS
        self._engine.invoke(self._context, self._addr_token_score, 'call', call_data)

        # ICO스코어 주소에 토큰이체 확인
        self._context.type = IconScoreContextType.QUERY
        call_data = {'method': 'balance_of', 'params': {'addr_from': str(self._addr_crowd_sale_score)}}
        self.assertEqual(self._totalsupply,
                         self._engine.query(self._context, self._addr_token_score, 'call', call_data))

        # addr1이 1ICX로 sample ICO참가
        join_icx = 1
        self._context.msg = Message(self._addr1, join_icx * self._one_icx)
        self._context.tx = Transaction('test_01', origin=self._addr1)
        self._context.block = Block(1, 'block_hash', 0)
        self._context.type = IconScoreContextType.GENESIS
        self._engine.invoke(self._context, self._addr_crowd_sale_score, '', {})

        # ICO score와 addr1의 토큰량 확인
        self._context.type = IconScoreContextType.QUERY
        self._context.msg = Message(self._addr1, 0)
        self._context.tx = Transaction('test_01', origin=self._addr1)
        self._context.block = Block(1, 'block_hash', 0)
        call_data = {'method': 'balance_of', 'params': {'addr_from': str(self._addr_crowd_sale_score)}}
        expect = self._totalsupply - join_icx
        self.assertEqual(expect,
                         self._engine.query(self._context, self._addr_token_score, 'call', call_data))
        call_data = {'method': 'balance_of', 'params': {'addr_from': str(self._addr1)}}
        self.assertEqual(join_icx * self._one_icx_to_token,
                         self._engine.query(self._context, self._addr_token_score, 'call', call_data))

        # ICO 조인한 사람 확인
        call_data = {'method': 'total_joiner_count', 'params': {}}
        self._context.type = IconScoreContextType.QUERY
        self.assertEqual(1, self._engine.query(self._context, self._addr_crowd_sale_score, 'call', call_data))

        # addr2이 100ICX로 sample ICO참가
        self._context.type = IconScoreContextType.GENESIS
        join_icx = 100
        self._context.msg = Message(self._addr2, join_icx * self._one_icx)
        self._context.tx = Transaction('test_01', origin=self._addr2)
        self._context.block = Block(1, 'block_hash', 0)
        self._engine.invoke(self._context, self._addr_crowd_sale_score, '', {})

        # ICO score와 addr2의 토큰량 확인
        self._context.type = IconScoreContextType.QUERY
        self._context.msg = Message(self._addr2, 0)
        self._context.tx = Transaction('test_01', origin=self._addr2)
        self._context.block = Block(1, 'block_hash', 0)
        expect = expect - join_icx * self._one_icx_to_token
        call_data = {'method': 'balance_of', 'params': {'addr_from': str(self._addr_crowd_sale_score)}}
        self.assertEqual(expect,
                         self._engine.query(self._context, self._addr_token_score, 'call', call_data))
        call_data = {'method': 'balance_of', 'params': {'addr_from': str(self._addr2)}}
        self.assertEqual(join_icx * self._one_icx_to_token,
                         self._engine.query(self._context, self._addr_token_score, 'call', call_data))

        # ICO 조인한 사람 확인
        call_data = {'method': 'total_joiner_count', 'params': {}}
        self._context.type = IconScoreContextType.QUERY
        self.assertEqual(2, self._engine.query(self._context, self._addr_crowd_sale_score, 'call', call_data))

        # addr1이 ICO끝났는지 확인
        self._context.msg = Message(self._addr1, 0)
        self._context.tx = Transaction('test_01', origin=self._addr2)
        one_minute_to_sec = 1 * 60
        one_second_to_microsec = 1 * 10 ** 6

        self._context.block = Block(2, 'block_hash', 1 * one_minute_to_sec * one_second_to_microsec)

        self._context.type = IconScoreContextType.GENESIS
        call_data = {'method': 'check_goal_reached', 'params': {}}
        self._engine.invoke(self._context, self._addr_crowd_sale_score, 'call', call_data)

        default_icx = 101 * self._one_icx
        account = Account(AccountType.CONTRACT, self._addr_crowd_sale_score, default_icx)
        self._icx_storage.put_account(self._context, self._addr_crowd_sale_score, account)

        self._context.type = IconScoreContextType.GENESIS
        call_data = {'method': 'safe_withdrawal', 'params': {}}
        self._engine.invoke(self._context, self._addr_crowd_sale_score, 'call', call_data)





