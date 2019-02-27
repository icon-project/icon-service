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
from unittest.mock import Mock

from iconservice.base.address import Address, AddressPrefix, ICON_ADDRESS_BYTES_SIZE
from iconservice.base.exception import EventLogException, ScoreErrorException
from iconservice.database.batch import TransactionBatch
from iconservice.deploy.icon_score_deploy_engine import IconScoreDeployEngine
from iconservice.icon_constant import DATA_BYTE_ORDER, ICX_TRANSFER_EVENT_LOG
from iconservice.icon_service_engine import IconServiceEngine
from iconservice.iconscore.icon_score_base import eventlog, IconScoreBase, IconScoreDatabase, external
from iconservice.iconscore.icon_score_context import ContextContainer, \
    IconScoreContext, IconScoreContextType, IconScoreFuncType
from iconservice.iconscore.icon_score_step import IconScoreStepCounter
from iconservice.icx import IcxEngine
from iconservice.utils import int_to_bytes
from iconservice.utils import to_camel_case


class TestEventlog(unittest.TestCase):
    def setUp(self):
        address = Address.from_data(AddressPrefix.CONTRACT, os.urandom(20))
        db = Mock(spec=IconScoreDatabase)
        db.attach_mock(address, 'address')
        context = IconScoreContext()
        traces = Mock(spec=list)
        step_counter = Mock(spec=IconScoreStepCounter)

        IconScoreContext.icon_score_deploy_engine = Mock(spec=IconScoreDeployEngine)
        IconScoreContext.icx_engine = Mock(spec=IcxEngine)
        context.type = IconScoreContextType.INVOKE
        context.func_type = IconScoreFuncType.WRITABLE
        context.tx_batch = TransactionBatch()
        context.event_logs = []
        context.traces = traces
        context.step_counter = step_counter
        context.get_owner = Mock()
        ContextContainer._push_context(context)

        self._mock_score = EventlogScore(db)

    def tearDown(self):
        ContextContainer._clear_context()
        self._mock_icon_score = None

    def test_call_event(self):
        context = ContextContainer._get_context()

        name = "name"
        address = Address.from_data(AddressPrefix.EOA, os.urandom(20))
        age = 10
        phone_number = "000"

        # Tests simple event emit
        self._mock_score.ZeroIndexEvent(name, address, age)
        self.assertEqual(len(context.event_logs), 1)
        event_log = context.event_logs[0]
        self.assertEqual(1, len(event_log.indexed))
        self.assertEqual(3, len(event_log.data))

        # This event has a indexed parameter,
        # so the list of indexed Should have 2 items
        self._mock_score.OneIndexEvent(name, address, age)
        self.assertEqual(len(context.event_logs), 2)
        event_log = context.event_logs[1]
        self.assertEqual(2, len(event_log.indexed))
        self.assertEqual(2, len(event_log.data))

        logs_bloom = IconServiceEngine._generate_logs_bloom(context.event_logs)

        # Asserts whether the SCORE address is included in the bloom
        self.assert_score_address_in_bloom(logs_bloom)

        zero_event_bloom_data = \
            int(0).to_bytes(1, DATA_BYTE_ORDER) + \
            'ZeroIndexEvent(str,Address,int)'.encode('utf-8')
        self.assertIn(zero_event_bloom_data, logs_bloom)

        one_event_bloom_data = \
            int(0).to_bytes(1, DATA_BYTE_ORDER) + \
            'OneIndexEvent(str,Address,int)'.encode('utf-8')
        self.assertIn(one_event_bloom_data, logs_bloom)

        name_bloom_data = int(1).to_bytes(1, DATA_BYTE_ORDER) + name.encode('utf-8')
        self.assertIn(name_bloom_data, logs_bloom)

    def test_call_event_kwarg(self):
        context = ContextContainer._get_context()

        name = "name"
        address = Address.from_data(AddressPrefix.EOA, os.urandom(20))
        age = 10

        # Call with ordered arguments
        self._mock_score.OneIndexEvent(name, address, age)
        self.assertEqual(len(context.event_logs), 1)
        event_log_ordered_args = context.event_logs[0]

        # Call with ordered arguments and keyword arguments
        self._mock_score.OneIndexEvent(
            name, age=age, address=address)
        self.assertEqual(len(context.event_logs), 2)
        event_log_keyword_args = context.event_logs[1]

        self.assertEqual(event_log_ordered_args.score_address,
                         event_log_keyword_args.score_address)
        self.assertEqual(event_log_ordered_args.indexed,
                         event_log_keyword_args.indexed)
        self.assertEqual(event_log_ordered_args.data,
                         event_log_keyword_args.data)

        logs_bloom = IconServiceEngine._generate_logs_bloom(context.event_logs)

        # Asserts whether the SCORE address is included in the bloom
        self.assert_score_address_in_bloom(logs_bloom)

        one_event_bloom_data = \
            int(0).to_bytes(1, DATA_BYTE_ORDER) + \
            'OneIndexEvent(str,Address,int)'.encode('utf-8')
        self.assertIn(one_event_bloom_data, logs_bloom)

        name_bloom_data = int(1).to_bytes(1, DATA_BYTE_ORDER) + name.encode('utf-8')
        self.assertIn(name_bloom_data, logs_bloom)

    def test_call_event_mismatch_arg(self):
        context = ContextContainer._get_context()

        name = "name"
        address = Address.from_data(AddressPrefix.EOA, os.urandom(20))
        age = "10"
        # The hint of 'age' is int type but argument is str type

        self.assertRaises(ScoreErrorException, self._mock_score.OneIndexEvent,
                          name, address, age)

        logs_bloom = IconServiceEngine._generate_logs_bloom(context.event_logs)

        # Asserts whether the SCORE address is not included in the bloom
        self.assert_score_address_not_in_bloom(logs_bloom)

        one_event_bloom_data = \
            int(0).to_bytes(1, DATA_BYTE_ORDER) + \
            'OneIndexEvent(str,Address,int)'.encode('utf-8')
        self.assertNotIn(one_event_bloom_data, logs_bloom)

        name_bloom_data = int(1).to_bytes(1, DATA_BYTE_ORDER) + name.encode('utf-8')
        self.assertNotIn(name_bloom_data, logs_bloom)

    def test_address_index_event(self):
        context = ContextContainer._get_context()

        address = Address.from_data(AddressPrefix.EOA, os.urandom(20))

        # Tests simple event emit
        self._mock_score.AddressIndexEvent(address)
        self.assertEqual(1, len(context.event_logs))
        event_log = context.event_logs[0]
        self.assertEqual(2, len(event_log.indexed))
        self.assertEqual(0, len(event_log.data))

        logs_bloom = IconServiceEngine._generate_logs_bloom(context.event_logs)

        # Asserts whether the SCORE address is included in the bloom
        self.assert_score_address_in_bloom(logs_bloom)

        event_bloom_data = \
            int(0).to_bytes(1, DATA_BYTE_ORDER) + \
            'AddressIndexEvent(Address)'.encode('utf-8')
        self.assertIn(event_bloom_data, logs_bloom)

        indexed_bloom_data = int(1).to_bytes(1, DATA_BYTE_ORDER) + \
                             address.prefix.value.to_bytes(1, DATA_BYTE_ORDER) + address.body
        self.assertEqual(ICON_ADDRESS_BYTES_SIZE + 1, len(indexed_bloom_data))
        self.assertIn(indexed_bloom_data, logs_bloom)

    def test_bool_index_event(self):
        context = ContextContainer._get_context()

        yes_no = True

        # Tests simple event emit
        self._mock_score.BoolIndexEvent(yes_no)
        self.assertEqual(len(context.event_logs), 1)
        event_log = context.event_logs[0]
        self.assertEqual(2, len(event_log.indexed))
        self.assertEqual(0, len(event_log.data))

        logs_bloom = IconServiceEngine._generate_logs_bloom(context.event_logs)

        # Asserts whether the SCORE address is included in the bloom
        self.assert_score_address_in_bloom(logs_bloom)

        event_bloom_data = \
            int(0).to_bytes(1, DATA_BYTE_ORDER) + \
            'BoolIndexEvent(bool)'.encode('utf-8')
        self.assertIn(event_bloom_data, logs_bloom)

        indexed_bloom_data = \
            int(1).to_bytes(1, DATA_BYTE_ORDER) + int_to_bytes(yes_no)
        self.assertIn(indexed_bloom_data, logs_bloom)

    def test_int_index_event(self):
        context = ContextContainer._get_context()

        amount = 123456789

        # Tests simple event emit
        self._mock_score.IntIndexEvent(amount)
        self.assertEqual(len(context.event_logs), 1)
        event_log = context.event_logs[0]
        self.assertEqual(2, len(event_log.indexed))
        self.assertEqual(0, len(event_log.data))

        logs_bloom = IconServiceEngine._generate_logs_bloom(context.event_logs)

        # Asserts whether the SCORE address is included in the bloom
        self.assert_score_address_in_bloom(logs_bloom)

        event_bloom_data = \
            int(0).to_bytes(1, DATA_BYTE_ORDER) + \
            'IntIndexEvent(int)'.encode('utf-8')
        self.assertIn(event_bloom_data, logs_bloom)

        indexed_bloom_data = \
            int(1).to_bytes(1, DATA_BYTE_ORDER) + int_to_bytes(amount)
        self.assertIn(indexed_bloom_data, logs_bloom)

    def test_bytes_index_event(self):
        context = ContextContainer._get_context()

        data = b'0123456789abc'

        # Tests simple event emit
        self._mock_score.BytesIndexEvent(data)
        self.assertEqual(len(context.event_logs), 1)
        event_log = context.event_logs[0]
        self.assertEqual(2, len(event_log.indexed))
        self.assertEqual(0, len(event_log.data))

        logs_bloom = IconServiceEngine._generate_logs_bloom(context.event_logs)

        # Asserts whether the SCORE address is included in the bloom
        self.assert_score_address_in_bloom(logs_bloom)

        event_bloom_data = \
            int(0).to_bytes(1, DATA_BYTE_ORDER) + \
            'BytesIndexEvent(bytes)'.encode('utf-8')
        self.assertIn(event_bloom_data, logs_bloom)

        indexed_bloom_data = \
            int(1).to_bytes(1, DATA_BYTE_ORDER) + data
        self.assertIn(indexed_bloom_data, logs_bloom)

    def test_to_dict_camel(self):
        context = ContextContainer._get_context()

        address = Address.from_data(AddressPrefix.EOA, os.urandom(20))
        age = 10
        data = b'0123456789abc'

        self._mock_score.MixedEvent(b'i_data', address, age, data, 'text')
        self.assertEqual(len(context.event_logs), 1)

        event_log = context.event_logs[0]

        camel_dict = event_log.to_dict(to_camel_case)
        self.assertIn('scoreAddress', camel_dict)
        self.assertIn('indexed', camel_dict)
        self.assertIn('data', camel_dict)
        self.assertEqual(3, len(camel_dict['indexed']))
        self.assertEqual(3, len(camel_dict['data']))

    def test_event_log_on_readonly_method(self):
        context = ContextContainer._get_context()
        context.func_type = IconScoreFuncType.READONLY

        with self.assertRaises(EventLogException):
            self._mock_score.BoolIndexEvent(False)

    def test_reserved_event_log(self):
        context = ContextContainer._get_context()
        context.func_type = IconScoreFuncType.READONLY

        address = Address.from_data(AddressPrefix.EOA, os.urandom(20))
        with self.assertRaises(EventLogException):
            self._mock_score.ICXTransfer(address, address, 0)

    def test_icx_transfer_event(self):
        context = ContextContainer._get_context()

        address = Address.from_data(AddressPrefix.EOA, os.urandom(20))

        # Tests simple event emit
        self._mock_score.icx.send(address, 1)
        self.assertEqual(len(context.event_logs), 1)
        event_log = context.event_logs[0]
        self.assertEqual(4, len(event_log.indexed))
        self.assertEqual(ICX_TRANSFER_EVENT_LOG, event_log.indexed[0])
        self.assertEqual(0, len(event_log.data))

    def assert_score_address_in_bloom(self, logs_bloom):
        # Asserts whether the SCORE address is included in the bloom
        address = self._mock_score.address
        score_address_bytes = address.prefix.value.to_bytes(1, DATA_BYTE_ORDER) + address.body
        self.assertEqual(ICON_ADDRESS_BYTES_SIZE, len(score_address_bytes))
        self.assertIn(score_address_bytes, logs_bloom)

    def assert_score_address_not_in_bloom(self, logs_bloom):
        # Asserts whether the SCORE address is not included in the bloom
        address = self._mock_score.address
        score_address_bytes = address.prefix.value.to_bytes(1, DATA_BYTE_ORDER) + address.body
        self.assertEqual(ICON_ADDRESS_BYTES_SIZE, len(score_address_bytes))
        self.assertNotIn(score_address_bytes, logs_bloom)


class EventlogScore(IconScoreBase):

    def __init__(self, db: 'IconScoreDatabase') -> None:
        super().__init__(db)

    def on_install(self) -> None:
        pass

    def on_update(self) -> None:
        pass

    @eventlog
    def ZeroIndexEvent(self, name: str, address: 'Address', age: int):
        pass

    @eventlog(indexed=1)
    def OneIndexEvent(self, name: str, address: Address, age: int):
        pass

    @eventlog(indexed=1)
    def AddressIndexEvent(self, address: Address):
        pass

    @eventlog(indexed=1)
    def BoolIndexEvent(self, yes_no: bool):
        pass

    @eventlog(indexed=1)
    def IntIndexEvent(self, amount: int):
        pass

    @eventlog(indexed=1)
    def BytesIndexEvent(self, data: bytes):
        pass

    @eventlog(indexed=2)
    def MixedEvent(self, i_data: bytes, address: Address, amount: int,
                   data: bytes, text: str):
        pass

    @eventlog(indexed=3)
    def ICXTransfer(self, from_: Address, to: Address, amount: int):
        pass

    @external
    def empty(self):
        pass
