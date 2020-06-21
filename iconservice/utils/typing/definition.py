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

from typing import List, Dict

from .conversion import is_base_type
from ...base.exception import IllegalFormatException


def get_type_name(type_template: type):
    if is_base_type(type(type_template)):
        return type_template.__name__

    if isinstance(type_template, list):
        item = type_template[0]
        name = "struct" if isinstance(item, dict) else item.__name__
        return f"[]{name}"

    if isinstance(type_template, dict):
        return "struct"


def get_fields(type_template: type) -> List[Dict[str, str]]:
    if isinstance(type_template, list):
        item = type_template[0]
    elif isinstance(type_template, dict):
        item = type_template
    else:
        raise IllegalFormatException(f"Invalid type: {type(type_template)}")

    return [{"name": k, "type": item[k].__name__} for k in item]
