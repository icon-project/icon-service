# -*- coding: utf-8 -*-

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
from iconservice.utils.hashing.hash_generator import HashGenerator


class TestHashGenerator:
    def test_generate_hash(self):
        main_net_tx_data = {
            "from": "hx930eb8a0e793253aad876503367c344fe8d4e282",
            "to": "cx502c47463314f01e84b1b203c315180501eb2481",
            "version": "0x3",
            "nid": "0x1",
            "stepLimit": "0x7a120",
            "timestamp": "0x58d2588ab7288",
            "nonce": "0x3059",
            "dataType": "call",
            "data": {
                "method": "transfer",
                "params": {
                    "_to": "hx1ada76577eac29b1e60efee22aac66af9f434036",
                    "_value": "0x2b5e3af16b1880000",
                    "_data": "20"
                }
            }
        }
        main_net_tx_hash = "0xc64119ddd6b0d5034cdcd8b903dadca34e3d79cfe3e00bb2bca8a9ec48e25978"
        actual_tx_hash = HashGenerator.generate_hash(main_net_tx_data)

        assert actual_tx_hash == main_net_tx_hash

        main_net_tx_data = {
            "version": "0x3",
            "from": "hx226e6e4340136836b36977bd76ca83746b8b071c",
            "to": "cxb7ef03fea5fa9b2fe1f00f548d6da7ff2ddfebd5",
            "stepLimit": "0x989680",
            "timestamp": "0x58d25822f154c",
            "nid": "0x1",
            "nonce": "0x64",
            "dataType": "call",
            "data": {
                "method": "transaction_RT",
                "params": {
                    "_date": "20190708",
                    "_time": "0625",
                    "_div": "GOOGLE",
                    "_value": "[\"Earthquake\", \"Concacaf Gold Cup\", \"Concacaf Gold Cup\", \"Bella Thorne\", \"New York Knicks\"]"
                }
            }}
        main_net_tx_hash = "0x77a6109d6be90643e54e4ebfbea86f966937cc7978c7105ffea9e852ef447ae3"
        actual_tx_hash = HashGenerator.generate_hash(main_net_tx_data)

        assert actual_tx_hash == main_net_tx_hash
