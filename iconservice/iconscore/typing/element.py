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

import inspect
from collections import OrderedDict
from collections.abc import MutableMapping
from inspect import (
    isfunction,
    getmembers,
    signature,
    Signature,
    Parameter,
)
from typing import Union, Mapping, List, Dict, Optional, Tuple

from . import (
    is_base_type,
    is_struct,
    get_origin,
    get_args,
    name_to_type,
)
from ..icon_score_constant import (
    CONST_SCORE_FLAG,
    ScoreFlag,
    CONST_INDEXED_ARGS_COUNT,
    CONST_CLASS_ELEMENT_METADATAS,
)
from ... import utils
from ...base.exception import (
    IllegalFormatException,
    InternalServiceErrorException,
    MethodNotFoundException,
    InvalidParamsException,
)


def normalize_signature(func: callable) -> Signature:
    """Normalize signature of score methods

    1. Normalize type hint: ex) no type hint -> str
    2. Remove "self" parameter

    :param func: function attribute from class
    :return:
    """
    sig = inspect.signature(func)
    params = sig.parameters
    new_params = []

    normalized = False

    # CAUTION:
    # def A:
    #     def func(self):
    #         pass
    #
    # inspect.isfunction(A.func) == True
    # inspect.isfunction(A().func) == False
    # inspect.ismethod(A.func) == False
    # inspect.isfunction(A().func) == True
    is_regular_method: bool = inspect.isfunction(func)

    for i, k in enumerate(params):
        # Remove "self" parameter from signature of regular method
        if i == 0 and k == "self" and is_regular_method:
            new_param = None
        else:
            new_param = normalize_parameter(params[k])
            new_params.append(new_param)

        if new_param is not params[k]:
            normalized = True

    return_annotation = normalize_return_annotation(sig.return_annotation)
    if return_annotation is not sig.return_annotation:
        normalized = True

    if normalized:
        sig = sig.replace(parameters=new_params, return_annotation=return_annotation)

    return sig


def normalize_parameter(param: Parameter) -> Parameter:
    annotation = param.annotation

    if annotation == Parameter.empty:
        type_hint = str
    else:
        type_hint = normalize_type_hint(annotation)

    if type_hint == annotation:
        # Nothing to update
        return param

    return param.replace(annotation=type_hint)


def normalize_return_annotation(return_annotation: type) -> Union[type, Signature.empty]:
    if return_annotation in (None, Signature.empty):
        return Signature.empty

    return return_annotation


def normalize_type_hint(type_hint) -> type:
    # If type hint is str, convert it to type hint
    if isinstance(type_hint, str):
        type_hint = name_to_type(type_hint)

    origin = get_origin(type_hint)

    if is_base_type(origin) or is_struct(origin):
        return type_hint

    args = get_args(type_hint)
    size = len(args)

    if origin is list:
        if size == 1:
            return List[normalize_type_hint(args[0])]
    elif origin is dict:
        if size == 2 and args[0] is str:
            return Dict[str, normalize_type_hint(args[1])]
    elif origin is Union:
        if size == 2 and type(None) in args:
            arg = args[0] if args[1] is type(None) else args[1]
            if arg is not None and arg:
                return Union[normalize_type_hint(arg), None]

    raise IllegalFormatException(f"Unsupported type hint: {type_hint}")


def verify_score_flag(flag: ScoreFlag):
    """Check if score flag combination is valid

    If the flag combination is not valid, raise an exception
    """
    valid = {
        ScoreFlag.EXTERNAL,
        ScoreFlag.EXTERNAL | ScoreFlag.PAYABLE,
        ScoreFlag.EXTERNAL | ScoreFlag.READONLY,
        ScoreFlag.FALLBACK | ScoreFlag.PAYABLE,
        ScoreFlag.EVENTLOG,
        ScoreFlag.INTERFACE,
    }

    if flag not in valid:
        raise IllegalFormatException(f"Invalid score decorator: {flag}")


class ScoreElementMetadata(object):
    def __init__(self, element: callable):
        self._signature: Signature = normalize_signature(element)
        self._element = element

    @property
    def element(self) -> callable:
        return self._element

    @property
    def name(self) -> str:
        return self._element.__name__

    @property
    def flag(self) -> ScoreFlag:
        return get_score_flag(self._element)

    @property
    def signature(self) -> Signature:
        return self._signature


