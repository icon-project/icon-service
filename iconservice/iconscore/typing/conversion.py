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

from typing import Optional, Dict, Union, Type, List, ForwardRef, Any

from iconservice.base.address import Address
from iconservice.base.exception import InvalidParamsException

BaseObject = Union[bool, bytes, int, str, 'Address']
BaseObjectType = Type[BaseObject]
CommonObject = Union[bool, bytes, int, str, 'Address', Dict[str, BaseObject]]
CommonType = Type[CommonObject]

BASE_TYPES = {bool, bytes, int, str, Address}
TYPE_NAME_TO_TYPE = {
    "bool": bool,
    "bytes": bytes,
    "int": int,
    "str": str,
    "Address": Address,
}


def is_base_type(value: type) -> bool:
    try:
        return value in BASE_TYPES
    except:
        return False


def type_name_to_type(type_name: str) -> BaseObjectType:
    return TYPE_NAME_TO_TYPE[type_name]


def str_to_int(value: str) -> int:
    if isinstance(value, int):
        return value

    base = 16 if is_hex(value) else 10
    return int(value, base)


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
    try:
        return base_object_to_str(value)
    except TypeError:
        pass

    if isinstance(value, list):
        return object_to_str_in_list(value)
    elif isinstance(value, dict):
        return object_to_str_in_dict(value)

    raise TypeError(f"Unsupported type: {type(value)}")


def str_to_base_object_by_type_name(type_name: str, value: str) -> BaseObject:
    return str_to_base_object(type_name_to_type(type_name), value)


def str_to_base_object(type_hint: BaseObjectType, value: str) -> BaseObject:
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


def str_to_object(type_hint, value):
    if isinstance(value, dict):
        return str_to_object_in_typed_dict(type_hint, value)
    else:
        return str_to_base_object(type_hint, value)


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


def str_to_object_in_typed_dict(type_hints, value: Dict[str, str]) -> Dict[str, BaseObject]:
    annotations = type_hints.__annotations__
    return {k: str_to_base_object(annotations[k], value[k]) for k in annotations}


def object_to_str_in_dict(value: Dict[str, BaseObject]) -> Dict[str, str]:
    return {k: object_to_str(value[k]) for k in value}


def str_to_object_in_list(type_hint, value: List[Any]) -> List[CommonObject]:
    assert len(type_hint.__args__) == 1

    args_type_hint = type_hint.__args__[0]
    return [str_to_object(args_type_hint, i) for i in value]


def object_to_str_in_list(value: List[CommonObject]) -> List[Union[str, Dict[str, str]]]:
    """Return a copied list from a given list

    All items in the origin list are copied to a copied list and converted in string format
    There is no change in a given list
    """
    return [object_to_str(i) for i in value]


def type_hint_to_type_template(type_hint) -> Any:
    """Convert type_hint to type_template consisting of base_object_types, list and dict

    :param type_hint:
    :return:
    """
    if isinstance(type_hint, ForwardRef):
        type_hint = type_name_to_type(type_hint.__forward_arg__)
    elif isinstance(type_hint, str):
        type_hint = type_name_to_type(type_hint)

    if is_base_type(type_hint):
        return type_hint

    if type_hint is List:
        raise InvalidParamsException(f"No arguments: {type_hint}")

    # If type_hint is a subclass of TypedDict
    attr = "__annotations__"
    if hasattr(type_hint, attr):
        # annotations is a dictionary containing filed_name(str) as a key and type as a value
        annotations = getattr(type_hint, attr)
        return {k: type_hint_to_type_template(v) for k, v in annotations.items()}

    try:
        origin = getattr(type_hint, "__origin__")
        if origin is list:
            args = getattr(type_hint, "__args__")
            return [type_hint_to_type_template(args[0])]
    except:
        pass

    raise InvalidParamsException(f"Unsupported type: {type_hint}")
