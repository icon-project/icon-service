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

from inspect import (
    Signature,
    Parameter,
)
from typing import Optional, Tuple, Dict, Any, List, Mapping, Union

from typing_extensions import TypedDict

from . import (
    get_origin,
    get_args,
    get_annotations,
    is_base_type,
    is_struct,
    isinstance_ex,
)
from ...base.exception import InvalidParamsException


def verify_internal_call_arguments(sig: Signature, args: Optional[Tuple], kwargs: Optional[Dict]):
    """Check if argument types matches to type hints in sig.parameters

    :param sig: normalized signature of method in SCORE
    :param args: args in tuple
    :param kwargs:
    :return:
    """
    if args is None:
        args = ()
    if kwargs is None:
        kwargs = {}

    params: Dict[str, Any] = {}
    parameters = sig.parameters

    bind_arguments(params, parameters, args, kwargs)
    add_default_value_to_params(params, parameters)

    for name, parameter in parameters.items():
        if name not in params:
            raise InvalidParamsException(f"Argument not found: name={name}")

        type_hint = parameter.annotation
        value = params[name]

        try:
            verify_type_hint(value, type_hint)
        except:
            raise InvalidParamsException(
                f"Type mismatch: name={name} type_hint={type_hint} value_type={type(value)}")


def bind_arguments(
        params: Dict[str, Any],
        parameters: Mapping[str, Parameter],
        args: Optional[Tuple], kwargs: Optional[Dict]) -> Dict[str, Any]:
    for arg, k in zip(args, parameters):
        params[k] = arg

    for k in kwargs:
        if k in params:
            raise InvalidParamsException(f"Duplicated argument: name={k} value={kwargs[k]}")

        if k not in parameters:
            raise InvalidParamsException(f"Invalid argument: name={k} value={kwargs[k]}")

        params[k] = kwargs[k]

    return params


def add_default_value_to_params(params: Dict[str, Any], parameters: Mapping[str, Parameter]):
    if len(params) == len(parameters):
        return

    # fill default values in params:
    for k in parameters:
        if k in params:
            continue

        parameter = parameters[k]
        if parameter is Parameter.empty:
            raise InvalidParamsException(f"Argument not found: name={k}")

        params[k] = parameter.default


def verify_type_hint(value: Any, type_hint: type):
    origin: type = get_origin(type_hint)

    if is_base_type(origin):
        if not isinstance_ex(value, origin):
            raise TypeError
    elif is_struct(origin):
        verify_struct_type_hint(value, type_hint)
    elif origin is list:
        verify_list_type_hint(value, type_hint)
    elif origin is dict:
        verify_dict_type_hint(value, type_hint)
    elif origin is Union:
        verify_union_type_hint(value, type_hint)
    else:
        raise TypeError


def verify_struct_type_hint(value: TypedDict, type_hint: type):
    annotations = get_annotations(type_hint, None)
    assert annotations is not None

    for name, type_hint in annotations.items():
        verify_type_hint(value[name], type_hint)


def verify_list_type_hint(values: List[Any], type_hint: type):
    args = get_args(type_hint)

    for value in values:
        verify_type_hint(value, args[0])


def verify_dict_type_hint(values: Dict[str, Any], type_hint: type):
    args = get_args(type_hint)
    key_type_hint = args[0]
    value_type_hint = args[1]

    assert key_type_hint is str

    for k, v in values.items():
        if not isinstance_ex(k, key_type_hint):
            raise TypeError

        verify_type_hint(v, value_type_hint)


def verify_union_type_hint(value: Union[Any, None], type_hint: type):
    args = get_args(type_hint)
    verify_type_hint(value, args[0])
