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

from secp256k1 import PublicKey, FLAG_VERIFY


class IconScoreDeploySignVerifier:
    def __init__(self, data, raw=True):
        """
        Refer to https://github.com/ludbb/secp256k1-py api documents.
        :param data: 65 bytes data which PublicKey.serialize() returns.
        :param raw: if False, it is assumed that pubkey has gone through PublicKey.deserialize already, otherwise it must be specified as bytes.
        """
        self.__pubkey = PublicKey(data, raw, FLAG_VERIFY)

    def verify(self, msg_hash: bytes, signature: bytes) -> bool:
        """Verify signature.

        :param msg_hash: Hash value of msg
        :param signature: signature data
        :return:
        """
        pubkey = self.__pubkey

        signature = pubkey.ecdsa_deserialize(signature)
        return pubkey.ecdsa_verify(msg_hash, signature, True)

    @classmethod
    def from_bytes(cls, data: bytes):
        """
        :param data: bytes data which PublicKey.serialize() returns
        :return:
        """
        return cls(data, True)
