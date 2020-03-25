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

from iconservice.base.type_converter import TypeConverter
from iconservice.base.type_converter_templates import ParamType, ConstantKeys
from tests import create_address


def test_set_stake():
    stake = 1 * 10 ** 18

    request = {
        ConstantKeys.VALUE: hex(stake),
    }

    ret_params = TypeConverter.convert(request, ParamType.IISS_SET_STAKE)
    assert stake == ret_params[ConstantKeys.VALUE]


def test_get_stake():
    address = create_address()

    request = {
        ConstantKeys.ADDRESS: str(address),
    }

    ret_params = TypeConverter.convert(request, ParamType.IISS_GET_STAKE)
    assert address == ret_params[ConstantKeys.ADDRESS]


def test_set_delegation():
    address1 = create_address()
    value1 = 1 * 10 ** 18

    address2 = create_address()
    value2 = 2 * 10 ** 18

    request = [
        {
            ConstantKeys.ADDRESS: str(address1),
            ConstantKeys.VALUE: hex(value1)
        },
        {
            ConstantKeys.ADDRESS: str(address2),
            ConstantKeys.VALUE: hex(value2)
        }
    ]

    ret_params = TypeConverter.convert(request, ParamType.IISS_SET_DELEGATION)
    assert address1 == ret_params[0][ConstantKeys.ADDRESS]
    assert value1 == ret_params[0][ConstantKeys.VALUE]
    assert address2 == ret_params[1][ConstantKeys.ADDRESS]
    assert value2 == ret_params[1][ConstantKeys.VALUE]


def test_get_delegation():
    address = create_address()

    request = {
        ConstantKeys.ADDRESS: str(address),
    }

    ret_params = TypeConverter.convert(request, ParamType.IISS_GET_DELEGATION)
    assert address == ret_params[ConstantKeys.ADDRESS]


def test_claim_i_score():

    request = {}

    ret_params = TypeConverter.convert(request, ParamType.IISS_CLAIM_ISCORE)
    assert {} == ret_params


def test_query_i_score():
    address = create_address()

    request = {
        ConstantKeys.ADDRESS: str(address),
    }

    ret_params = TypeConverter.convert(request, ParamType.IISS_QUERY_ISCORE)
    assert address == ret_params[ConstantKeys.ADDRESS]


def test_reg_prep():
    name = "name"
    email = 'email'
    website = "website"
    json = "json"
    ip = "ip"

    request = {
        ConstantKeys.NAME: name,
        ConstantKeys.EMAIL: email,
        ConstantKeys.WEBSITE: website,
        ConstantKeys.DETAILS: json,
        ConstantKeys.P2P_ENDPOINT: ip,
    }

    ret_params = TypeConverter.convert(request, ParamType.IISS_REG_PREP)
    assert name == ret_params[ConstantKeys.NAME]
    assert email == ret_params[ConstantKeys.EMAIL]
    assert website == ret_params[ConstantKeys.WEBSITE]
    assert json == ret_params[ConstantKeys.DETAILS]
    assert ip == ret_params[ConstantKeys.P2P_ENDPOINT]


def test_unreg_prep():

    request = {}

    ret_params = TypeConverter.convert(request, ParamType.IISS_UNREG_PREP)
    assert {} == ret_params


def test_set_prep():
    name = "name"
    email = 'email'
    website = "website"
    json = "json"
    ip = "ip"

    request = {
        ConstantKeys.NAME: name,
        ConstantKeys.EMAIL: email,
        ConstantKeys.WEBSITE: website,
        ConstantKeys.DETAILS: json,
        ConstantKeys.P2P_ENDPOINT: ip,
    }

    ret_params = TypeConverter.convert(request, ParamType.IISS_SET_PREP)
    assert name == ret_params[ConstantKeys.NAME]
    assert email == ret_params[ConstantKeys.EMAIL]
    assert website == ret_params[ConstantKeys.WEBSITE]
    assert json == ret_params[ConstantKeys.DETAILS]
    assert ip == ret_params[ConstantKeys.P2P_ENDPOINT]


def test_set_governance_variable():
    irep = 12345

    request = {
        ConstantKeys.IREP: hex(irep),
    }

    ret_params = TypeConverter.convert(request, ParamType.IISS_SET_GOVERNANCE_VARIABLES)
    assert irep == ret_params[ConstantKeys.IREP]


def test_get_prep():
    address = create_address()

    request = {
        ConstantKeys.ADDRESS: str(address),
    }

    ret_params = TypeConverter.convert(request, ParamType.IISS_GET_PREP)
    assert address == ret_params[ConstantKeys.ADDRESS]


def test_get_main_prep_list():

    request = {}

    ret_params = TypeConverter.convert(request, ParamType.IISS_GET_MAIN_PREP_LIST)
    assert {} == ret_params


def test_get_prep_list():
    start_rank = 10
    end_rank = 20

    request = {
        ConstantKeys.START_RANKING: hex(start_rank),
        ConstantKeys.END_RANKING: hex(end_rank)
    }

    ret_params = TypeConverter.convert(request, ParamType.IISS_GET_PREP_LIST)
    assert start_rank == ret_params[ConstantKeys.START_RANKING]
    assert end_rank == ret_params[ConstantKeys.END_RANKING]
