#!/usr/bin/env python3
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

import unittest

from iconservice.deploy.icon_score_deploy_storage import \
    IconScoreDeployTXParams, IconScoreDeployInfo, DeployType, DeployState
from tests import create_tx_hash, create_address


class TestIconScoreDeployInfos(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_tx_params_from_bytes_to_bytes1(self):
        tx_hash1 = create_tx_hash()
        score_address = create_address(1)
        deploy_state = DeployType.INSTALL
        data_params = {
            "contentType": "application/zip",
            "content": "0x1867291283973610982301923812873419826abcdef91827319263187263a7326e",
            "params": {
                "name": "ABCToken",
                "symbol": "abc",
                "decimals": "0x12"
            }
        }

        tx_params1 = IconScoreDeployTXParams(tx_hash1, deploy_state, score_address, data_params)

        data = IconScoreDeployTXParams.to_bytes(tx_params1)
        self.assertTrue(isinstance(data, bytes))

        tx_params2 = IconScoreDeployTXParams.from_bytes(data)
        self.assertEqual(tx_params2.tx_hash, tx_hash1)
        self.assertEqual(tx_params2.deploy_type, deploy_state)
        self.assertEqual(tx_params2._score_address, score_address)
        self.assertEqual(tx_params2.deploy_data, data_params)

    def test_tx_params_from_bytes_to_bytes2(self):
        tx_hash1 = create_tx_hash()
        score_address = create_address(1)
        deploy_state = DeployType.INSTALL
        data_params = {
            "contentType": "application/zip",
            "content": "0x1867291283973610982301923812873419826abcdef91827319263187263a7326e",
            "params": {
                "name": "ABCToken",
                "symbol": "abc",
                "decimals": "0x12"
            }
        }

        tx_params1 = IconScoreDeployTXParams(tx_hash1, deploy_state, score_address, data_params)

        data = IconScoreDeployTXParams.to_bytes(tx_params1)
        self.assertTrue(isinstance(data, bytes))

        tx_params2 = IconScoreDeployTXParams.from_bytes(data)
        self.assertEqual(tx_params2.tx_hash, tx_hash1)
        self.assertEqual(tx_params2.deploy_type, deploy_state)
        self.assertEqual(tx_params2._score_address, score_address)
        self.assertEqual(tx_params2.deploy_data, data_params)

    def test_deploy_info_from_bytes_to_bytes(self):
        score_address = create_address(1)
        owner_address = create_address()
        tx_hash1 = create_tx_hash()
        tx_hash2 = create_tx_hash()
        deploy_state = DeployState.INACTIVE

        info1 = IconScoreDeployInfo(score_address, deploy_state, owner_address, tx_hash1, tx_hash2)

        data = IconScoreDeployInfo.to_bytes(info1)
        self.assertTrue(isinstance(data, bytes))

        info2 = IconScoreDeployInfo.from_bytes(data)
        self.assertEqual(info2.score_address, score_address)
        self.assertEqual(info2.deploy_state, deploy_state)
        self.assertEqual(info2.owner, owner_address)
        self.assertEqual(info2.current_tx_hash, tx_hash1)
        self.assertEqual(info2.next_tx_hash, tx_hash2)

    def test_deploy_info_from_bytes_to_bytes_none_check(self):
        score_address = create_address(1)
        owner_address = create_address()
        tx_hash1 = create_tx_hash()
        tx_hash2 = None
        deploy_state = DeployState.INACTIVE

        info1 = IconScoreDeployInfo(score_address, deploy_state, owner_address, tx_hash1, tx_hash2)

        data = IconScoreDeployInfo.to_bytes(info1)
        self.assertTrue(isinstance(data, bytes))

        info2 = IconScoreDeployInfo.from_bytes(data)
        self.assertEqual(info2.score_address, score_address)
        self.assertEqual(info2.deploy_state, deploy_state)
        self.assertEqual(info2.owner, owner_address)
        self.assertEqual(info2.current_tx_hash, tx_hash1)
        self.assertEqual(info2.next_tx_hash, tx_hash2)
