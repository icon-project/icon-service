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

import json
import importlib.machinery
import importlib.util
from sys import path as sys_path
from os import path


class IconScoreLoader(object):
    _PACKAGE_PATH = 'package.json'

    def __init__(self, score_root_path: str):
        self._score_root_path = score_root_path
        sys_path.append(score_root_path)

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
        import_path: str = last_version_path.split(tmp_str)[1]
        import_path = import_path.replace('/', '.')

        if False:
            package_module = importlib.import_module(f".{score_package_info[__MAIN_FILE]}", package=import_path)
            return getattr(package_module, score_package_info[__MAIN_SCORE])

        spec = importlib.util.find_spec(f".{score_package_info[__MAIN_FILE]}", import_path)
        mod = importlib.util.module_from_spec(spec)
        mod = mod.__loader__.load_module()
        return getattr(mod, score_package_info[__MAIN_SCORE])

    @staticmethod
    def _get_score_path_by_score_id(score_root_path: str, address_body: str, score_id: str) -> str:
        address_path = path.join(score_root_path, address_body)
        return path.join(address_path, score_id)

    def load_score(self, address_body: str, score_id: str) -> callable:
        last_version_path = self._get_score_path_by_score_id(self._score_root_path, address_body, score_id)

        score_package_info = self._load_json(last_version_path)
        score = self._load_user_score_module(last_version_path, score_package_info)
        return score
