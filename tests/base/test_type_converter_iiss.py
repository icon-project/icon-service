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

import unittest

from iconservice.base.type_converter import TypeConverter
from iconservice.base.type_converter_templates import ParamType, ConstantKeys
from tests import create_address


class TestTypeConverter(unittest.TestCase):

    def test_set_stake(self):
        stake = 1 * 10 ** 18

        request = {
            ConstantKeys.VALUE: hex(stake),
        }

        ret_params = TypeConverter.convert(request, ParamType.IISS_SET_STAKE)
        self.assertEqual(stake, ret_params[ConstantKeys.VALUE])

    def test_get_stake(self):
        address = create_address()

        request = {
            ConstantKeys.ADDRESS: str(address),
        }

        ret_params = TypeConverter.convert(request, ParamType.IISS_GET_STAKE)
        self.assertEqual(address, ret_params[ConstantKeys.ADDRESS])

    def test_set_delegation(self):
        address1 = create_address()
        value1 = 1 * 10 ** 18

        address2 = create_address()
        value2 = 2 * 10 ** 18

        request = {
            ConstantKeys.DELEGATIONS: [
                {
                    ConstantKeys.ADDRESS: str(address1),
                    ConstantKeys.VALUE: hex(value1)
                },
                {
                    ConstantKeys.ADDRESS: str(address2),
                    ConstantKeys.VALUE: hex(value2)
                }
            ]
        }

        ret_params = TypeConverter.convert(request, ParamType.IISS_SET_DELEGATION)
        ret_delegations = ret_params[ConstantKeys.DELEGATIONS]
        self.assertEqual(address1, ret_delegations[0][ConstantKeys.ADDRESS])
        self.assertEqual(value1, ret_delegations[0][ConstantKeys.VALUE])
        self.assertEqual(address2, ret_delegations[1][ConstantKeys.ADDRESS])
        self.assertEqual(value2, ret_delegations[1][ConstantKeys.VALUE])

    def test_get_delegation(self):
        address = create_address()

        request = {
            ConstantKeys.ADDRESS: str(address),
        }

        ret_params = TypeConverter.convert(request, ParamType.IISS_GET_DELEGATION)
        self.assertEqual(address, ret_params[ConstantKeys.ADDRESS])

    def test_claim_i_score(self):

        request = {}

        ret_params = TypeConverter.convert(request, ParamType.IISS_CLAIM_ISCORE)
        self.assertEqual({}, ret_params)

    def test_query_i_score(self):
        address = create_address()

        request = {
            ConstantKeys.ADDRESS: str(address),
        }

        ret_params = TypeConverter.convert(request, ParamType.IISS_QUERY_ISCORE)
        self.assertEqual(address, ret_params[ConstantKeys.ADDRESS])

    def test_reg_prep_candidate(self):
        name = "name"
        email = 'email'
        website = "website"
        json = "json"
        ip = "ip"
        incentive_rep = 10000

        request = {
            ConstantKeys.NAME: name,
            ConstantKeys.EMAIL: email,
            ConstantKeys.WEBSITE: website,
            ConstantKeys.JSON: json,
            ConstantKeys.TARGET: ip,
            ConstantKeys.GOVERNANCE_VARIABLE: {
                ConstantKeys.INCENTIVE_REP: hex(incentive_rep)
            }
        }

        ret_params = TypeConverter.convert(request, ParamType.IISS_REG_PREP_CANDIDATE)
        self.assertEqual(name, ret_params[ConstantKeys.NAME])
        self.assertEqual(email, ret_params[ConstantKeys.EMAIL])
        self.assertEqual(website, ret_params[ConstantKeys.WEBSITE])
        self.assertEqual(json, ret_params[ConstantKeys.JSON])
        self.assertEqual(ip, ret_params[ConstantKeys.TARGET])
        governance = ret_params[ConstantKeys.GOVERNANCE_VARIABLE]
        self.assertEqual(incentive_rep, governance[ConstantKeys.INCENTIVE_REP])

    def test_unreg_prep_candidate(self):

        request = {}

        ret_params = TypeConverter.convert(request, ParamType.IISS_UNREG_PREP_CANDIDATE)
        self.assertEqual({}, ret_params)

    def test_set_prep_candidate(self):
        website = "website"
        incentive_rep = 10000

        request = {
            ConstantKeys.WEBSITE: website,
            ConstantKeys.GOVERNANCE_VARIABLE: {
                ConstantKeys.INCENTIVE_REP: hex(incentive_rep)
            }
        }

        ret_params = TypeConverter.convert(request, ParamType.IISS_SET_PREP_CANDIDATE)
        self.assertEqual(website, ret_params[ConstantKeys.WEBSITE])
        governance = ret_params[ConstantKeys.GOVERNANCE_VARIABLE]
        self.assertEqual(incentive_rep, governance[ConstantKeys.INCENTIVE_REP])

    def test_get_prep_candidate(self):
        address = create_address()

        request = {
            ConstantKeys.ADDRESS: str(address),
        }

        ret_params = TypeConverter.convert(request, ParamType.IISS_GET_PREP_CANDIDATE)
        self.assertEqual(address, ret_params[ConstantKeys.ADDRESS])

    def test_get_prep_candidate_delegation_info(self):
        address = create_address()

        request = {
            ConstantKeys.ADDRESS: str(address),
        }

        ret_params = TypeConverter.convert(request, ParamType.IISS_GET_PREP_CANDIDATE_DELEGATION_INFO)
        self.assertEqual(address, ret_params[ConstantKeys.ADDRESS])

    def test_get_prep_list(self):

        request = {}

        ret_params = TypeConverter.convert(request, ParamType.IISS_GET_PREP_LIST)
        self.assertEqual({}, ret_params)

    def test_get_prep_candidate_list(self):
        start_rank = 10
        end_rank = 20

        request = {
            ConstantKeys.START_RANK: hex(start_rank),
            ConstantKeys.END_RANK: hex(end_rank)
        }

        ret_params = TypeConverter.convert(request, ParamType.IISS_GET_PREP_CANDIDATE_LIST)
        self.assertEqual(start_rank, ret_params[ConstantKeys.START_RANK])
        self.assertEqual(end_rank, ret_params[ConstantKeys.END_RANK])
