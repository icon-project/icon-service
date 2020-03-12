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
from unittest import mock

import pytest

from iconservice.icon_constant import ConfigKey
from iconservice.icon_service_engine import IconServiceEngine


def mock_config_get(_, key):
    return key


class TestIconServiceEngine:

    # @pytest.mark.skip("TODO")
    def test_open(self, mocker):
        mocker.patch_object(IconServiceEngine, "_make_service_flag", autospec=True)

        conf = mock.Mock()
        conf.attach_mock(mock.Mock(side_effect=lambda key: key), "__getitem__")



        engine = IconServiceEngine()
        engine.open(conf)
        pass
