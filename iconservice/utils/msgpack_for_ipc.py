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
from typing import Tuple, Any, Union

import msgpack

from . import int_to_bytes, bytes_to_int
from ..base.address import Address
from ..base.exception import InvalidParamsException
from ..icon_constant import CHARSET_ENCODING


class TypeTag(IntEnum):
    NIL = 0
    DICT = 1
    LIST = 2
    BYTES = 3
    STRING = 4

    CUSTOM = 10
    INT = CUSTOM + 1
    ADDRESS = CUSTOM


class BaseCodec(object):

    def encode(self, obj: Any) -> Tuple[int, bytes]:
        if isinstance(obj, Address):
            return TypeTag.ADDRESS, obj.to_bytes_including_prefix()
        raise InvalidParamsException(f"Invalid encode type: {type(obj)}")

    def decode(self, t: int, b: bytes) -> Any:
        if t == TypeTag.ADDRESS:
            return Address.from_bytes_including_prefix(b)
        else:
            raise InvalidParamsException(f"UnknownType: {type(t)}")


class MsgPackForIpc(object):
    codec: 'BaseCodec' = BaseCodec()

    @classmethod
    def decode(cls, tag: int, val: bytes) -> 'Any':
        if tag == TypeTag.NIL:
            if val == b'':
                return None
            else:
                raise InvalidParamsException(f"Invalid tag type:{tag} value: {val}")
        if tag == TypeTag.BYTES:
            return val
        elif tag == TypeTag.STRING:
            return val.decode(CHARSET_ENCODING)
        elif tag == TypeTag.INT:
            return bytes_to_int(val)
        else:
            return cls.codec.decode(tag, val)

    @classmethod
    def encode(cls, o: Any) -> bytes:
        if o is None:
            return bytes([])
        if isinstance(o, int):
            return int_to_bytes(o)
        elif isinstance(o, str):
            return o.encode(CHARSET_ENCODING)
        elif isinstance(o, bytes):
            return o
        elif isinstance(o, bool):
            return b'\x01' if o else b'\x00'
        else:
            t, v = cls.codec.encode(o)
            return v

    @classmethod
    def decode_any(cls, to: Tuple) -> Any:
        tag: int = to[0]
        val: Union[bytes, dict, list] = to[1]
        if tag == TypeTag.NIL:
            return None
        elif tag == TypeTag.DICT:
            obj = {}
            for k, v in val.items():
                if isinstance(k, bytes):
                    k = k.decode(CHARSET_ENCODING)
                obj[k] = cls.decode_any(v)
            return obj
        elif tag == TypeTag.LIST:
            obj = []
            for v in val:
                obj.append(cls.decode_any(v))
            return obj
        else:
            return cls.decode(tag, val)

    @classmethod
    def encode_any(cls, o: Any) -> Tuple[int, Any]:
        if o is None:
            return TypeTag.NIL, b''
        elif isinstance(o, dict):
            m = {}
            for k, v in o.items():
                m[k] = cls.encode_any(v)
            return TypeTag.DICT, m
        elif isinstance(o, (list, tuple)):
            lst = []
            for v in o:
                lst.append(cls.encode_any(v))
            return TypeTag.LIST, lst
        elif isinstance(o, bytes):
            return TypeTag.BYTES, o
        elif isinstance(o, str):
            return TypeTag.STRING, o.encode(CHARSET_ENCODING)
        elif isinstance(o, int):
            return TypeTag.INT, int_to_bytes(o)
        else:
            return cls.codec.encode(o)

    @classmethod
    def dumps(cls, data: Any) -> bytes:
        return msgpack.dumps(data, use_bin_type=False)

    @classmethod
    def loads(cls, data: bytes) -> list:
        return msgpack.loads(data, raw=True, strict_map_key=False)
