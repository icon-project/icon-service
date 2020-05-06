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
from copy import deepcopy
from unittest.mock import Mock, patch

from iconservice.base.exception import (
    ExceptionCode,
    AccessDeniedException,
    InvalidParamsException,
)
from iconservice.database.db import ContextDatabase
from iconservice.deploy import DeployStorage
from iconservice.deploy.storage import (
    IconScoreDeployTXParams,
    IconScoreDeployInfo,
    DeployType,
    DeployState,
)
from iconservice.icon_constant import ZERO_TX_HASH
from iconservice.iconscore.icon_score_context import IconScoreContext
from tests import create_tx_hash, create_address


class TestIconScoreDeployTxParams(unittest.TestCase):
    def test_tx_params_from_bytes_to_bytes(self):
        tx_hash1 = create_tx_hash()
        score_address = create_address(1)
        deploy_state = DeployType.INSTALL
        data_params = {
            "contentType": "application/zip",
            "content": "0x1867291283973610982301923812873419826abcdef91827319263187263a7326e",
            "params": {"name": "ABCToken", "symbol": "abc", "decimals": "0x12"},
        }

        tx_params1 = IconScoreDeployTXParams(
            tx_hash1, deploy_state, score_address, data_params
        )

        data = IconScoreDeployTXParams.to_bytes(tx_params1)
        self.assertTrue(isinstance(data, bytes))

        tx_params2 = IconScoreDeployTXParams.from_bytes(data)
        self.assertEqual(tx_params2.tx_hash, tx_hash1)
        self.assertEqual(tx_params2.deploy_type, deploy_state)
        self.assertEqual(tx_params2._score_address, score_address)
        self.assertEqual(tx_params2.deploy_data, data_params)


class TestIconScoreDeployInfo(unittest.TestCase):
    def test_deploy_info_from_bytes_to_bytes(self):
        score_address = create_address(1)
        owner_address = create_address()
        tx_hash1 = create_tx_hash()
        tx_hash2 = create_tx_hash()
        deploy_state = DeployState.INACTIVE

        info1 = IconScoreDeployInfo(
            score_address, deploy_state, owner_address, tx_hash1, tx_hash2
        )

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
        tx_hash2 = ZERO_TX_HASH
        deploy_state = DeployState.INACTIVE

        info1 = IconScoreDeployInfo(
            score_address, deploy_state, owner_address, tx_hash1, tx_hash2
        )

        data = IconScoreDeployInfo.to_bytes(info1)
        self.assertTrue(isinstance(data, bytes))

        info2 = IconScoreDeployInfo.from_bytes(data)
        self.assertEqual(info2.score_address, score_address)
        self.assertEqual(info2.deploy_state, deploy_state)
        self.assertEqual(info2.owner, owner_address)
        self.assertEqual(info2.current_tx_hash, tx_hash1)
        self.assertEqual(info2.next_tx_hash, tx_hash2)


