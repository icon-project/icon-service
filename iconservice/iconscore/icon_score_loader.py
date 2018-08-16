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

import importlib.util
import json
from os import path
from sys import path as sys_path

from .import_validator import ImportValidator
from ..icon_constant import IconScoreLoaderFlag


class IconScoreLoader(object):
    _PACKAGE_PATH = 'package.json'

    def __init__(self, score_root_path: str, flag: int):
        self._score_root_path = score_root_path
        self._flag = flag
        sys_path.append(score_root_path)

    def _is_flag_on(self, flag: 'IconScoreLoaderFlag') -> bool:
        return (self._flag & flag) == flag

    @property
    def score_root_path(self):
        return self._score_root_path

    @staticmethod
    def _load_json(root_path: str) -> dict:
        root_path = path.join(root_path, IconScoreLoader._PACKAGE_PATH)
        with open(root_path, 'r') as f:
            return json.load(f)

    def _load_user_score_module(self, last_version_path: str, score_package_info: dict) -> callable:
        __MAIN_SCORE = 'main_score'
        __MAIN_FILE = 'main_file'

        tmp_str = f"{self._score_root_path}/"
        parent_import_path: str = last_version_path.split(tmp_str)[1]
        parent_import = parent_import_path.replace('/', '.')

        if self._is_flag_on(IconScoreLoaderFlag.ENABLE_VALIDATE_IMPORT_WHITELIST):
            ImportValidator().validator(tmp_str + parent_import_path, parent_import)

        spec = importlib.util.find_spec(f".{score_package_info[__MAIN_FILE]}", parent_import)
        module = spec.loader.load_module()
        return getattr(module, score_package_info[__MAIN_SCORE])

    @staticmethod
    def _get_score_path_by_tx_hash(score_root_path: str, address_body: str, tx_hash: bytes) -> str:
        address_path = path.join(score_root_path, address_body)
        converted_tx_hash = f'0x{bytes.hex(tx_hash)}'
        return path.join(address_path, converted_tx_hash)

    def load_score(self, address_body: str, tx_hash: bytes) -> callable:
        last_version_path = self._get_score_path_by_tx_hash(self._score_root_path, address_body, tx_hash)
        score_package_info = self._load_json(last_version_path)
        score = self._load_user_score_module(last_version_path, score_package_info)

        return score
