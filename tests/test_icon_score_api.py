# -*- coding: utf-8 -*-
#
# Copyright 2019 ICON Foundation
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
import hashlib
import unittest

from iconservice.base.address import Address
from iconservice.iconscore.icon_score_base2 import _create_address_with_key, _recover_key


def create_msg_hash(tx: dict, excluded_keys: tuple) -> bytes:
    keys = [key for key in tx if key not in excluded_keys]
    keys.sort()

    msg = 'icx_sendTransaction'
    for key in keys:
        value: str = tx[key]
        msg += f'.{key}.{value}'

    return hashlib.sha3_256(msg.encode('utf-8')).digest()


class TestIconScoreApi(unittest.TestCase):
    def setUp(self):
        # The transaction in block 1000 of TestNet
        self.tx_v2 = {
            'from': 'hxdbc9f726ad776d9a43d5bad387eff01325178fa3',
            'to': 'hx0fb148785e4a5d77d16429c7ed2edae715a4453a',
            'value': '0x324e964b3eca80000',
            'fee': '0x2386f26fc10000',
            'timestamp': '1519709385120909',
            'tx_hash': '1257b9ea76e716b145463f0350f534f973399898a18a50d391e7d2815e72c950',
            'signature': 'WiRTA/tUNGVByc8fsZ7+U9BSDX4BcBuv2OpAuOLLbzUiCcovLPDuFE+PBaT8ovmz5wg+Bjr7rmKiu7Rl8v0DUQE=',
        }

        # The transaction in block 100000 of MainNet
        self.tx_v3 = {
            'version': '0x3',
            'nid': '0x1',
            'from': 'hx522bff55a62e0c75a1b51855b0802cfec6a92e84',
            'to': 'hx11de4e28be4845de3ea392fd8d758655bf766ca7',
            'value': '0x71afd498d0000',
            'stepLimit': '0xf4240',
            'timestamp': '0x57a4e5556cc03',
            'signature': 'fcEMXqEGlqEivXXr7YtD/F1RXgxSXF+R4gVrGKxT1zxi3HukX4NzkSl9/Es1G+nyZx+kviTAtQFUrA+/T0NrfAA=',
            'txHash': '6c71ac77b2d130a1f81d234e814974e85cabb0a3ec462c66ff3f820502d0ded2'
        }

    def test_recover_key_v2_and_create_address_with_key(self):
        signature: bytes = base64.b64decode(self.tx_v2['signature'])
        self.assertIsInstance(signature, bytes)
        self.assertTrue(len(signature) > 0)

        msg_hash: bytes = create_msg_hash(self.tx_v2, ('tx_hash', 'signature'))
        self.assertEqual(msg_hash, bytes.fromhex(self.tx_v2['tx_hash']))

        uncompressed_public_key: bytes = _recover_key(msg_hash, signature, compressed=False)
        self.assertIsInstance(uncompressed_public_key, bytes)
        self.assertEqual(65, len(uncompressed_public_key))
        self.assertEqual(0x04, uncompressed_public_key[0])

        address: Address = _create_address_with_key(uncompressed_public_key)
        self.assertEqual(self.tx_v2['from'], str(address))

        compressed_public_key: bytes = _recover_key(msg_hash, signature, compressed=True)
        self.assertIsInstance(compressed_public_key, bytes)
        self.assertEqual(33, len(compressed_public_key))
        self.assertIn(compressed_public_key[0], (0x02, 0x03))

        address: Address = _create_address_with_key(compressed_public_key)
        self.assertEqual(self.tx_v2['from'], str(address))

    def test_recover_key_v3_and_create_address_with_key(self):
        signature: bytes = base64.b64decode(self.tx_v3['signature'])
        self.assertIsInstance(signature, bytes)
        self.assertTrue(len(signature) > 0)

        msg_hash: bytes = create_msg_hash(self.tx_v3, ('txHash', 'signature'))
        self.assertEqual(msg_hash, bytes.fromhex(self.tx_v3['txHash']))

        uncompressed_public_key: bytes = _recover_key(msg_hash, signature, compressed=False)
        self.assertIsInstance(uncompressed_public_key, bytes)
        self.assertEqual(65, len(uncompressed_public_key))
        self.assertEqual(0x04, uncompressed_public_key[0])

        address: Address = _create_address_with_key(uncompressed_public_key)
        self.assertEqual(self.tx_v3['from'], str(address))

        compressed_public_key: bytes = _recover_key(msg_hash, signature, compressed=True)
        self.assertIsInstance(compressed_public_key, bytes)
        self.assertEqual(33, len(compressed_public_key))
        self.assertIn(compressed_public_key[0], (0x02, 0x03))

        address: Address = _create_address_with_key(compressed_public_key)
        self.assertEqual(self.tx_v3['from'], str(address))


if __name__ == '__main__':
    unittest.main()
