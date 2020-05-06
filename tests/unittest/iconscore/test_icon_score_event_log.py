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
from unittest import mock

import pytest

from iconservice.base.address import (
    GOVERNANCE_SCORE_ADDRESS,
    Address,
    ICON_ADDRESS_BODY_SIZE,
    ICON_ADDRESS_BYTES_SIZE,
)
from iconservice.icon_constant import Revision
from iconservice.iconscore.icon_score_context import IconScoreContext
from iconservice.iconscore.icon_score_event_log import EventLog, EventLogEmitter
from iconservice.utils import to_camel_case, byte_length_of_int
from tests import create_address


class TestEventLog:
    @pytest.fixture
    def mock_event_log(self, mocker):
        def _data(score_address, indexed, data):
            return EventLog(score_address, indexed, data)

        return _data

    @pytest.mark.parametrize("score_address", [create_address(0), create_address(1)])
    @pytest.mark.parametrize("indexed", [[int], [str], [int, str]])
    @pytest.mark.parametrize("data", [[int], [str], [int, str]])
    def test_str(self, mock_event_log, score_address, indexed, data):
        if not score_address.is_contract:
            with pytest.raises(AssertionError):
                mock_event_log(score_address=score_address, indexed=indexed, data=data)
        else:
            mock_event_log = mock_event_log(
                score_address=score_address, indexed=indexed, data=data
            )
            ret = str(mock_event_log)
            expected = (
                f"score_address: {score_address}\nindexed: {indexed}\ndata: {data}"
            )
            assert ret == expected

    @pytest.mark.parametrize("score_address", [create_address(0), create_address(1)])
    @pytest.mark.parametrize("indexed", [[int], [str], [int, str]])
    @pytest.mark.parametrize("data", [[int], [str], [int, str]])
    @pytest.mark.parametrize("casting", [to_camel_case])
    def test_to_dict(self, mock_event_log, score_address, indexed, data, casting):
        if not score_address.is_contract:
            with pytest.raises(AssertionError):
                mock_event_log(score_address=score_address, indexed=indexed, data=data)
        else:
            mock_event_log = mock_event_log(
                score_address=score_address, indexed=indexed, data=data
            )
            ret = mock_event_log.to_dict(casing=casting)
            expected = {
                casting("score_address"): score_address,
                casting("indexed"): indexed,
                casting("data"): data,
            }
            assert ret == expected


class TestEventLogEmitter:
    @pytest.fixture
    def mock_context(self, mocker):
        def _data(revision):
            m = mock.MagicMock()
            params = mock.PropertyMock(return_value=revision)
            type(m).revision = params
            return m

        return _data

    @pytest.mark.parametrize(
        "data, expected",
        [
            (1, b"\x01"),
            ("1", b"1"),
            (
                GOVERNANCE_SCORE_ADDRESS,
                b"\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01",
            ),
            (b"1", b"1"),
            (True, b"\x01"),
        ],
    )
    def test_get_bytes_from_base_type(self, data, expected):
        func = getattr(
            EventLogEmitter, f"_{EventLogEmitter.__name__}__get_bytes_from_base_type"
        )
        ret = func(data)
        assert ret == expected

    @pytest.mark.parametrize("revision", [revision.value for revision in Revision])
    @pytest.mark.parametrize("data", [None, 0, 0x80, GOVERNANCE_SCORE_ADDRESS])
    def test_get_bytes_length(self, mock_context, revision, data):
        context = mock_context(revision)
        func = getattr(EventLogEmitter, f"_{EventLogEmitter.__name__}__get_byte_length")
        ret = func(context, data)

        expected: int = 0
        if data is None:
            expected = 0
        elif isinstance(data, int):
            expected = byte_length_of_int(data)
        elif isinstance(data, Address):
            if revision < Revision.THREE.value:
                expected = ICON_ADDRESS_BODY_SIZE
            else:
                expected = ICON_ADDRESS_BYTES_SIZE
        assert ret == expected
