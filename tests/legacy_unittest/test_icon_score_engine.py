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

import unittest
from unittest.mock import Mock, patch

from iconservice import *
from iconservice.base.address import AddressPrefix, SYSTEM_SCORE_ADDRESS, Address
from iconservice.base.exception import ScoreNotFoundException, InvalidParamsException
from iconservice.iconscore.icon_score_constant import ATTR_SCORE_GET_API, ATTR_SCORE_CALL, \
    ATTR_SCORE_VALIDATATE_EXTERNAL_METHOD
from iconservice.iconscore.icon_score_context import IconScoreContext
from iconservice.iconscore.icon_score_context import IconScoreContextType
from iconservice.iconscore.icon_score_engine import IconScoreEngine
from iconservice.iconscore.icon_score_mapper import IconScoreMapper
from tests import create_address


class TestIconScoreEngine(unittest.TestCase):
    @patch('iconservice.iconscore.icon_score_context_util.IconScoreContextUtil.validate_score_blacklist')
    def test_validate_score_blacklist(self,
                                      mocked_score_context_util_validate_score_blacklist):
        context = IconScoreContext(IconScoreContextType.INVOKE)

        # failure case: should not accept EOA as SCORE address
        eoa_address = create_address(AddressPrefix.EOA)
        self.assertRaises(InvalidParamsException,
                          IconScoreEngine._validate_score_blacklist,
                          context, eoa_address)
        mocked_score_context_util_validate_score_blacklist.assert_not_called()

        # failure case: should not accept None type as SCORE address
        none_address = None
        self.assertRaises(InvalidParamsException,
                          IconScoreEngine._validate_score_blacklist,
                          context, none_address)
        mocked_score_context_util_validate_score_blacklist.assert_not_called()

        # success case: valid SCORE address should be passed
        contract_address = create_address(AddressPrefix.CONTRACT)
        IconScoreEngine._validate_score_blacklist(context, contract_address)
        mocked_score_context_util_validate_score_blacklist.assert_called_with(context, contract_address)

    @patch('iconservice.iconscore.icon_score_engine.IconScoreEngine._validate_score_blacklist')
    @patch('iconservice.iconscore.icon_score_engine.IconScoreEngine._fallback')
    @patch('iconservice.iconscore.icon_score_engine.IconScoreEngine._call')
    def test_invoke(self,
                    mocked_score_engine_call,
                    mocked_score_engine_fallback,
                    mocked_score_engine_validate_score_blacklist):

        # success case: valid score. if data type is 'call', _call method should be called
        context = IconScoreContext(IconScoreContextType.INVOKE)
        data_type = 'call'
        data = {}
        mocked_score_engine_call.return_value = None
        mocked_score_engine_fallback.return_value = None

        contract_address = create_address(AddressPrefix.CONTRACT)
        IconScoreEngine.invoke(context, contract_address, data_type, data)
        mocked_score_engine_validate_score_blacklist.assert_called_with(context, contract_address)
        mocked_score_engine_call.assert_called()
        mocked_score_engine_fallback.assert_not_called()

        # reset mock
        mocked_score_engine_validate_score_blacklist.reset_mock(return_value=None)
        mocked_score_engine_call.reset_mock(return_value=None)
        mocked_score_engine_fallback.reset_mock(return_value=None)

        # success case: valid score. if data type is not 'call', fallback method should be called
        data_type = ''

        IconScoreEngine.invoke(context, contract_address, data_type, data)
        mocked_score_engine_call.assert_not_called()
        mocked_score_engine_fallback.assert_called()

    @patch('iconservice.iconscore.icon_score_engine.IconScoreEngine._validate_score_blacklist')
    @patch('iconservice.iconscore.icon_score_engine.IconScoreEngine._call')
    def test_query(self,
                   mocked_score_engine_call,
                   mocked_score_engine_validate_score_blacklist):

        # success case: valid score. if data type is 'call', _call method should be called
        context = IconScoreContext(IconScoreContextType.QUERY)
        data_type = 'call'
        data = {}

        mocked_score_engine_call.return_value = "_call_method_return_data"

        contract_address = create_address(AddressPrefix.CONTRACT)
        result = IconScoreEngine.query(context, contract_address, data_type, data)

        self.assertEqual(result, "_call_method_return_data")
        mocked_score_engine_validate_score_blacklist.assert_called_with(context, contract_address)
        mocked_score_engine_call.assert_called()

        # reset mock
        mocked_score_engine_validate_score_blacklist.reset_mock(return_value=None)
        mocked_score_engine_call.reset_mock(return_value=None)

        # failure case: valid score. if data type is not 'call', exception should be raised
        data_type = ''

        self.assertRaises(InvalidParamsException,
                          IconScoreEngine.query,
                          context, contract_address, data_type, data)
        mocked_score_engine_validate_score_blacklist.assert_called()
        mocked_score_engine_call.assert_not_called()

    @patch('iconservice.iconscore.icon_score_context_util.IconScoreContextUtil.get_icon_score')
    @patch('iconservice.iconscore.icon_score_engine.IconScoreEngine._validate_score_blacklist')
    def test_get_score_api(self,
                           mocked_icon_score_engine_validate_score_blacklist,
                           mocked_score_context_util_get_icon_score):
        context = IconScoreContext(IconScoreContextType.INVOKE)
        context.new_icon_score_mapper = IconScoreMapper()

        # failure case: should raise error if there is no SCORE
        score_address = create_address(AddressPrefix.CONTRACT)
        mocked_score_context_util_get_icon_score.return_value = None
        self.assertRaises(ScoreNotFoundException, IconScoreEngine.get_score_api, context, score_address)
        mocked_icon_score_engine_validate_score_blacklist.assert_called_with(context, score_address)

        # reset mock
        mocked_icon_score_engine_validate_score_blacklist.reset_mock(return_value=None)

        # success case: if SCORE exists, getattr(score, "__get_api") method should be called

        score_object = Mock(spec=IconScoreBase)
        mocked_score_context_util_get_icon_score.return_value = score_object

        IconScoreEngine.get_score_api(context, score_address)
        mocked_icon_score_engine_validate_score_blacklist.assert_called_with(context, score_address)
        get_api = getattr(score_object, ATTR_SCORE_GET_API)
        get_api.assert_called()

    @patch('iconservice.iconscore.icon_score_engine.IconScoreEngine._convert_score_params_by_annotations')
    @patch('iconservice.iconscore.icon_score_engine.IconScoreEngine._get_icon_score')
    def test_call(self,
                  mocked_score_engine_get_icon_score,
                  mocked_score_engine_convert_score_params_by_annotations):
        context = IconScoreContext(IconScoreContextType.INVOKE)
        context.new_icon_score_mapper = IconScoreMapper()

        def intercept_score_base_call(func_name: str, kw_params: dict):
            self.assertEqual(func_name, 'score_method')
            # should be equal to converted_params
            self.assertEqual(kw_params, converted_params)
            return "__call method called"

        score_address = Mock(spec=Address)
        score_object = Mock(spec=IconScoreBase)
        mocked_score_engine_get_icon_score.return_value = score_object

        primitive_params = {"address": str(create_address(AddressPrefix.EOA)),
                            "integer": "0x10"}
        converted_params = {"address": create_address(AddressPrefix.EOA),
                            "integer": 10}
        mocked_score_engine_convert_score_params_by_annotations.return_value = converted_params
        context.set_func_type_by_icon_score = Mock()
        setattr(score_object, ATTR_SCORE_CALL, Mock(side_effect=intercept_score_base_call))

        # set method, and params, method cannot be None as pre-validate it
        data = {'method': 'score_method',
                'params': primitive_params}
        result = IconScoreEngine._call(context, score_address, data)

        self.assertEqual(result, "__call method called")
        IconScoreEngine._get_icon_score.assert_called()
        IconScoreEngine._convert_score_params_by_annotations.assert_called()
        context.set_func_type_by_icon_score.assert_called()
        call = getattr(score_object, ATTR_SCORE_CALL)
        call.assert_called()

    def test_convert_score_params_by_annotations(self):
        # main function is to converting params based on method annotation
        def test_method(address: Address, integer: int):
            pass

        # success case: valid params and method
        primitive_params = {"address": str(create_address(AddressPrefix.EOA)),
                            "integer": "0x10"}
        context = Mock(spec=IconScoreContext)
        score_object = Mock(spec=IconScoreBase)

        setattr(score_object, ATTR_SCORE_VALIDATATE_EXTERNAL_METHOD, Mock())
        setattr(score_object, 'test_method', test_method)
        converted_params = \
            IconScoreEngine._convert_score_params_by_annotations(context, score_object, 'test_method', primitive_params)

        validate_external_method = getattr(score_object, ATTR_SCORE_VALIDATATE_EXTERNAL_METHOD)
        validate_external_method.assert_called()
        # primitive_params must not be changed.
        self.assertEqual(type(primitive_params["address"]), str)
        self.assertEqual(type(converted_params["address"]), Address)

        # failure case: if arguments' type and parameters' type of method does not match, should raise an error
        not_matching_type_params = {"address": b'bytes_data',
                                    "integer": "string_data"}

        self.assertRaises(InvalidParamsException,
                          IconScoreEngine._convert_score_params_by_annotations,
                          context, score_object, 'test_method', not_matching_type_params)

        # success case: even though not enough number of params inputted, doesn't raise an error
        # parameter check is processed when executing method.
        validate_external_method = getattr(score_object, ATTR_SCORE_VALIDATATE_EXTERNAL_METHOD)
        validate_external_method.reset_mock()
        insufficient_params = {"address": str(create_address(AddressPrefix.EOA))}
        converted_params = \
            IconScoreEngine._convert_score_params_by_annotations(context, score_object, 'test_method', insufficient_params)

        validate_external_method = getattr(score_object, ATTR_SCORE_VALIDATATE_EXTERNAL_METHOD)
        validate_external_method.assert_called()
        self.assertEqual(type(insufficient_params["address"]), str)
        self.assertEqual(type(converted_params["address"]), Address)

    def test_fallback(self):
        pass
