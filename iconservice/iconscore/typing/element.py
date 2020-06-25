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

from collections.abc import MutableMapping
from inspect import (
    isfunction,
    getmembers,
    signature,
    Signature,
    Parameter,
)
from typing import Union, Mapping

from .type_hint import normalize_type_hint
from ..icon_score_constant import (
    CONST_SCORE_FLAG,
    ScoreFlag,
    STR_FALLBACK,
    CONST_INDEXED_ARGS_COUNT,
)
from ...base.exception import IllegalFormatException, InternalServiceErrorException


def normalize_signature(sig: Signature) -> Signature:
    params = sig.parameters
    new_params = []

    normalized = False
    for k in params:
        new_param = normalize_parameter(params[k])
        new_params.append(new_param)

        if params[k] != new_params:
            normalized = True

    if normalized:
        sig = sig.replace(parameters=new_params)

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


def verify_score_flag(func: callable):
    """Check if score flag combination is valid

    If the combination is not valid, raise an exception
    """
    flag: ScoreFlag = get_score_flag(func)

    if flag & ScoreFlag.READONLY:
        # READONLY cannot be combined with PAYABLE
        if flag & ScoreFlag.PAYABLE:
            raise IllegalFormatException(f"Payable method cannot be readonly")
        # READONLY cannot be set alone without EXTERNAL
        elif not (flag & ScoreFlag.EXTERNAL):
            raise IllegalFormatException(f"Invalid score flag: {flag}")

    # EVENTLOG cannot be combined with other flags
    if flag & ScoreFlag.EVENTLOG and flag != ScoreFlag.EVENTLOG:
        raise IllegalFormatException(f"Invalid score flag: {flag}")

    # INTERFACE cannot be combined with other flags
    if flag & ScoreFlag.INTERFACE and flag != ScoreFlag.INTERFACE:
        raise IllegalFormatException(f"Invalid score flag: {flag}")


class ScoreElement(object):
    def __init__(self, element: callable):
        verify_score_flag(element)
        self._element = element
        self._signature: Signature = normalize_signature(signature(element))

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


class Function(ScoreElement):
    def __init__(self, func: callable):
        super().__init__(func)

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
        return self.name == STR_FALLBACK and self.is_payable


class EventLog(ScoreElement):
    def __init__(self, eventlog: callable):
        super().__init__(eventlog)

    @property
    def indexed_args_count(self) -> int:
        return getattr(self.element, CONST_INDEXED_ARGS_COUNT, 0)


class ScoreElementContainer(MutableMapping):
    def __init__(self):
        self._elements = {}
        self._externals = 0
        self._eventlogs = 0
        self._readonly = False

    @property
    def externals(self) -> int:
        return self._externals

    @property
    def eventlogs(self) -> int:
        return self._eventlogs

    def __getitem__(self, k: str) -> ScoreElement:
        return self._elements[k]

    def __setitem__(self, k: str, v: ScoreElement) -> None:
        self._check_writable()
        self._elements[k] = v

        if isinstance(v, Function):
            self._externals += 1
        elif isinstance(v, EventLog):
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
            raise InternalServiceErrorException("ScoreElementContainer not writable")

    def freeze(self):
        self._readonly = True


def create_score_elements(cls) -> Mapping:
    elements = ScoreElementContainer()
    flags = (
            ScoreFlag.READONLY |
            ScoreFlag.EXTERNAL |
            ScoreFlag.PAYABLE |
            ScoreFlag.EVENTLOG
    )

    for name, func in getmembers(cls, predicate=isfunction):
        if name.startswith("__"):
            continue

        # Collect the only functions with one or more of the above 4 score flags
        if is_any_score_flag_on(func, flags):
            elements[name] = create_score_element(func)

    elements.freeze()
    return elements


def create_score_element(element: callable) -> Union[Function, EventLog]:
    flags = get_score_flag(element)

    if flags & ScoreFlag.EVENTLOG:
        return EventLog(element)
    else:
        return Function(element)


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
    return (get_score_flag(obj) & flag) == flag


def is_any_score_flag_on(obj: callable, flag: ScoreFlag) -> bool:
    return bool(get_score_flag(obj) & flag)
