# -*- coding: utf-8 -*-

# Copyright 2020 ICON Foundation
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

"""IconServiceEngine testCase"""
from unittest.mock import Mock

import pytest

from iconservice.icon_constant import IconServiceFlag, ConfigKey
from iconservice.icon_service_engine import IconServiceEngine


@pytest.fixture
def engine():
    engine = IconServiceEngine()
    return engine


@pytest.mark.parametrize("fee", [True, False])
@pytest.mark.parametrize("audit", [True, False])
@pytest.mark.parametrize("validator", [True, False])
def test_make_flag(engine, fee, audit, validator):
    table = {
        ConfigKey.SERVICE_FEE: fee,
        ConfigKey.SERVICE_AUDIT: audit,
        ConfigKey.SERVICE_SCORE_PACKAGE_VALIDATOR: validator,
    }
    fee_flag_value = IconServiceFlag.FEE.value if fee else 0
    audit_flag_value = IconServiceFlag.AUDIT.value if audit else 0
    validator_flag_value = (
        IconServiceFlag.SCORE_PACKAGE_VALIDATOR.value if validator else 0
    )
    flag = engine._make_service_flag(table)
    assert flag == (fee_flag_value | audit_flag_value | validator_flag_value)


@pytest.mark.parametrize(
    "method",
    [
        "icx_getBalance",
        "icx_getTotalSupply",
        "icx_call",
        "icx_sendTransaction",
        "debug_estimateStep",
        "icx_getScoreApi",
        "ise_getStatus",
    ],
)
def test_call_method(engine, method):
    call_method = engine._handlers[method] = Mock()
    ctx = Mock()
    params = Mock(spec=dict)
    engine._call(ctx, method, params)
    call_method.assert_called_with(ctx, params)
