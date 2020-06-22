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


def normalize_type_hint(type_hint) -> type:
    return type_hint

# def _normalize_type_hint():
#     # BaseType
#     if is_base_type(annotation):
#         return param
#
#     # No annotation
#     if annotation is Parameter.empty:
#         return param.replace(annotation=str)
#     if annotation is list:
#         return param.replace(annotation=List[str])
#
#     origin = getattr(annotation, "__origin__", None)
#
#     if origin is list:
#         return param.replace(annotation=List[str])
#
#     raise TypeError(f"Unsupported type hint: {annotation}")


# def normalize_list_type_hint(type_hint) -> type:
#     """
#     1. list -> List[str]
#     2. List -> List[str]
#     3. List[int] -> List[int]
#     4. List[Custom] -> List[Custom]
#     5. List["Custom"] -> exception
#     6. List[Union[str, int]] -> exception
#
#     :param type_hint:
#     :return:
#     """
#     if type_hint is list:
#         return List[str]
#
#     attr = "__args__"
#     if not hasattr(type_hint, attr):
#         return List[str]
#
#     args = getattr(type_hint, "__args__")
#     if len(args) > 1:
#         raise TypeError(f"Unsupported type hint: {type_hint}")
#
#     if is_base_type(args[0]) or issubclass(args[0], TypedDict):
#         return type_hint
#
#     raise TypeError(f"Unsupported type hint: {type_hint}")