class FunctionMetadata(ScoreElementMetadata):
    """Represents metadata of an exposed function in a SCORE

    """
    def __init__(self, func: callable):
        super().__init__(func)
        self._verify()

    @property
    def is_external(self) -> bool:
        return bool(self.flag & ScoreFlag.EXTERNAL)

    @property
    def is_payable(self) -> bool:
        return bool(self.flag & ScoreFlag.PAYABLE)

    @property
    def is_readonly(self) -> bool:
        return bool(self.flag & ScoreFlag.READONLY)

    @property
    def is_fallback(self) -> bool:
        return utils.is_all_flag_on(
            self.flag, ScoreFlag.FALLBACK | ScoreFlag.PAYABLE)

    def _verify(self):
        if self.is_fallback:
            self._verify_fallback_signature()

    def _verify_fallback_signature(self):
        """Verify if the signature of fallback() is valid

        fallback function must have no parameters
        """
        sig = self.signature

        if not (
                len(sig.parameters) == 0
                and sig.return_annotation in (None, Signature.empty)
        ):
            raise IllegalFormatException("Invalid fallback signature")


class EventLogMetadata(ScoreElementMetadata):
    """Represents metadata of an eventlog declared in a SCORE
    """

    def __init__(self, eventlog: callable):
        super().__init__(eventlog)

    @property
    def indexed_args_count(self) -> int:
        return getattr(self.element, CONST_INDEXED_ARGS_COUNT, 0)


class ScoreElementMetadataContainer(MutableMapping):
    """Container which has score elements like function and eventlog
    """

    def __init__(self):
        self._elements = OrderedDict()
        self._externals = 0
        self._eventlogs = 0
        self._readonly = False

    @property
    def externals(self) -> int:
        return self._externals

    @property
    def eventlogs(self) -> int:
        return self._eventlogs

    def __getitem__(self, k: str) -> ScoreElementMetadata:
        return self._elements[k]

    def __setitem__(self, k: str, v: ScoreElementMetadata) -> None:
        self._check_writable()
        self._elements[k] = v

        if isinstance(v, FunctionMetadata):
            self._externals += 1
        elif isinstance(v, EventLogMetadata):
            self._eventlogs += 1
        else:
            raise InternalServiceErrorException(f"Invalid element: {v}")

    def __iter__(self):
        for k in self._elements:
            yield k

    def __len__(self) -> int:
        return len(self._elements)

    def __delitem__(self, k: str) -> None:
        self._check_writable()

        element = self._elements[k]
        del self._elements[k]

        if is_any_score_flag_on(element, ScoreFlag.EVENTLOG):
            self._eventlogs -= 1
        else:
            self._externals -= 1

    def _check_writable(self):
        if self._readonly:
            raise InternalServiceErrorException(f"{self.__class__.__name__} not writable")

    def freeze(self):
        self._readonly = True


def create_score_element_metadatas(cls: type) -> Mapping:
    elements = ScoreElementMetadataContainer()

    for name, func in getmembers(cls, predicate=isfunction):
        if name.startswith("__"):
            continue

        # Collect the only functions with one or more of the above 4 score flags
        flag = get_score_flag(func)

        if utils.is_any_flag_on(flag, ScoreFlag.FUNC | ScoreFlag.EVENTLOG):
            verify_score_flag(flag)
            elements[name] = create_score_element_metadata(func)

    elements.freeze()
    return elements


def create_score_element_metadata(element: callable) -> Union[FunctionMetadata, EventLogMetadata]:
    flags = get_score_flag(element)

    if flags & ScoreFlag.EVENTLOG:
        return EventLogMetadata(element)
    else:
        return FunctionMetadata(element)


def get_score_flag(obj: callable, default: ScoreFlag = ScoreFlag.NONE) -> ScoreFlag:
    return getattr(obj, CONST_SCORE_FLAG, default)


def set_score_flag(obj: callable, flag: ScoreFlag) -> ScoreFlag:
    setattr(obj, CONST_SCORE_FLAG, flag)
    return flag


def set_score_flag_on(obj: callable, flag: ScoreFlag) -> ScoreFlag:
    flag |= get_score_flag(obj)
    set_score_flag(obj, flag)
    return flag


def is_all_score_flag_on(obj: callable, flag: ScoreFlag) -> bool:
    return utils.is_all_flag_on(get_score_flag(obj), flag)


def is_any_score_flag_on(obj: callable, flag: ScoreFlag) -> bool:
    return utils.is_any_flag_on(get_score_flag(obj), flag)


def get_score_element(score, func_name: str) -> ScoreElementMetadata:
    try:
        elements = getattr(score, CONST_CLASS_ELEMENT_METADATAS)
        return elements[func_name]
    except KeyError:
        raise MethodNotFoundException(
            f"Method not found: {type(score).__name__}.{func_name}")


def verify_internal_call_arguments(score, func_name: str, args: Optional[Tuple], kwargs: Optional[Dict]):
    element = get_score_element(score, func_name)
    sig = element.signature
    sig = inspect.signature(getattr(score, func_name))

    try:
        arguments = sig.bind(*args, **kwargs)
    except TypeError:
        raise InvalidParamsException(
            f"Invalid internal call params: address={score.address} func={func_name}")
