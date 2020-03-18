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
from unittest.mock import Mock

import pytest

import iconservice.iconscore.utils as utils
from iconservice.deploy.utils import convert_path_to_package_name
from iconservice.score_loader.icon_score_class_loader import IconScoreClassLoader
from tests import create_address, create_tx_hash


class TestSCORELoader:
    score_deploy_path = "path"
    package_name = "package_name"
    main_file = "main_file_value"
    main_score = "main_score_value"
    ins_ret_value = "ins_ret_value"

    @pytest.fixture
    def mock_utils(self, monkeypatch):
        monkeypatch.setattr(utils, "get_score_deploy_path", Mock(return_value=self.score_deploy_path))
        monkeypatch.setattr(utils, "get_package_name_by_address_and_tx_hash", Mock(return_value=self.package_name))
        yield utils
        monkeypatch.undo()

    @pytest.fixture
    def mock_icon_score_class_loader(self, monkeypatch):
        package_json = {
            "version": "0.0,1",
            "main_file": self.main_file,
            "main_score": self.main_score
        }
        package_info = self.main_file, self.main_score

        monkeypatch.setattr(IconScoreClassLoader, "_load_package_json", Mock(return_value=package_json))
        monkeypatch.setattr(IconScoreClassLoader, "_get_package_info", Mock(return_value=package_info))
        yield IconScoreClassLoader
        monkeypatch.undo()

    @pytest.fixture
    def mock_importlib(self, monkeypatch):

        ins = Mock()
        ins.attach_mock(Mock(return_value=self.ins_ret_value), self.main_score)

        monkeypatch.setattr(importlib, "invalidate_caches", Mock())
        monkeypatch.setattr(importlib, "import_module", Mock(return_value=ins))
        yield importlib
        monkeypatch.undo()

    def test_run(self, mock_utils, mock_icon_score_class_loader, mock_importlib):
        # Arrange
        address = create_address()
        tx_hash = create_tx_hash()
        score_root_path = ".score"

        # Act
        ret_module = IconScoreClassLoader.run(score_address=address,
                                              tx_hash=tx_hash,
                                              score_root_path=score_root_path)

        # Assert
        mock_utils.get_score_deploy_path.assert_called_once_with(score_root_path, address, tx_hash)
        mock_utils.get_package_name_by_address_and_tx_hash.assert_called_once_with(address, tx_hash)
        mock_icon_score_class_loader._load_package_json.assert_called_once_with(mock_utils.get_score_deploy_path.return_value)
        mock_icon_score_class_loader._get_package_info.assert_called_once_with(IconScoreClassLoader._load_package_json.return_value)

        assert self.ins_ret_value == ret_module()


@pytest.mark.parametrize("package_json, expected_module, expected_score", [
    ({"version": "1.0.0", "main_module": "token", "main_score": "Token"}, "token", "Token"),
    ({"version": "1.0.0", "main_file": "token", "main_score": "Token"}, "token", "Token"),
    ({"version": "1.0.0", "main_file": "invalid.token", "main_module": "valid.token", "main_score": "Token"}, "valid.token", "Token"),
])
def test_get_package_info(package_json, expected_module, expected_score):
    main_module, main_score = IconScoreClassLoader._get_package_info(package_json)
    assert expected_module == main_module
    assert expected_score == main_score


# TODO unused test case
def test_make_pkg_root_import():
    address = '010cb2b5d7cca1dec18c51de595155a4468711d4f4'
    tx_hash = '0x49485e08589256a68e02a63fa3484b16edd322a729394fbd6b543d77a7f68621'
    score_root_path = './.score'
    score_path = f'{score_root_path}/{address}/{tx_hash}'
    expected_import_name: str = f'{address}.{tx_hash}'
    index: int = len(score_root_path)

    import_name: str = convert_path_to_package_name(score_path[index:])
    assert import_name == expected_import_name

    score_root_path = '/haha/hoho/hehe/score/'
    index: int = len(score_root_path)
    score_path = f'{score_root_path}/{address}/{tx_hash}'
    import_name: str = convert_path_to_package_name(score_path[index:])
    assert import_name == expected_import_name
