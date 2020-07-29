# -*- coding: utf-8 -*-
# Copyright 2020 ICON Foundation Inc.
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

from collections import OrderedDict
from enum import Flag, auto
from inspect import Signature, Parameter
from typing import Optional, Dict, Union, Any, List

from . import (
    BaseObject,
    is_base_type,
    is_struct,
    name_to_type,
    get_origin,
    get_args,
    get_annotations,
)
from .verification import set_default_value_to_params
from ...base.address import Address
from ...base.exception import InvalidParamsException


def base_object_to_str(value: Any) -> str:
    if isinstance(value, Address):
        return str(value)
    elif isinstance(value, int):
        return hex(value)
    elif isinstance(value, bytes):
        return bytes_to_hex(value)
    elif isinstance(value, bool):
        return hex(value)
    elif isinstance(value, str):
        return value

    raise TypeError(f"Unsupported type: {type(value)}")


def object_to_str(value: Any) -> Union[Any]:
    if is_base_type(type(value)):
        return base_object_to_str(value)

    if isinstance(value, list):
        return [object_to_str(i) for i in value]

    if isinstance(value, dict):
        return {k: object_to_str(value[k]) for k in value}

    if value is None:
        return None

    raise TypeError(f"Unsupported type: {type(value)}")


def str_to_base_object_by_type_name(type_name: str, value: str) -> BaseObject:
    return str_to_base_object(value, name_to_type(type_name))


def str_to_int(value: str) -> int:
    if isinstance(value, int):
        return value

    base = 16 if is_hex(value) else 10
    return int(value, base)


def str_to_base_object(value: str, type_hint: type) -> BaseObject:
    if not isinstance(value, str):
        raise InvalidParamsException(f"Type mismatch: value={value} type_hint={type_hint}")

    if type_hint is bool:
        return bool(str_to_int(value))
    if type_hint is bytes:
        return hex_to_bytes(value)
    if type_hint is int:
        return str_to_int(value)
    if type_hint is str:
        return value
    if type_hint is Address:
        return Address.from_string(value)

    raise InvalidParamsException(f"Unknown type: {type_hint}")


def bytes_to_hex(value: bytes, prefix: str = "0x") -> str:
    return f"{prefix}{value.hex()}"


def hex_to_bytes(value: Optional[str]) -> Optional[bytes]:
    if value is None:
        return None

    if value.startswith("0x"):
        value = value[2:]

    return bytes.fromhex(value)


def is_hex(value: str) -> bool:
    return value.startswith("0x") or value.startswith("-0x")


class ConvertOption(Flag):
    NONE = 0
    IGNORE_UNKNOWN_PARAMS = auto()


def convert_score_parameters(
        params: Dict[str, Any],
        sig: Signature,
        options: ConvertOption = ConvertOption.NONE):
    """Convert string values in score parameters to object values

    :param params:
    :param sig:
    :param options:
    :return:
    """
    _verify_arguments(params, sig)

    converted_params = {}
    parameters = sig.parameters

    for k, v in params.items():
        if not isinstance(k, str):
            raise InvalidParamsException(f"Invalid key type: key={k}")

        try:
            parameter: Parameter = parameters[k]
            converted_params[k] = str_to_object(v, parameter.annotation)
        except KeyError:
            if not (options & ConvertOption.IGNORE_UNKNOWN_PARAMS):
                raise InvalidParamsException(f"Unknown param: key={k} value={v}")

    set_default_value_to_params(params, parameters)

    return converted_params


def _verify_arguments(params: Dict[str, Any], sig: Signature):
    """Check if all required arguments are present

    :param params:
    :param sig: normalized signature
    :return:
    """
    parameters = sig.parameters

    for k in parameters:
        parameter: Parameter = parameters[k]
        param = params.get(k, parameter.default)

        if param is Parameter.empty:
            raise InvalidParamsException(f"Argument not found: {k}")


def str_to_object(value: Union[str, list, dict, None], type_hint: type) -> Any:
    if not isinstance(value, (dict, list, str, type(None))):
        raise InvalidParamsException(f"Invalid value type: {value}")

    origin = get_origin(type_hint)

    if is_base_type(origin):
        return str_to_base_object(value, origin)
    elif is_struct(origin):
        return str_to_object_in_struct(value, type_hint)
    elif origin is list:
        return str_to_object_in_list(value, type_hint)
    elif origin is dict:
        return str_to_object_in_dict(value, type_hint)
    elif origin is Union:
        # Assume that only the specific type of Union (= Optional) is allowed in iconservice
        return str_to_object_in_union(value, type_hint)

    raise InvalidParamsException(f"Type mismatch: value={value} type_hint={type_hint}")


def str_to_object_in_struct(value: Dict[str, Optional[str]], type_hint: type) -> Dict[str, Any]:
    if not isinstance(value, dict):
        raise InvalidParamsException(f"Type mismatch: value={value} type_hint={type_hint}")

    annotations = get_annotations(type_hint, None)

    ret = OrderedDict()

    for k, v in value.items():
        if k not in annotations:
            raise InvalidParamsException(f"Unknown field in struct: key={k}")

        ret[k] = str_to_object(v, annotations[k])

    if len(ret) != len(annotations):
        raise InvalidParamsException(f"Missing field in struct")

    return ret


def str_to_object_in_list(value: List[Any], type_hint: type) -> List[Any]:
    if not isinstance(value, list):
        raise InvalidParamsException(f"Type mismatch: value={value} type_hint={type_hint}")

    args = get_args(type_hint)
    return [str_to_object(i, args[0]) for i in value]


def str_to_object_in_dict(value: Dict[str, Any], type_hint: type) -> Dict[str, Any]:
    if not isinstance(value, dict):
        raise InvalidParamsException(f"Type mismatch: value={value} type_hint={type_hint}")

    args = get_args(type_hint)
    return OrderedDict(
        (k, str_to_object(v, type_hint=args[1])) for k, v in value.items()
    )


def str_to_object_in_union(value: Union[Any], type_hint: type) -> Optional[Any]:
    args = get_args(type_hint)
    return None if value is None else str_to_object(value, args[0])