class TestIconScoreDeployStorage(unittest.TestCase):
    def setUp(self):
        self.storage = DeployStorage(Mock(spec=ContextDatabase))

    def test_put_deploy_info_and_tx_params(self):
        self.storage.put_deploy_tx_params = Mock()
        self.storage.get_deploy_tx_params = Mock(return_value=bytes())
        context = Mock(spec=IconScoreContext)
        score_address = create_address(1)
        deploy_type = DeployType.INSTALL
        owner = create_address()
        tx_hash = create_tx_hash()
        deploy_data = {}
        with self.assertRaises(InvalidParamsException) as e:
            self.storage.put_deploy_info_and_tx_params(
                context, score_address, deploy_type, owner, tx_hash, deploy_data
            )
        self.assertEqual(e.exception.code, ExceptionCode.INVALID_PARAMETER)
        self.assertEqual(
            e.exception.message, f"deploy_params already exists: {tx_hash}"
        )
        self.storage.put_deploy_tx_params.assert_not_called()

        with patch(
            "iconservice.deploy.storage.IconScoreDeployTXParams"
        ) as MockTxParams:
            with patch(
                "iconservice.deploy.storage.IconScoreDeployInfo"
            ) as MockDeployInfos:
                self.storage.put_deploy_tx_params.reset_mock()
                self.storage.get_deploy_tx_params.reset_mock()
                self.storage.get_deploy_tx_params.return_value = None
                self.storage.get_deploy_info = Mock(return_value=None)
                self.storage.put_deploy_info = Mock()
                context = Mock(spec=IconScoreContext)
                score_address = create_address(1)
                deploy_type = DeployType.INSTALL
                owner = create_address()
                tx_hash = create_tx_hash()
                deploy_data = {}
                tx_params = IconScoreDeployTXParams(
                    tx_hash, deploy_type, score_address, deploy_data
                )
                MockTxParams.return_value = tx_params
                deploy_info = IconScoreDeployInfo(
                    score_address, DeployState.INACTIVE, owner, ZERO_TX_HASH, tx_hash
                )
                MockDeployInfos.return_value = deploy_info

                self.storage.put_deploy_info_and_tx_params(
                    context, score_address, deploy_type, owner, tx_hash, deploy_data
                )
                self.storage.get_deploy_tx_params.assert_called_once_with(
                    context, tx_hash
                )
                self.storage.put_deploy_tx_params.assert_called_once_with(
                    context, tx_params
                )
                self.storage.get_deploy_info.assert_called_once_with(
                    context, score_address
                )
                self.storage.put_deploy_info.assert_called_once_with(
                    context, deploy_info
                )

        with patch(
            "iconservice.deploy.storage.IconScoreDeployTXParams"
        ) as MockTxParams:
            self.storage.put_deploy_tx_params.reset_mock()
            self.storage.get_deploy_tx_params.reset_mock()
            self.storage.get_deploy_tx_params.return_value = None
            self.storage.put_deploy_info = Mock()
            context = Mock(spec=IconScoreContext)
            score_address = create_address(1)
            deploy_type = DeployType.INSTALL
            owner = create_address()
            tx_hash = create_tx_hash()
            deploy_data = {}
            deploy_info = IconScoreDeployInfo(
                score_address, DeployState.INACTIVE, owner, ZERO_TX_HASH, tx_hash
            )
            tx_params = IconScoreDeployTXParams(
                tx_hash, deploy_type, score_address, deploy_data
            )
            self.storage.get_deploy_info = Mock(return_value=deploy_info)
            MockTxParams.return_value = tx_params

            other_owner = create_address()

            with self.assertRaises(AccessDeniedException) as e:
                self.storage.put_deploy_info_and_tx_params(
                    context,
                    score_address,
                    deploy_type,
                    other_owner,
                    tx_hash,
                    deploy_data,
                )
            self.assertEqual(e.exception.code, ExceptionCode.ACCESS_DENIED)
            self.assertEqual(
                e.exception.message,
                f"Invalid owner: {deploy_info.owner} != {other_owner}",
            )

            self.storage.get_deploy_tx_params.assert_called_once_with(context, tx_hash)
            self.storage.put_deploy_tx_params.assert_called_once_with(
                context, tx_params
            )
            self.storage.get_deploy_info.assert_called_once_with(context, score_address)

        with patch(
            "iconservice.deploy.storage.IconScoreDeployTXParams"
        ) as MockTxParams:
            self.storage.put_deploy_tx_params.reset_mock()
            self.storage.get_deploy_tx_params.reset_mock()
            self.storage.get_deploy_tx_params.return_value = None
            self.storage.put_deploy_info = Mock()
            self.storage._db.delete = Mock()
            context = Mock(spec=IconScoreContext)
            context.revision = 0
            score_address = create_address(1)
            deploy_type = DeployType.INSTALL
            owner = create_address()
            tx_hash = create_tx_hash()
            deploy_data = {}
            already_tx_hash = create_tx_hash()
            deploy_info = IconScoreDeployInfo(
                score_address,
                DeployState.INACTIVE,
                owner,
                ZERO_TX_HASH,
                already_tx_hash,
            )
            tx_params = IconScoreDeployTXParams(
                tx_hash, deploy_type, score_address, deploy_data
            )
            self.storage.get_deploy_info = Mock(return_value=deepcopy(deploy_info))
            self.storage._create_db_key = Mock(return_value=deploy_info.next_tx_hash)
            MockTxParams.return_value = tx_params

            self.storage.put_deploy_info_and_tx_params(
                context, score_address, deploy_type, owner, tx_hash, deploy_data
            )
            self.storage.get_deploy_tx_params.assert_called_once_with(context, tx_hash)
            self.storage.put_deploy_tx_params.assert_called_once_with(
                context, tx_params
            )
            self.storage.get_deploy_info.assert_called_once_with(context, score_address)
            self.storage._db.delete.assert_called_once_with(
                context, deploy_info.next_tx_hash
            )

            self.storage.put_deploy_info.assert_called_once()
            ret_context, ret_deployinfo = self.storage.put_deploy_info.call_args[0]
            self.assertEqual(ret_context, context)
            self.assertEqual(ret_deployinfo.next_tx_hash, tx_hash)

    def test_update_score_info(self):
        context = Mock(spec=IconScoreContext)
        score_address = create_address(1)
        tx_hash = create_tx_hash()

        self.storage.get_deploy_info = Mock(return_value=None)
        with self.assertRaises(InvalidParamsException) as e:
            self.storage.update_score_info(context, score_address, tx_hash)
        self.assertEqual(e.exception.code, ExceptionCode.INVALID_PARAMETER)
        self.assertEqual(e.exception.message, f"deploy_info is None: {score_address}")
        self.storage.get_deploy_info.assert_called_once_with(context, score_address)

        current_tx_hash = create_tx_hash()
        next_tx_hash = create_tx_hash()
        deploy_info = IconScoreDeployInfo(
            score_address,
            DeployState.INACTIVE,
            create_address(),
            current_tx_hash,
            next_tx_hash,
        )
        self.storage.get_deploy_info = Mock(return_value=deepcopy(deploy_info))
        with self.assertRaises(InvalidParamsException) as e:
            self.storage.update_score_info(context, score_address, tx_hash)
        self.assertEqual(e.exception.code, ExceptionCode.INVALID_PARAMETER)
        self.assertEqual(
            e.exception.message,
            f"Invalid update: " f"tx_hash({tx_hash}) != next_tx_hash({next_tx_hash})",
        )
        self.storage.get_deploy_info.assert_called_once_with(context, score_address)

        owner = create_address()
        current_tx_hash = create_tx_hash()
        deploy_info = IconScoreDeployInfo(
            score_address, DeployState.INACTIVE, owner, current_tx_hash, tx_hash
        )
        self.storage.get_deploy_info = Mock(return_value=deepcopy(deploy_info))
        self.storage.put_deploy_info = Mock()
        self.storage.get_deploy_tx_params = Mock(return_value=None)
        with self.assertRaises(InvalidParamsException) as e:
            self.storage.update_score_info(context, score_address, tx_hash)
        self.assertEqual(e.exception.code, ExceptionCode.INVALID_PARAMETER)
        self.assertEqual(e.exception.message, f"tx_params is None: {tx_hash}")
        self.storage.get_deploy_info.assert_called_once_with(context, score_address)
        self.storage.put_deploy_info.assert_called_once()
        ret_context, ret_deploy_info = self.storage.put_deploy_info.call_args[0]
        self.assertEqual(ret_context, context)
        expected = IconScoreDeployInfo(
            score_address, DeployState.ACTIVE, owner, tx_hash, ZERO_TX_HASH
        )
        self.assertEqual(ret_deploy_info.to_bytes(), expected.to_bytes())

        self.storage.get_deploy_info = Mock(return_value=deepcopy(deploy_info))
        self.storage.put_deploy_info = Mock()
        self.storage.get_deploy_tx_params = Mock(
            return_value=Mock(spec=IconScoreDeployTXParams)
        )
        self.storage.update_score_info(context, score_address, tx_hash)
        self.storage.get_deploy_info.assert_called_once_with(context, score_address)
        self.storage.put_deploy_info.assert_called_once()
        ret_context, ret_deploy_info = self.storage.put_deploy_info.call_args[0]
        self.assertEqual(ret_context, context)
        expected = IconScoreDeployInfo(
            score_address, DeployState.ACTIVE, owner, tx_hash, ZERO_TX_HASH
        )
        self.assertEqual(ret_deploy_info.to_bytes(), expected.to_bytes())
        self.storage.get_deploy_tx_params.assert_called_once_with(context, tx_hash)

    def test_put_deploy_info(self):
        context = Mock(spec=IconScoreContext)
        score_address = create_address(1)
        deploy_info = IconScoreDeployInfo(
            score_address,
            DeployState.INACTIVE,
            create_address(),
            ZERO_TX_HASH,
            create_tx_hash(),
        )
        self.storage._create_db_key = Mock(return_value=score_address.to_bytes())
        self.storage._db.put = Mock()

        self.storage.put_deploy_info(context, deploy_info)
        self.storage._db.put.assert_called_once_with(
            context, score_address.to_bytes(), deploy_info.to_bytes()
        )

    def test_get_deploy_info(self):
        context = Mock(spec=IconScoreContext)

        score_address = create_address(1)
        self.storage._create_db_key = Mock(return_value=score_address.to_bytes())
        self.storage._db.get = Mock(return_value=None)
        self.assertEqual(None, self.storage.get_deploy_info(context, score_address))

        score_address = create_address(1)
        deploy_info = IconScoreDeployInfo(
            score_address,
            DeployState.INACTIVE,
            create_address(),
            ZERO_TX_HASH,
            create_tx_hash(),
        )
        self.storage._create_db_key = Mock(return_value=score_address.to_bytes())
        self.storage._db.get = Mock(return_value=deploy_info.to_bytes())
        self.assertEqual(
            deploy_info.to_bytes(),
            self.storage.get_deploy_info(context, score_address).to_bytes(),
        )

    def test_put_deploy_tx_params(self):
        context = Mock(spec=IconScoreContext)
        tx_hash = create_tx_hash()
        tx_params = IconScoreDeployTXParams(
            tx_hash, DeployType.INSTALL, create_address(1), {}
        )
        self.storage._create_db_key = Mock(return_value=tx_hash)
        self.storage._db.put = Mock()

        self.storage.put_deploy_tx_params(context, tx_params)
        self.storage._db.put.assert_called_once_with(
            context, tx_params.tx_hash, tx_params.to_bytes()
        )

    def test_get_deploy_tx_params(self):
        context = Mock(spec=IconScoreContext)

        tx_hash = create_tx_hash()
        self.storage._create_db_key = Mock(return_value=tx_hash)
        self.storage._db.get = Mock(return_value=None)
        self.assertEqual(None, self.storage.get_deploy_tx_params(context, tx_hash))

        tx_hash = create_tx_hash()
        tx_params = IconScoreDeployTXParams(
            tx_hash, DeployType.INSTALL, create_address(1), {}
        )
        self.storage._create_db_key = Mock(return_value=tx_hash)
        self.storage._db.get = Mock(return_value=tx_params.to_bytes())

        self.assertEqual(
            tx_params.to_bytes(),
            self.storage.get_deploy_tx_params(context, tx_hash).to_bytes(),
        )

    def test_create_db_key(self):
        prefix = b"prefix"
        src_key = b"src_key"
        self.assertEqual(prefix + src_key, self.storage._create_db_key(prefix, src_key))

        prefix = b""
        src_key = b""
        self.assertEqual(prefix + src_key, self.storage._create_db_key(prefix, src_key))

    def test_get_tx_hashes_by_score_address(self):
        context = Mock(spec=IconScoreContext)
        score_address = create_address(1)

        self.storage.get_deploy_info = Mock(return_value=None)
        self.assertEqual(
            (None, None),
            self.storage.get_tx_hashes_by_score_address(context, score_address),
        )
        self.storage.get_deploy_info.assert_called_once_with(context, score_address)

        deploy_info = Mock(spec=IconScoreDeployInfo)
        deploy_info.attach_mock(Mock(), "current_tx_hash")
        deploy_info.attach_mock(Mock(), "next_tx_hash")
        self.storage.get_deploy_info = Mock(return_value=deploy_info)
        self.assertEqual(
            (deploy_info.current_tx_hash, deploy_info.next_tx_hash),
            self.storage.get_tx_hashes_by_score_address(context, score_address),
        )
        self.storage.get_deploy_info.assert_called_once_with(context, score_address)

    def test_get_score_address_by_tx_hash(self):
        context = Mock(spec=IconScoreContext)
        tx_hash = create_tx_hash()

        self.storage.get_deploy_tx_params = Mock(return_value=None)
        self.assertIsNone(self.storage.get_score_address_by_tx_hash(context, tx_hash))
        self.storage.get_deploy_tx_params.assert_called_once_with(context, tx_hash)

        tx_params = Mock(spec=IconScoreDeployTXParams)
        self.storage.get_deploy_tx_params = Mock(return_value=tx_params)
        self.assertEqual(
            tx_params.score_address,
            self.storage.get_score_address_by_tx_hash(context, tx_hash),
        )
        self.storage.get_deploy_tx_params.assert_called_once_with(context, tx_hash)
