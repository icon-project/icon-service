# -*- coding: utf-8 -*-

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

from unittest.mock import Mock

import pytest

from iconservice.base.exception import AccessDeniedException
from iconservice.icon_network import INVEngine, INVContainer, INVStorage
from iconservice.icon_network.data.value import *
from iconservice.iconscore.icon_score_context import IconScoreContext
from iconservice.utils import ContextStorage
from tests import create_address


class TestValue:
    @pytest.mark.parametrize("value", [
        RevisionCode(5),
        RevisionName("1.1.5"),
        ScoreBlackList([]),
        StepPrice(10_000),
        StepCosts({
            StepType('default'): 10_000
        }),
        MaxStepLimits({
            IconScoreContextType.INVOKE: 100_000_000,
            IconScoreContextType.QUERY: 100_000_000
        }),
        ServiceConfig(5),
        ImportWhiteList({"iconservice": ['*'], "os": ["path"]})
    ])
    def test_from_to_bytes(self, value: 'Value'):
        # TEST: Check key is generated as expected
        expected_bytes_key = b'inv' + value.TYPE.value

        bytes_key: bytes = value.make_key()

        assert bytes_key == expected_bytes_key

        # TEST: encoded_value should include the version information
        # and encoded by msgpack
        encoded_value: bytes = value.to_bytes()

        unpacked_value: list = MsgPackForDB.loads(encoded_value)
        expected_version = 0

        assert len(unpacked_value) == 2
        assert unpacked_value[0] == expected_version

        # TEST: decoded value has same value with original
        decoded_value: 'Value' = value.from_bytes(encoded_value)

        assert decoded_value.value == value.value
