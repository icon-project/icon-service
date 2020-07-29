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

__all__ = "get_score_api"

from inspect import Signature, Parameter
from typing import List, Dict, Mapping, Iterable, Any, Union

from . import get_origin, get_args, is_struct
from .conversion import is_base_type
from .element import (
    ScoreElementMetadata,
    FunctionMetadata,
    EventLogMetadata,
    ScoreFlag,
)
from ..icon_score_constant import STR_FALLBACK
from ...base.exception import (
    IllegalFormatException,
    InvalidParamsException,
    InternalServiceErrorException,
)

"""Utils to support icx_getScoreApi method
"""


def get_score_api(elements: Iterable[ScoreElementMetadata]) -> List:
    """Returns score api used in icx_getScoreApi JSON-RPC method

    :param elements:
    :return:
    """

    api = []

    for element in elements:
        if isinstance(element, FunctionMetadata):
            func: FunctionMetadata = element
            if func.flag == ScoreFlag.PAYABLE:
                continue

            item = _get_function(func.name, func.signature, func.is_readonly, func.is_payable)
        elif isinstance(element, EventLogMetadata):
            eventlog: EventLogMetadata = element
            item = _get_eventlog(eventlog.name, eventlog.signature, eventlog.indexed_args_count)
        else:
            raise InternalServiceErrorException(f"Invalid score element: {element} {type(element)}")

        api.append(item)

    return api


def _get_function(func_name: str, sig: Signature, is_readonly: bool, is_payable: bool) -> Dict:
    if _is_fallback(func_name, sig, is_payable):
        return _get_fallback_function()
    else:
        return _get_normal_function(func_name, sig, is_readonly, is_payable)


def _get_normal_function(func_name: str, sig: Signature, is_readonly: bool, is_payable: bool) -> Dict:
    ret = {
        "name": func_name,
        "type": "function",
        "inputs": _get_inputs(sig.parameters),
        "outputs": _get_outputs(sig.return_annotation)
    }

    if is_readonly:
        ret["readonly"] = True

    if is_payable:
        ret["payable"] = True

    return ret


def _is_fallback(func_name: str, sig: Signature, is_payable: bool) -> bool:
    ret: bool = func_name == STR_FALLBACK and is_payable
    if ret:
        if len(sig.parameters) > 1:
            raise InvalidParamsException("Invalid fallback signature")

        return_annotation = sig.return_annotation
        if return_annotation not in (None, Signature.empty):
            raise InvalidParamsException("Invalid fallback signature")

    return ret


def _get_fallback_function() -> Dict:
    return {
        "name": STR_FALLBACK,
        "type": STR_FALLBACK,
        "payable": True,
    }


def _get_inputs(params: Mapping[str, Parameter]) -> list:
    inputs = []

    for name, param in params.items():
        annotation = param.annotation
        type_hint = str if annotation is Parameter.empty else annotation

        inputs.append(_get_input(name, type_hint, param.default))

    return inputs


def _get_input(name: str, type_hint: type, default: Any) -> Dict:
    inp = {"name": name}

    # Add default parameter value to score api
    if default is not Parameter.empty:
        if default is not None and not isinstance(default, type_hint):
            raise InvalidParamsException(
                f"Default params type mismatch. value: {default} type: {type_hint}")

        inp["default"] = default

    type_hints: List[type] = _split_type_hint(type_hint)
    inp["type"] = _type_hints_to_name(type_hints)

    last_type_hint: type = type_hints[-1]

    if is_struct(last_type_hint):
        inp["fields"] = _get_fields(last_type_hint)

    return inp


def _split_type_hint(type_hint: type) -> List[type]:
    type_hints = [type_hint]
    ret = []

    while len(type_hints) > 0:
        type_hint = type_hints.pop(0)
        origin: type = get_origin(type_hint)
        ret.append(origin)

        if origin is list:
            args = get_args(type_hint)
            if len(args) != 1:
                raise IllegalFormatException(f"Invalid type: {type_hint}")

            type_hints.append(args[0])
        elif origin is Union:
            args = get_args(type_hint)
            if not (len(args) == 2 and args[1] is type(None)):
                raise IllegalFormatException(f"Invalid type: {type_hint}")

            type_hints.append(args[0])

    return ret


def _type_hints_to_name(type_hints: List[type]) -> str:
    def func():
        for _type in type_hints:
            if _type is Union:
                continue

            if _type is list:
                yield "[]"
            elif is_base_type(_type):
                yield _type.__name__
            elif is_struct(_type):
                yield "struct"

    return "".join(func())


def _type_hint_to_name(type_hint: type) -> str:
    if is_base_type(type_hint):
        return type_hint.__name__
    elif is_struct(type_hint):
        return "struct"

    raise IllegalFormatException(f"Invalid type: {type_hint}")


def _get_fields(struct: type) -> List[dict]:
    """Returns fields info from struct

    :param struct: struct type
    :return:
    """
    # annotations is a dictionary containing key-type pair
    # which has field_name as a key and type as a value
    annotations = struct.__annotations__

    fields = []
    for name, type_hint in annotations.items():
        field = {"name": name}

        type_hints: List[type] = _split_type_hint(type_hint)
        field["type"] = _type_hints_to_name(type_hints)

        last_type_hint: type = type_hints[-1]
        if is_struct(last_type_hint):
            field["fields"] = _get_fields(last_type_hint)

        fields.append(field)

    return fields


def _get_outputs(type_hint: type) -> List:
    origin = get_origin(type_hint)

    if is_base_type(origin):
        type_name = origin.__name__
    elif is_struct(origin) or origin is dict:
        type_name = "{}"
    elif origin is list:
        type_name = "[]"
    else:
        return []

    return [{"type": type_name}]


def _get_eventlog(func_name: str, sig: Signature, indexed_args_count: int) -> Dict:
    params = sig.parameters

    inputs = []
    for name, param in params.items():
        annotation = param.annotation
        type_hint = str if annotation is Parameter.empty else annotation
        inp: Dict = _get_input(name, type_hint, param.default)
        if len(inputs) < indexed_args_count:
            inp["indexed"] = True

        inputs.append(inp)

    return {
        "name": func_name,
        "type": "eventlog",
        "inputs": inputs
    }
