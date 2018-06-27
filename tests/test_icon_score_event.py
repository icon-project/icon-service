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
from unittest.mock import Mock

from iconservice import eventlog, IconScoreBase, IconScoreDatabase, List, \
    external, IconScoreException
from iconservice.base.address import Address
from iconservice.iconscore.icon_score_context import ContextContainer, \
    IconScoreContext


class TestEventlog(unittest.TestCase):
    def setUp(self):
        db = Mock(spec=IconScoreDatabase)
        address = Mock(spec=Address)
        context = Mock(spec=IconScoreContext)
        event_logs = Mock(spec=List['EventLog'])

        context.attach_mock(event_logs, 'event_logs')
        ContextContainer._put_context(context)

        self._mock_score = EventlogScore(db, address)

    def test_call_event(self):
        context = ContextContainer._get_context()

        name = "name"
        address = Mock(spec=Address)
        age = 10
        phone_number = "000"

        # Tests simple event emit
        self._mock_score.ZeroIndexEvent(name, address, age)
        context.event_logs.append.assert_called()
        event_log = context.event_logs.append.call_args[0][0]
        self.assertEqual(1, len(event_log.indexed))
        self.assertEqual(3, len(event_log.data))

        # This event has a indexed parameter,
        # so the list of indexed Should have 2 items
        self._mock_score.OneIndexEvent(name, address, age)
        context.event_logs.append.assert_called()
        event_log = context.event_logs.append.call_args[0][0]
        self.assertEqual(2, len(event_log.indexed))
        self.assertEqual(2, len(event_log.data))

        # This event is declared 3 indexed_count,
        # but it accept only 2 arguments.
        self.assertRaises(IconScoreException, self._mock_score.ThreeIndexEvent,
                          name, address)

        # This event is declared 4 indexed_count
        self.assertRaises(IconScoreException, self._mock_score.FourIndexEvent,
                          name, address, age, phone_number)

    def test_call_event_kwarg(self):
        context = ContextContainer._get_context()

        name = "name"
        address = Mock(spec=Address)
        age = 10

        # Call with ordered arguments
        self._mock_score.OneIndexEvent(name, address, age)
        context.event_logs.append.assert_called()
        event_log_ordered_args = context.event_logs.append.call_args[0][0]

        # Call with ordered arguments and keyword arguments
        self._mock_score.OneIndexEvent(
            name, age=age, address=address)
        context.event_logs.append.assert_called()
        event_log_keyword_args = context.event_logs.append.call_args[0][0]

        self.assertEqual(event_log_ordered_args.score_address,
                         event_log_keyword_args.score_address)
        self.assertEqual(event_log_ordered_args.indexed,
                         event_log_keyword_args.indexed)
        self.assertEqual(event_log_ordered_args.data,
                         event_log_keyword_args.data)

    # def test_call_event_no_hint_exception(self):
    #     name = "name"
    #     address = Mock(spec=Address)
    #     age = 10
    #     self.assertRaises(IconScoreException, self._mock_score.HintlessEvent,
    #                       name, address, age)

    def test_call_event_mismatch_arg(self):
        name = "name"
        address = Mock(spec=Address)
        age = "10"
        # The hint of 'age' is int type but argument is str type

        self.assertRaises(IconScoreException, self._mock_score.OneIndexEvent,
                          name, address, age)

    # def test_call_event_unsupported_arg(self):
    #     context = ContextContainer._get_context()
    #
    #     name = "name"
    #     address = [create_address(AddressPrefix.CONTRACT, b'empty')]
    #
    #     self.assertRaises(EventLogException, self._mock_score.ArrayEvent,
    #                       name, address)

    def tearDown(self):
        self._mock_icon_score = None


class EventlogScore(IconScoreBase):

    def __init__(self, db: 'IconScoreDatabase', owner: 'Address') -> None:
        super().__init__(db, owner)

    def on_install(self) -> None:
        pass

    def on_update(self) -> None:
        pass

    def on_selfdestruct(self, recipient: 'Address') -> None:
        pass

    @eventlog
    def ZeroIndexEvent(self, name: str, address: Address, age: int):
        pass

    @eventlog(indexed_args_count=1)
    def OneIndexEvent(self, name: str, address: Address, age: int):
        pass

    @eventlog(indexed_args_count=3)
    def ThreeIndexEvent(self, name: str, address: Address):
        pass

    @eventlog(indexed_args_count=4)
    def FourIndexEvent(
            self, name: str, address: Address, age: int, phone_number: str):
        pass

    # @eventlog
    # def HintlessEvent(self, name, address, age):
    #     pass

    # @eventlog
    # def ArrayEvent(self, name: str, address: List[Address], ):
    #     pass

    @external
    def empty(self):
        pass
