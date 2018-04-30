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
import hashlib
import unittest

from iconservice.iconscore.icon_score_install_signer import ScoreInstallSigner
from iconservice.iconscore.icon_score_install_signer import SignVerifier


class TestScoreInstallSigner(unittest.TestCase):
    def setUp(self):
        self.msg = 'install transaction'
        self.msg_bytes = self.msg.encode()
        self.tx_hash = hashlib.sha3_256(self.msg_bytes).digest()
        self.signer = ScoreInstallSigner()
        self.sign_verifier = SignVerifier(self.signer.public_key)

    def test_sign_and_verify(self):
        sig = self.signer.sign(self.tx_hash)
        self.assertTrue(isinstance(sig, bytes))

        public_key = self.signer.public_key
        self.assertTrue(isinstance(public_key, bytes))
        self.assertEqual(65, len(public_key))

        verified = self.sign_verifier.verify(self.tx_hash, sig)
        self.assertTrue(verified)

        wrong_message = "wronag message"
        wrong_message_bytes = wrong_message.encode()
        wrong_hash = hashlib.sha3_256(wrong_message_bytes).digest()
        verified2 = self.sign_verifier.verify(wrong_hash, sig)
        self.assertFalse(verified2)


if __name__ == "__main__":
    unittest.main()
