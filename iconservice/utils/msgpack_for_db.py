# Copyright 2019 ICON Foundation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from enum import IntEnum
from abc import ABCMeta, abstractmethod
from typing import Any

from msgpack import dumps as msgpack_dumps, loads as msgpack_loads, ExtType as msgpack_extType

from ..base.address import Address, AddressPrefix
from . import int_to_bytes, bytes_to_int


# you should override if you want to parse custom type
# class CustomCodec(Codec):
#     class CustomType(IntEnum):
#         # NONE = 0
#         # BIG_INT = 1
#         # ADDRESS = 2
#
#         CUSTOM = 3
#
#     @classmethod
#     def encode(cls, obj: Any) -> Any:
#         return obj
#
#     @classmethod
#     def decode(cls, t: int, b: bytes) -> Any:
#         return msgpack_extType(t, b)


class Codec(metaclass=ABCMeta):
    @classmethod
    @abstractmethod
    def encode(cls, obj: Any) -> Any:
        pass

    @classmethod
    @abstractmethod
    def decode(cls, t: int, b: bytes) -> Any:
        pass


class MsgPackForDB(object):
    class BaseCodec(Codec):
        @classmethod
        def encode(cls, obj: Any) -> Any:
            return obj

        @classmethod
        def decode(cls, t: int, b: bytes) -> Any:
            return msgpack_extType(t, b)

    # you should assign CustomCodec if you want to parse custom type
    _codec: 'Codec' = BaseCodec()

    class BaseType(IntEnum):
        NONE = 0
        BIG_INT = 1
        ADDRESS = 2

    @classmethod
    def _address_to_bytes(cls, addr: 'Address') -> bytes:
        prefix_byte = b''
        addr_bytes = addr.to_bytes()
        if addr.prefix == AddressPrefix.EOA:
            prefix_byte = int_to_bytes(addr.prefix.value)
        return prefix_byte + addr_bytes

    @classmethod
    def _bytes_to_address(cls, data: bytes) -> 'Address':
        prefix = AddressPrefix(data[0])
        return Address(prefix, data[1:])

    @classmethod
    def _encode(cls, obj: Any) -> Any:
        if isinstance(obj, int):
            return msgpack_extType(cls.BaseType.BIG_INT, int_to_bytes(obj))
        elif isinstance(obj, Address):
            return msgpack_extType(cls.BaseType.ADDRESS, cls._address_to_bytes(obj))
        else:
            return cls._codec.encode(obj)

    @classmethod
    def _decode(cls, t: int, b: bytes) -> Any:
        if t == cls.BaseType.BIG_INT:
            return bytes_to_int(b)
        elif t == cls.BaseType.ADDRESS:
            return cls._bytes_to_address(b)
        else:
            return cls._codec.decode(t, b)

    @classmethod
    def dumps(cls, data: Any) -> bytes:
        return msgpack_dumps(data, default=cls._encode, use_bin_type=True, strict_types=True)

    @classmethod
    def loads(cls, data: bytes) -> list:
        return msgpack_loads(data, ext_hook=cls._decode, raw=False)
