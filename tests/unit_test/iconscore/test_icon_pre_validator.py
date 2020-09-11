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
import copy
from unittest.mock import Mock

import pytest

from iconservice.base.address import Address, is_icon_address_valid
from iconservice.base.address import SYSTEM_SCORE_ADDRESS
from iconservice.base.exception import InvalidRequestException
from iconservice.base.type_converter_templates import ConstantKeys
from iconservice.icon_constant import Revision
from iconservice.iconscore.icon_pre_validator import IconPreValidator
from iconservice.iconscore.icon_score_context import IconScoreContext, IconScoreContextType
from iconservice.icx import IcxEngine, IcxStorage
from iconservice.utils import ContextEngine, ContextStorage
from iconservice.utils.locked import LOCKED_ADDRESSES
from tests import create_address, create_tx_hash


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
        "version",
        [
            None,
            hex(2),
            hex(3),
            "3"
            "0x003"
        ]
    )
    @pytest.mark.parametrize(
        "value",
        [
            None,
            hex(1),
            "1"
            "0x001"
        ]
    )
    @pytest.mark.parametrize(
        "step_limit",
        [
            None,
            hex(1),
            "1"
            "0x001"
        ]
    )
    @pytest.mark.parametrize(
        "timestamp",
        [
            None,
            hex(1),
            "1",
            "0x001"
        ]
    )
    @pytest.mark.parametrize(
        "nonce",
        [
            None,
            hex(1),
            "1",
            "0x001"
        ]
    )
    @pytest.mark.parametrize(
        "to",
        [
            None,
            str(create_address(0)),
            str(create_address(1)),
            str(create_address(0))[2:],
            str(create_address(0))[:10],
        ]
    )
    @pytest.mark.parametrize(
        "fee",
        [
            None,
            hex(1),
            "123",
        ]
    )
    @pytest.mark.parametrize(
        "tx_hash",
        [
            None,
            create_tx_hash().hex(),
        ]
    )
    def test_origin_request_execute(
            self,
            version: str,
            value: str,
            step_limit: str,
            timestamp: str,
            nonce: str,
            to: str,
            fee: str,
            tx_hash: str,
    ):
        revision: int = Revision.IMPROVED_PRE_VALIDATOR.value
        validator = IconPreValidator()
        origin_request = {}

        def set_value(value, key):
            if origin_request:
                if value:
                    origin_request[ConstantKeys.PARAMS][key] = value
                elif key in origin_request[ConstantKeys.PARAMS]:
                    del origin_request[ConstantKeys.PARAMS][key]

        params: list = [
            (version, ConstantKeys.VERSION),
            (value, ConstantKeys.VALUE),
            (step_limit, ConstantKeys.STEP_LIMIT),
            (timestamp, ConstantKeys.TIMESTAMP),
            (nonce, ConstantKeys.NONCE),
            (to, ConstantKeys.TO),
            (fee, ConstantKeys.FEE),
            (tx_hash, ConstantKeys.OLD_TX_HASH)
        ]
        for value, key in params:
            set_value(value, key)

        if origin_request:
            if version is None:
                with pytest.raises(InvalidRequestException) as e:
                    validator.origin_request_execute(revision=revision, origin_request=origin_request)
                assert f"The version field is essential." == e.value
            elif version == hex(2):
                with pytest.raises(InvalidRequestException) as e:
                    validator.origin_request_execute(revision=revision, origin_request=origin_request)
                assert f"Version2 is deprecated." == e.value
            elif version not in [hex(3)]:
                with pytest.raises(InvalidRequestException) as e:
                    validator.origin_request_execute(revision=revision, origin_request=origin_request)
                assert f"Malformed int: {version}" == e.value

            key_list: list = [
                value,
                step_limit,
                timestamp,
                nonce,
            ]
            for key in key_list:
                if key not in [None, hex(1)]:
                    with pytest.raises(InvalidRequestException) as e:
                        validator.origin_request_execute(revision=revision, origin_request=origin_request)
                    assert f"Malformed int: {key}" == e.value

            if not is_icon_address_valid(to):
                with pytest.raises(InvalidRequestException) as e:
                    validator.origin_request_execute(revision=revision, origin_request=origin_request)
                assert f"Malformed address: {to}" == e.value

            key_list: list = [
                fee,
                tx_hash,
            ]
            for key in key_list:
                if key not in [None]:
                    with pytest.raises(InvalidRequestException) as e:
                        validator.origin_request_execute(revision=revision, origin_request=origin_request)
                    assert f"Invalid v2 field: {key}" == e.value
        else:
            validator.origin_request_execute(revision=revision, origin_request=origin_request)
