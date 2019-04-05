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

from typing import Tuple, Any
from ..base.msgpack_util import TypeTag, MsgPackConverter, Codec
from ..base.address import AddressPrefix, Address
from ..base.exception import InvalidParamsException
from ..utils import int_to_bytes


def address_to_bytes(addr: 'Address') -> bytes:
    prefix_byte = b''
    addr_bytes = addr.to_bytes()
    if addr.prefix == AddressPrefix.EOA:
        prefix_byte = int_to_bytes(addr.prefix.value)
    return prefix_byte + addr_bytes


def bytes_to_address(data: bytes) -> 'Address':
    prefix = AddressPrefix(data[0])
    return Address(prefix, data[1:])


class IissCodec(Codec):
    def encode(self, obj) -> Tuple[int, bytes]:
        if isinstance(obj, Address):
            return TypeTag.ADDRESS, address_to_bytes(obj)
        raise InvalidParamsException(f"Invalid encode type: {type(obj)}")

    def decode(self, t: int, b: bytes) -> Any:
        if t == TypeTag.ADDRESS:
            return bytes_to_address(b)
        else:
            raise InvalidParamsException(f"UnknownType: {type(t)}")


class IissDataConverter(MsgPackConverter):
    codec: 'Codec' = IissCodec()
