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

import importlib.util
import json
import os
import sys

from ..base.address import Address
from ..deploy.utils import get_package_name_by_address_and_tx_hash
from ..deploy.utils import get_score_deploy_path
from ..icon_constant import PACKAGE_JSON_FILE


class IconScoreClassLoader(object):
    """IconScoreBase subclass Loader

    """
    _MAIN_SCORE = 'main_score'
    _MAIN_FILE = 'main_file'

    @staticmethod
    def init(score_root_path: str):
        if score_root_path not in sys.path:
            sys.path.append(score_root_path)

    @staticmethod
    def exit(score_root_path: str):
        sys.path.remove(score_root_path)

    @staticmethod
    def _load_package_json(score_deploy_path: str) -> dict:
        """Loads package.json in SCORE

        :param score_deploy_path:
        :return:
        """
        pkg_json_path = os.path.join(score_deploy_path, PACKAGE_JSON_FILE)
        with open(pkg_json_path, 'r') as f:
            return json.load(f)

    @staticmethod
    def run(score_address: 'Address', tx_hash: bytes, score_root_path: str) -> type:
        """Load a IconScoreBase subclass and return it

        :param score_address:
        :param tx_hash:
        :param score_root_path:
        :return: subclass derived from IconScoreBase
        """

        score_deploy_path: str = get_score_deploy_path(score_root_path, score_address, tx_hash)
        score_package_info: dict = IconScoreClassLoader._load_package_json(score_deploy_path)
        package_name: str = get_package_name_by_address_and_tx_hash(score_address, tx_hash)

        # in order for the new module to be noticed by the import system
        importlib.invalidate_caches()
        module = importlib.import_module(
            f".{score_package_info[IconScoreClassLoader._MAIN_FILE]}", package_name)

        return getattr(module, score_package_info[IconScoreClassLoader._MAIN_SCORE])
