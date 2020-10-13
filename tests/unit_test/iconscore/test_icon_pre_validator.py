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

import os
from unittest.mock import Mock

import pytest

from iconservice.base.address import Address, AddressPrefix
from iconservice.base.address import SYSTEM_SCORE_ADDRESS
from iconservice.base.exception import InvalidRequestException, InvalidParamsException
from iconservice.icon_constant import Revision
from iconservice.iconscore.icon_pre_validator import IconPreValidator
from iconservice.iconscore.icon_score_context import IconScoreContext, IconScoreContextType
from iconservice.icx import IcxEngine, IcxStorage
from iconservice.utils import ContextEngine, ContextStorage
from iconservice.utils.locked import LOCKED_ADDRESSES


@pytest.fixture
def context():
    IconScoreContext.engine = ContextEngine(
        icx=Mock(spec=IcxEngine),
        deploy=None,
        fee=None,
        iiss=None,
        prep=None,
        issue=None,
    )
    IconScoreContext.storage = ContextStorage(
        icx=Mock(spec=IcxStorage),
        deploy=None,
        fee=None,
        iiss=None,
        prep=None,
        issue=None,
        rc=None,
        meta=None
    )

    context = Mock()
    context.engine.icx.get_balance.return_value = 10 ** 18

    return context


class TestTransactionValidator:

    @pytest.mark.parametrize(
        "context_type,revision,blocked",
        [
            (IconScoreContextType.QUERY, 9, False),
            (IconScoreContextType.INVOKE, 9, False),
            (IconScoreContextType.QUERY, Revision.LOCK_ADDRESS.value, True),
            (IconScoreContextType.INVOKE, Revision.LOCK_ADDRESS.value, True),
        ]
    )
    def test_is_address_locked(self, context, context_type, revision, blocked):
        context.type = context_type
        context.revision = revision

        validator = IconPreValidator()

        step_price = 0
        addresses = [address_text for address_text in LOCKED_ADDRESSES]

        for address_text in addresses:
            address = Address.from_string(address_text)

            params = {
                "version": 3,
                "from": Address.from_string(address_text),
                "to": SYSTEM_SCORE_ADDRESS,
                "stepLimit": 128600,
                "dataType": "call",
                "data": {
                    "method": "setDelegation",
                    "params": {
                        "delegations": [
                            {
                                "address": "hx8b91a08e04b17609d20fbcc233548fc80f7a4067",
                                "value": hex(10 ** 18)
                            }
                        ]
                    }
                }
            }

            if blocked:
                with pytest.raises(InvalidRequestException) as execinfo:
                    validator.execute(context, params, step_price, 100_000)
                assert execinfo.value.message == f"Address is locked: {address}"

                with pytest.raises(InvalidRequestException) as execinfo:
                    validator.execute_to_check_out_of_balance(context, params, step_price)
                assert execinfo.value.message == f"Address is locked: {address}"
            else:
                validator.execute(context, params, step_price, 100_000)
                validator.execute_to_check_out_of_balance(context, params, step_price)

    @pytest.mark.parametrize(
        "context_type,revision,blocked",
        [
            (IconScoreContextType.QUERY, 9, True),
            (IconScoreContextType.INVOKE, 9, False),
            (IconScoreContextType.QUERY, Revision.LOCK_ADDRESS.value, True),
            (IconScoreContextType.INVOKE, Revision.LOCK_ADDRESS.value, True),
        ]
    )
    def test_is_address_locked2(self, context, context_type, revision, blocked):
        context.type = context_type
        context.revision = revision

        validator = IconPreValidator()

        step_price = 0
        address = Address.from_string("hxe7af5fcfd8dfc67530a01a0e403882687528dfcb")

        params = {
            "version": 3,
            "from": address,
            "to": SYSTEM_SCORE_ADDRESS,
            "stepLimit": 128600,
            "dataType": "call",
            "data": {
                "method": "setDelegation",
                "params": {
                    "delegations": [
                        {
                            "address": "hx8b91a08e04b17609d20fbcc233548fc80f7a4067",
                            "value": hex(10 ** 18)
                        }
                    ]
                }
            }
        }

        validator.execute(context, params, step_price, 100_000)
        validator.execute_to_check_out_of_balance(context, params, step_price)

    @pytest.mark.parametrize(
        "revision",
        [rev for rev in range(Revision.IMPROVED_PRE_VALIDATOR.value - 1, Revision.LATEST.value + 1)]
    )
    @pytest.mark.parametrize(
        "address_prefix,data_type,valid",
        [
            (AddressPrefix.EOA, "call", False),
            (AddressPrefix.CONTRACT, "call", True),
            (AddressPrefix.EOA, "deploy", False),
            (AddressPrefix.CONTRACT, "deploy", True),
            (AddressPrefix.EOA, "deposit", False),
            (AddressPrefix.CONTRACT, "deposit", True),
            (AddressPrefix.EOA, "message", True),
            (AddressPrefix.CONTRACT, "message", True),
            (AddressPrefix.EOA, None, True),
            (AddressPrefix.CONTRACT, None, True),
        ]
    )
    def test_validate_mismatch_between_to_and_data_type(self, context, revision, address_prefix, data_type, valid):
        to = Address(address_prefix, os.urandom(20))
        context.type = IconScoreContextType.INVOKE
        context.revision = revision

        if revision < Revision.IMPROVED_PRE_VALIDATOR.value or valid:
            IconPreValidator.validate_data_type(context, to, data_type)
        else:
            with pytest.raises(InvalidParamsException) as exc_info:
                IconPreValidator.validate_data_type(context, to, data_type)

            assert exc_info.value.message.startswith("Mismatch between to and dataType")

    @pytest.mark.parametrize(
        "revision",
        [rev for rev in range(Revision.IMPROVED_PRE_VALIDATOR.value - 1, Revision.LATEST.value + 1)]
    )
    @pytest.mark.parametrize("address_prefix", [AddressPrefix.EOA, AddressPrefix.CONTRACT])
    @pytest.mark.parametrize(
        "data_type,valid",
        [
            ("abc", False),
            (1, False),
            (1.1, False),
            (b"call", False),
        ]
    )
    def test_validate_data_type(self, context, revision, address_prefix, data_type, valid):
        to = Address(address_prefix, os.urandom(20))
        context.type = IconScoreContextType.INVOKE
        context.revision = revision

        if revision < Revision.IMPROVED_PRE_VALIDATOR.value or valid:
            IconPreValidator.validate_data_type(context, to, data_type)
        else:
            with pytest.raises(InvalidParamsException) as exc_info:
                IconPreValidator.validate_data_type(context, to, data_type)

            assert exc_info.value.message.startswith(f"Invalid dataType: {data_type}")
