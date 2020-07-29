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

    merge_arguments(params, parameters, args, kwargs)
    set_default_value_to_params(params, parameters)

    for name, parameter in parameters.items():
        if name not in params:
            raise InvalidParamsException(f"Argument not found: name={name}")

        type_hint = parameter.annotation
        value = params[name]

        try:
            verify_type_hint(value, type_hint)
        except TypeError:
            raise InvalidParamsException(
                f"Type mismatch: name={name} type_hint={type_hint} value_type={type(value)}")


def merge_arguments(
        params: Dict[str, Any],
        parameters: Mapping[str, Parameter],
        args: Optional[Tuple], kwargs: Optional[Dict]):
    """Merge args and kwargs to a dictionary

    Type checking and parameter default value will be handled in the next phase

    :param params: dictionary which will contain merged arguments from args and kwargs
    :param parameters: function signature
    :param args: arguments in tuple
    :param kwargs: keyword arguments in dict
    :return:
    """
    if len(args) > len(parameters):
        raise InvalidParamsException(f"Too many arguments")

    for arg, k in zip(args, parameters):
        params[k] = arg

    for k in kwargs:
        if k in params:
            raise InvalidParamsException(f"Duplicated argument: name={k} value={kwargs[k]}")

        if k not in parameters:
            raise InvalidParamsException(f"Invalid argument: name={k} value={kwargs[k]}")

        params[k] = kwargs[k]


def set_default_value_to_params(params: Dict[str, Any], parameters: Mapping[str, Parameter]):
    """Set default parameter value to missing parameter

    If No default parameter value is available for missing argument, an exception is raised

    :param params:
    :param parameters:
    :return:
    """
    if len(params) == len(parameters):
        return

    # Set default parameter values to missing arguments
    for k in parameters:
        if k in params:
            continue

        parameter = parameters[k]
        if parameter.default is Parameter.empty:
            raise InvalidParamsException(
                f"Missing argument: name={k} type={parameter.annotation}")

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


def verify_struct_type_hint(value: Dict[str, Any], type_hint: type):
    annotations = get_annotations(type_hint, None)
    assert annotations is not None

    for name, type_hint in annotations.items():
        if name not in value:
            raise InvalidParamsException(f"Missing field in struct: name={name}")

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
    if value is None:
        return

    args = get_args(type_hint)
    verify_type_hint(value, args[0])
