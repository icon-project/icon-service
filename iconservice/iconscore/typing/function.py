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

from inspect import signature, Signature, Parameter

from iconservice.iconscore.icon_score_constant import (
    CONST_BIT_FLAG,
    ConstBitFlag,
    STR_FALLBACK,
)
from iconservice.iconscore.typing.type_hint import normalize_type_hint


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


class Function(object):
    def __init__(self, func: callable):
        self._func = func
        self._signature: Signature = normalize_signature(signature(func))

    @property
    def name(self) -> str:
        return self._func.__name__

    @property
    def flags(self) -> int:
        return getattr(self._func, CONST_BIT_FLAG, 0)

    @property
    def is_external(self) -> bool:
        return bool(self.flags & ConstBitFlag.External)

    @property
    def is_payable(self) -> bool:
        return bool(self.flags & ConstBitFlag.Payable)

    @property
    def is_fallback(self) -> bool:
        return self.name == STR_FALLBACK and self.is_payable
