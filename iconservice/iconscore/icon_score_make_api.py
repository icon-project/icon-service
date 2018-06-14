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

from inspect import signature, Signature, Parameter
from typing import TYPE_CHECKING, Any
from ..base.exception import IconScoreException
from ..base.type_converter import score_base_support_type
from .icon_score_class import Indexed, ConstBitFlag, CONST_BIT_FLAG, STR_FALLBACK

if TYPE_CHECKING:
    from .icon_score_base import IconScoreBase


class MakeScoreApi:
    CONST_CLASS_API = '__api'

    __API_TYPE = 'type'
    __API_NAME = 'name'
    __API_INPUTS = 'inputs'
    __API_OUTPUTS = 'outputs'
    __API_PAYABLE = 'payable'
    __API_READONLY = 'readonly'
    __API_INPUTS_INDEXED = 'indexed'
    __API_PARAMS_ADDRESS = 'Address'
    __API_PARAMS_INDEXED = 'Indexed'
    __API_TYPE_FUNCTION = 'function'
    __API_TYPE_EVENT = 'eventlog'
    __API_TYPE_ON_INSTALL = 'on_install'
    __API_TYPE_ON_UPDATE = 'on_update'
    __API_TYPE_FALLBACK = STR_FALLBACK

    @staticmethod
    def make_api(score_cls: 'IconScoreBase', score_funcs: list) -> None:
        api = []

        MakeScoreApi.__make_functions(api, score_funcs)
        MakeScoreApi.__make_events(api, score_funcs)

        setattr(score_cls, MakeScoreApi.CONST_CLASS_API, api)

    @staticmethod
    def __make_functions(src: list, score_funcs: list) -> None:

        for func in score_funcs:
            const_bit_flag = getattr(func, CONST_BIT_FLAG, 0)
            is_readonly = const_bit_flag & ConstBitFlag.ReadOnly == ConstBitFlag.ReadOnly
            is_payable = const_bit_flag & ConstBitFlag.Payable == ConstBitFlag.Payable

            if const_bit_flag & ConstBitFlag.External and func.__name__ != STR_FALLBACK:
                src.append(MakeScoreApi.__make_normal_function(func.__name__, is_readonly, is_payable, signature(func)))
            elif func.__name__ == MakeScoreApi.__API_TYPE_FALLBACK:
                src.append(MakeScoreApi.__make_fallback_function(func.__name__, is_payable, signature(func)))
            elif func.__name__ == MakeScoreApi.__API_TYPE_ON_INSTALL:
                src.append(MakeScoreApi.__make_on_install_function(func.__name__, signature(func)))
            elif func.__name__ == MakeScoreApi.__API_TYPE_ON_UPDATE:
                src.append(MakeScoreApi.__make_on_update_function(func.__name__, signature(func)))

    @staticmethod
    def __make_normal_function(func_name: str, is_readonly: bool, is_payable: bool, sig_info: 'Signature') -> dict:
        info = dict()
        info[MakeScoreApi.__API_TYPE] = MakeScoreApi.__API_TYPE_FUNCTION
        info[MakeScoreApi.__API_NAME] = func_name
        info[MakeScoreApi.__API_INPUTS] = MakeScoreApi.__make_inputs(dict(sig_info.parameters))
        info[MakeScoreApi.__API_READONLY] = is_readonly
        info[MakeScoreApi.__API_PAYABLE] = is_payable
        info[MakeScoreApi.__API_OUTPUTS] = MakeScoreApi.__make_output(sig_info.return_annotation)
        return info

    @staticmethod
    def __make_fallback_function(func_name: str, is_payable: bool, sig_info: 'Signature') -> dict:
        info = dict()
        info[MakeScoreApi.__API_TYPE] = MakeScoreApi.__API_TYPE_FALLBACK
        info[MakeScoreApi.__API_NAME] = func_name
        info[MakeScoreApi.__API_INPUTS] = MakeScoreApi.__make_inputs(dict(sig_info.parameters))
        info[MakeScoreApi.__API_PAYABLE] = is_payable
        return info

    @staticmethod
    def __make_on_install_function(func_name: str, sig_info: 'Signature') -> dict:
        info = dict()
        info[MakeScoreApi.__API_TYPE] = MakeScoreApi.__API_TYPE_ON_INSTALL
        info[MakeScoreApi.__API_NAME] = func_name
        info[MakeScoreApi.__API_INPUTS] = MakeScoreApi.__make_inputs(dict(sig_info.parameters))
        return info

    @staticmethod
    def __make_on_update_function(func_name: str, sig_info: 'Signature') -> dict:
        info = dict()
        info[MakeScoreApi.__API_TYPE] = MakeScoreApi.__API_TYPE_ON_UPDATE
        info[MakeScoreApi.__API_NAME] = func_name
        info[MakeScoreApi.__API_INPUTS] = MakeScoreApi.__make_inputs(dict(sig_info.parameters))
        return info

    @staticmethod
    def __make_events(src: list, score_funcs: list) -> None:

        event_funcs = {func.__name__: signature(func) for func in score_funcs
                       if getattr(func, CONST_BIT_FLAG, 0) & ConstBitFlag.EventLog}

        for func_name, event in event_funcs.items():
            src.append(MakeScoreApi.__make_event(func_name, event))

    @staticmethod
    def __make_event(func_name: str, sig_info: 'Signature') -> dict:
        info = dict()
        info[MakeScoreApi.__API_TYPE] = MakeScoreApi.__API_TYPE_EVENT
        info[MakeScoreApi.__API_NAME] = func_name
        info[MakeScoreApi.__API_INPUTS] = MakeScoreApi.__make_inputs(dict(sig_info.parameters), is_eventlog=True)
        return info

    @staticmethod
    def __make_output(params_type: Any) -> list:
        info_list = []

        if params_type is Signature.empty:
            return info_list

        info = dict()
        converted_type, _ = MakeScoreApi.__make_type(params_type)
        info[MakeScoreApi.__API_TYPE] = converted_type
        info_list.append(info)
        return info_list

    @staticmethod
    def __make_inputs(params: dict, is_eventlog: bool = False) -> list:
        tmp_list = []
        for param_name, param in params.items():
            MakeScoreApi.__make_input(tmp_list, param, is_eventlog)
        return tmp_list

    @staticmethod
    def __make_input(src: list, param: 'Parameter', is_eventlog: bool):
        if param.name == 'self' or param.name == 'cls':
            return

        info = dict()
        info[MakeScoreApi.__API_NAME] = param.name
        convert_type, is_indexed = MakeScoreApi.__make_type(param.annotation)
        info[MakeScoreApi.__API_TYPE] = convert_type
        if is_eventlog:
            info[MakeScoreApi.__API_INPUTS_INDEXED] = is_indexed
        src.append(info)

    @staticmethod
    def __make_type(param_type: Any) -> (str, bool):
        indexed = False
        converted_type = ''

        if param_type in score_base_support_type:
            converted_type = MakeScoreApi.__convert_type(param_type)
        else:
            for sub in param_type._subs_tree():
                if sub is Indexed:
                    indexed = True
                else:
                    converted_type = MakeScoreApi.__convert_type(sub)

        return converted_type, indexed

    @staticmethod
    def __convert_type(src_type: Any) -> str:
        if src_type in score_base_support_type:
            return src_type.__name__
        else:
            raise IconScoreException(f"can't convert {src_type}")
