#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Copyright 2017-2018 theloop Inc.
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

import base64
from secp256k1 import PrivateKey, PublicKey, FLAG_VERIFY


class ScoreInstallSigner(object):
    """Sign when score installed.

    """
    def __init__(self, data=None, raw=True):
        self.__private_key = PrivateKey(data, raw)

    @property
    def public_key(self):
        return self.__private_key.pubkey.serialize(compressed=False)

    def sign_recoverable(self, tx_hash: 'bytes'):
        recoverable_signature = self.__private_key.ecdsa_sign_recoverable(tx_hash, raw=True)
        return self.__private_key.ecdsa_recoverable_serialize(recoverable_signature)

    def sign(self, tx_hash: 'bytes'):
        signature = self.__private_key.ecdsa_sign(tx_hash, raw=True)
        return self.__private_key.ecdsa_serialize(signature)

    def sign_install_score(self, tx_hash: 'bytes'):
        recoverable_sig_bytes = self.sign_recoverable_install_score(tx_hash)
        return base64.b64encode(recoverable_sig_bytes)

    def sign_recoverable_install_score(self, tx_hash: 'bytes'):
        signature, recovery_id = self.sign_recoverable(tx_hash)

        return bytes(bytearray(signature) + recovery_id.to_bytes(1, 'big'))
