# -*- coding: utf-8 -*-
#
# Copyright 2019 ICON Foundation Inc.
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


def create_msg_hash(tx: dict) -> bytes:
    keys = [key for key in tx if key not in ('tx_hash', 'method', 'signature')]
    keys.sort()
    
    msg = tx['method']
    for key in keys:
        value: str = tx[key]
        msg += f'.{key}.{value}'
        
    return hashlib.sha3_256(msg.encode('utf-8')).digest()


class TestIconScoreApi(unittest.TestCase):
    def setUp(self):
        # The real transaction in block 1000 of TestNet is used for unittest.
        self.tx = {
            'from': 'hxdbc9f726ad776d9a43d5bad387eff01325178fa3',
            'to': 'hx0fb148785e4a5d77d16429c7ed2edae715a4453a',
            'value': '0x324e964b3eca80000',
            'fee': '0x2386f26fc10000',
            'timestamp': '1519709385120909',
            'tx_hash': '1257b9ea76e716b145463f0350f534f973399898a18a50d391e7d2815e72c950',
            'signature': 'WiRTA/tUNGVByc8fsZ7+U9BSDX4BcBuv2OpAuOLLbzUiCcovLPDuFE+PBaT8ovmz5wg+Bjr7rmKiu7Rl8v0DUQE=',
            'method': 'icx_sendTransaction'
        }
    
    def test_recover_key(self):
        signature: bytes = base64.b64decode(self.tx['signature'])
        
        msg_hash: bytes = create_msg_hash(self.tx)
        self.assertEqual(msg_hash, bytes.fromhex(self.tx['tx_hash']))
        
        public_key: bytes = _recover_key(msg_hash, signature)
        self.assertIsInstance(public_key, bytes)
        self.assertEqual(65, len(public_key))
        self.assertEqual(0x4, public_key[0])
        
        address: Address = _create_address_with_key(public_key)
        self.assertEqual(self.tx['from'], str(address))
    

if __name__ == '__main__':
    unittest.main()
