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

import importlib
from unittest import mock

import pytest

import iconservice.iconscore.utils as utils
from iconservice.score_loader.icon_score_class_loader import IconScoreClassLoader
from tests import create_address, create_tx_hash


class TestSCORELoader:
    VERSION = "version"
    MAIN_MODULE = "main_module"
    MAIN_FILE = "main_file"
    MAIN_SCORE = "main_score"

    @pytest.fixture
    def mock_utils(self, mocker):
        mocker.patch.object(utils, "get_score_deploy_path")
        mocker.patch.object(utils, "get_package_name_by_address_and_tx_hash")
        return utils

    @pytest.fixture
    def mock_icon_score_class_loader(self, mocker):
        mocker.patch.object(IconScoreClassLoader, "_load_package_json")
        mocker.patch.object(IconScoreClassLoader, "_get_package_info")
        return IconScoreClassLoader

    @pytest.fixture
    def mock_importlib(self, mocker):
        mocker.patch.object(importlib, "invalidate_caches")
        mocker.patch.object(importlib, "import_module")
        return importlib

    @pytest.mark.parametrize(
        "deploy_path, package_name, main_file, main_score, ins_ret_value",
        [(".path", "addr.hash", "file", "Score", "ret_value"),],
    )
    def test_run(
        self,
        mock_utils,
        mock_icon_score_class_loader,
        mock_importlib,
        deploy_path,
        package_name,
        main_file,
        main_score,
        ins_ret_value,
    ):
        # Arrange
        address = create_address()
        tx_hash = create_tx_hash()
        score_root_path = ".score"

        # mock
        mock_utils.get_score_deploy_path.return_value = deploy_path
        mock_utils.get_package_name_by_address_and_tx_hash.return_value = package_name

        package_json = {
            self.VERSION: mock.ANY,
            self.MAIN_FILE: main_file,
            self.MAIN_SCORE: main_score,
        }
        mock_icon_score_class_loader._load_package_json.return_value = package_json
        mock_icon_score_class_loader._get_package_info.return_value = (
            main_file,
            main_score,
        )

        ins = mock.Mock()
        ins.attach_mock(mock.Mock(return_value=ins_ret_value), main_score)
        mock_importlib.import_module.return_value = ins

        # Act
        ret_module = IconScoreClassLoader.run(
            score_address=address, tx_hash=tx_hash, score_root_path=score_root_path
        )

        # Assert
        mock_utils.get_score_deploy_path.assert_called_once_with(
            score_root_path, address, tx_hash
        )
        mock_utils.get_package_name_by_address_and_tx_hash.assert_called_once_with(
            address, tx_hash
        )
        mock_icon_score_class_loader._load_package_json.assert_called_once_with(
            deploy_path
        )
        mock_icon_score_class_loader._get_package_info.assert_called_once_with(
            package_json
        )
        mock_importlib.invalidate_caches.assert_called_once()
        mock_importlib.import_module.assert_called_once_with(
            f".{main_file}", package_name
        )

        assert ins_ret_value == ret_module()

    @pytest.mark.parametrize(
        "package_json, expected_module, expected_score",
        [
            (
                {VERSION: mock.ANY, MAIN_MODULE: "token", MAIN_SCORE: "Token"},
                "token",
                "Token",
            ),
            (
                {VERSION: mock.ANY, MAIN_FILE: "token", MAIN_SCORE: "Token"},
                "token",
                "Token",
            ),
            (
                {
                    VERSION: mock.ANY,
                    MAIN_FILE: "invalid.token",
                    MAIN_MODULE: "valid.token",
                    MAIN_SCORE: "Token",
                },
                "valid.token",
                "Token",
            ),
        ],
    )
    def test_get_package_info(self, package_json, expected_module, expected_score):
        main_module, main_score = IconScoreClassLoader._get_package_info(package_json)
        assert expected_module == main_module
        assert expected_score == main_score
