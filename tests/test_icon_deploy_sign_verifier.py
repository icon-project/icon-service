# -*- coding: utf-8 -*-
#
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

import hashlib
import os
import unittest

from iconservice.deploy.icon_score_deploy_sign_verifier import IconScoreDeploySignVerifier
from secp256k1 import PrivateKey

TEST_DIR = os.path.abspath(os.path.dirname(__file__))


class TmpSigner:

    def __init__(self, data=None, raw=True):
        self._private_key = PrivateKey(data, raw)

    def sign(self, msg_hash):
        signature = self._private_key.ecdsa_sign(msg_hash, raw=True)
        return self._private_key.ecdsa_serialize(signature)

    @property
    def public_key(self):
        return self._private_key.pubkey.serialize(compressed=False)


def read_zipfile_as_byte(archive_path: str) -> bytes:
    with open(archive_path, 'rb') as f:
        byte_data = f.read()
        return byte_data


class TestIconDeploySignVerifier(unittest.TestCase):

    def setUp(self):
        self.tmp_signer = TmpSigner()

        self.verifier = IconScoreDeploySignVerifier(self.tmp_signer.public_key)

    def test_verify(self):
        testzip_bytes = read_zipfile_as_byte(os.path.join(TEST_DIR, "test.zip"))
        zip_hash = hashlib.sha3_256(testzip_bytes).digest()
        sig = self.tmp_signer.sign(zip_hash)

        self.assertTrue(self.verifier.verify(zip_hash, sig))


if __name__ == "__main__":
    unittest.main()
