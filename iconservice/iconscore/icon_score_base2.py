# -*- coding: utf-8 -*-

# Copyright 2018 ICON Foundation
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

import hashlib
import json
from abc import ABC, ABCMeta
from typing import TYPE_CHECKING, Optional, Union, Any

from secp256k1 import PublicKey, ALL_FLAGS, NO_FLAGS

from ..base.address import Address, AddressPrefix
from ..base.exception import RevertException, ExceptionCode, IconScoreException
from ..iconscore.icon_score_context import ContextContainer
from ..iconscore.icon_score_step import StepType

if TYPE_CHECKING:
    from .icon_score_base import IconScoreBase

"""
The explanation below are extracted
from https://github.com/bitcoin-core/secp256k1/blob/master/include/secp256k1.h

Opaque data structure that holds context information (precomputed tables etc.).

The purpose of context structures is to cache large precomputed data tables
that are expensive to construct, and also to maintain the randomization data for blinding.

Do not create a new context object for each operation, as construction is
far slower than all other API calls (~100 times slower than an ECDSA verification).

A constructed context can safely be used from multiple threads
simultaneously, but API call that take a non-const pointer to a context
need exclusive access to it. In particular this is the case for
secp256k1_context_destroy and secp256k1_context_randomize.

Regarding randomization, either do it once at creation time (in which case
you do not need any locking for the other calls), or use a read-write lock.
"""
_public_key = PublicKey(flags=ALL_FLAGS)


class InterfaceScoreMeta(ABCMeta):
    def __new__(mcs, name, bases, namespace, **kwargs):
        if ABC in bases:
            return super().__new__(mcs, name, bases, namespace, **kwargs)

        cls = super().__new__(mcs, name, bases, namespace, **kwargs)
        return cls


class InterfaceScore(ABC, metaclass=InterfaceScoreMeta):
    def __init__(self, addr_to: 'Address', from_score: 'IconScoreBase'):
        self.__addr_to = addr_to
        self.__from_score = from_score

    @property
    def addr_to(self) -> 'Address':
        return self.__addr_to

    @property
    def from_score(self) -> 'IconScoreBase':
        return self.__from_score


class Block(object):
    def __init__(self, block_height: int, timestamp: int) -> None:
        """Constructor

        :param block_height: block height
        :param timestamp: block timestamp
        """
        self._height = block_height
        # unit: microsecond
        self._timestamp = timestamp

    @property
    def height(self) -> int:
        return self._height

    @property
    def timestamp(self) -> int:
        return self._timestamp


def revert(message: Optional[str] = None,
           code: Union[ExceptionCode, int] = ExceptionCode.SCORE_ERROR) -> None:
    """
    Reverts the transaction and breaks.
    All the changes of state DB in current transaction will be rolled back.

    :param message: revert message
    :param code: code
    """
    try:
        if not isinstance(code, (int, ExceptionCode)):
            code = int(code)

        if not isinstance(message, str):
            message = str(message)
    except:
        raise IconScoreException(
            message=f"Revert error: code or message is invalid",
            code=ExceptionCode.SCORE_ERROR)
    else:
        raise RevertException(message, code)


def sha3_256(data: bytes) -> bytes:
    """
    Computes hash using the input data

    :param data: input data
    :return: hashed data in bytes
    """
    context = ContextContainer._get_context()
    if context.step_counter:
        step_count = 1
        if data:
            step_count += len(data)
        context.step_counter.apply_step(StepType.API_CALL, step_count)

    return hashlib.sha3_256(data).digest()


def json_dumps(obj: Any, **kwargs) -> str:
    """
    Converts a python object `obj` to a JSON string

    :param obj: a python object to be converted
    :param kwargs: json options (see https://docs.python.org/3/library/json.html#json.dumps)
    :return: json string
    """
    return json.dumps(obj, **kwargs)


def json_loads(src: str, **kwargs) -> Any:
    """
    Parses a JSON string `src` and converts it to a python object

    :param src: a JSON string to be converted
    :param kwargs: kwargs: json options (see https://docs.python.org/3/library/json.html#json.loads)
    :return: a python object
    """
    return json.loads(src, **kwargs)


def create_address_with_key(public_key: bytes) -> Optional['Address']:
    """Create an address with a given public key

    :param public_key: Public key based on secp256k1
    :return: Address created from a given public key or None if failed
    """
    # FIXME: Add step calculation code
    try:
        return _create_address_with_key(public_key)
    except:
        return None


def _create_address_with_key(public_key: bytes) -> Optional['Address']:
    if isinstance(public_key, bytes):
        size = len(public_key)
        prefix: bytes = public_key[0]

        if size == 33 and prefix in (0x02, 0x03):
            uncompressed_public_key: bytes = _convert_key(public_key)
        elif size == 65 and prefix == 0x04:
            uncompressed_public_key: bytes = public_key
        else:
            return None

        body: bytes = hashlib.sha3_256(uncompressed_public_key[1:]).digest()[-20:]
        return Address(AddressPrefix.EOA, body)

    return None


def _convert_key(public_key: bytes) -> Optional[bytes]:
    """Convert key between compressed and uncompressed keys

    :param public_key: compressed or uncompressed key
    :return: the counterpart key of a given public_key
    """
    size = len(public_key)
    if size == 33:
        compressed = True
    elif size == 65:
        compressed = False
    else:
        return None

    public_key = PublicKey(public_key, raw=True, flags=NO_FLAGS, ctx=_public_key.ctx)
    return public_key.serialize(compressed=not compressed)


def recover_key(msg_hash: bytes, signature: bytes, compressed: bool = True) -> Optional[bytes]:
    """Returns the public key from message hash and recoverable signature

    :param msg_hash: 32 bytes data
    :param signature: signature_data(64) + recovery_id(1)
    :param compressed: the type of public key to return
    :return: public key recovered from msg_hash and signature
        (compressed: 33 bytes key, uncompressed: 65 bytes key)
    """
    # FIXME: Add step calculation code
    try:
        return _recover_key(msg_hash, signature, compressed)
    except:
        return None


def _recover_key(msg_hash: bytes, signature: bytes, compressed: bool) -> Optional[bytes]:
    if isinstance(msg_hash, bytes) \
            and len(msg_hash) == 32 \
            and isinstance(signature, bytes) \
            and len(signature) == 65:
        internal_recover_sig = _public_key.ecdsa_recoverable_deserialize(
            ser_sig=signature[:64], rec_id=signature[64])
        internal_pubkey = _public_key.ecdsa_recover(
            msg_hash, internal_recover_sig, raw=True, digest=None)

        public_key = PublicKey(internal_pubkey, raw=False, ctx=_public_key.ctx)
        return public_key.serialize(compressed)

    return None
