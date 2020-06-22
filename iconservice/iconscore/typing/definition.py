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

from typing import List, Dict, Tuple

from iconservice.base.exception import IllegalFormatException
from .conversion import is_base_type
from . import get_origin, get_args


def get_type_name(type_template: type):
    if is_base_type(type(type_template)):
        return type_template.__name__

    if isinstance(type_template, list):
        item = type_template[0]
        name = "struct" if isinstance(item, dict) else item.__name__
        return f"[]{name}"

    if isinstance(type_template, dict):
        return "struct"


def get_type_name_by_type_hint(type_hint: type):
    # If type hint is a base type, just return its name
    # Ex: bool, bytes, int, str, Address
    if is_base_type(type_hint):
        return type_hint.__name__

    origin: type = get_origin(type_hint)
    args: Tuple[type, ...] = get_args(type_hint)

    if isinstance(origin, list):
        name = "struct" if isinstance(args[0], dict) else item.__name__
        return f"[]{name}"

    if isinstance(origin, dict):
        return "struct"


def get_fields(type_template: type) -> List[Dict[str, str]]:
    if isinstance(type_template, list):
        item = type_template[0]
    elif isinstance(type_template, dict):
        item = type_template
    else:
        raise IllegalFormatException(f"Invalid type: {type(type_template)}")

    return [{"name": k, "type": item[k].__name__} for k in item]
