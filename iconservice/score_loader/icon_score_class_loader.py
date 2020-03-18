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
import json
import os
import sys
from typing import TYPE_CHECKING

import iconservice.iconscore.utils as utils
from iconservice.base.address import Address
from iconservice.base.exception import IllegalFormatException
from iconservice.icon_constant import PACKAGE_JSON_FILE

if TYPE_CHECKING:
    from iconservice.base.address import Address


class IconScoreClassLoader:
    """IconScoreBase subclass Loader

    """
    @classmethod
    def init(cls, score_root_path: str):
        if score_root_path not in sys.path:
            sys.path.append(score_root_path)

    @classmethod
    def close(cls, score_root_path: str):
        sys.path.remove(score_root_path)

    @classmethod
    def _load_package_json(cls, score_deploy_path: str) -> dict:
        """Loads package.json in SCORE

        :param score_deploy_path:
        :return:
        """
        pkg_json_path = os.path.join(score_deploy_path, PACKAGE_JSON_FILE)
        with open(pkg_json_path, 'r') as f:
            return json.load(f)

    @classmethod
    def _get_package_info(cls, package_json: dict) -> tuple:
        """Returns main_module and main_score

        :param package_json: dict returned by _load_package_json()
        :return: tuple containing main_module and main_score
        """
        main_module: str = package_json.get('main_module')
        if not isinstance(main_module, str):
            # "main_file" field will be deprecated soon.
            # Use "main_module" instead
            main_module: str = package_json['main_file']

        # Relative package name is not allowed
        if main_module.startswith('.'):
            raise IllegalFormatException('Invalid main_module')

        main_score: str = package_json['main_score']

        return main_module, main_score

    @classmethod
    def run(cls, score_address: 'Address', tx_hash: bytes, score_root_path: str) -> type:
        """Load a IconScoreBase subclass and return it

        :param score_address:
        :param tx_hash:
        :param score_root_path:
        :return: subclass derived from IconScoreBase
        """
        score_deploy_path: str = utils.get_score_deploy_path(score_root_path, score_address, tx_hash)
        package_name: str = utils.get_package_name_by_address_and_tx_hash(score_address, tx_hash)

        package_json: dict = IconScoreClassLoader._load_package_json(score_deploy_path)
        main_module, main_score = IconScoreClassLoader._get_package_info(package_json)

        # In order for the new module to be noticed by the import system
        importlib.invalidate_caches()
        module = importlib.import_module(f".{main_module}", package_name)

        return getattr(module, main_score)
