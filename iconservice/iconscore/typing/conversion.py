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

from inspect import Signature, Parameter
from typing import Optional, Dict, Union, Type, List, Any
from enum import Flag, auto

from . import (
    BaseObject,
    is_base_type,
    is_struct,
    name_to_type,
    get_origin,
    get_args,
    get_annotations,
)
from ...base.address import Address
from ...base.exception import InvalidParamsException

CommonObject = Union[bool, bytes, int, str, 'Address', Dict[str, BaseObject]]
CommonType = Type[CommonObject]


def base_object_to_str(value: Any) -> str:
    if isinstance(value, Address):
        return str(value)
    elif isinstance(value, int):
        return hex(value)
    elif isinstance(value, bytes):
        return bytes_to_hex(value)
    elif isinstance(value, bool):
        return "0x1" if value else "0x0"
    elif isinstance(value, str):
        return value

    raise TypeError(f"Unsupported type: {type(value)}")


def object_to_str(value: Any) -> Union[List, Dict, CommonObject]:
    if is_base_type(type(value)):
        return base_object_to_str(value)

    if isinstance(value, list):
        return [object_to_str(i) for i in value]

    if isinstance(value, dict):
        return {k: object_to_str(value[k]) for k in value}

    raise TypeError(f"Unsupported type: {type(value)}")


def str_to_base_object_by_type_name(type_name: str, value: str) -> BaseObject:
    return str_to_base_object(value, name_to_type(type_name))


def str_to_int(value: str) -> int:
    if isinstance(value, int):
        return value

    base = 16 if is_hex(value) else 10
    return int(value, base)


def str_to_base_object(value: str, type_hint: type) -> BaseObject:
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

    raise TypeError(f"Unknown type: {type_hint}")


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
    verify_arguments(params, sig)

    converted_params = {}

    for k, v in params.items():
        if not isinstance(k, str):
            raise InvalidParamsException(f"Invalid key type: key={k}")

        try:
            parameter: Parameter = sig.parameters[k]
            converted_params[k] = str_to_object(v, parameter.annotation)
        except KeyError:
            if not (options & ConvertOption.IGNORE_UNKNOWN_PARAMS):
                raise InvalidParamsException(f"Unknown param: key={k} value={v}")

    return converted_params


def verify_arguments(params: Dict[str, Any], sig: Signature):
    for k in sig.parameters:
        if k in ("self", "cls"):
            continue

        parameter: Parameter = sig.parameters[k]
        if parameter.default == Parameter.empty and k not in params:
            raise InvalidParamsException(f"Parameter not found: {k}")


def str_to_object(value: Union[str, list, dict], type_hint: type) -> Any:
    if type(value) not in (str, list, dict):
        raise InvalidParamsException(f"Invalid value type: {value}")

    origin = get_origin(type_hint)

    if is_base_type(origin):
        return str_to_base_object(value, origin)

    if is_struct(origin):
        annotations = get_annotations(origin, None)
        return {k: str_to_object(v, annotations[k]) for k, v in value.items()}

    args = get_args(type_hint)

    if origin is list:
        return [str_to_object(i, args[0]) for i in value]

    if origin is dict:
        type_hint = args[1]
        return {k: str_to_object(v, type_hint) for k, v in value.items()}

    raise InvalidParamsException(f"Failed to convert: value={value} type={type_hint}")
