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
from sys import path as sys_path
from os import path
from os.path import dirname
from iconcommons.logger import Logger
from ..icon_constant import ICON_LOADER_LOG_TAG


class IconScoreLoader(object):
    __PACKAGE_PATH = 'package.json'
    __SCORE_ENTERANCE_FILE_PATH = '__init__.py'

    def __init__(self, score_root_path: str):
        self.__score_root_path = score_root_path

    @property
    def score_root_path(self):
        return self.__score_root_path

    @staticmethod
    def __load_json(root_path: str) -> dict:
        root_path = path.join(root_path, IconScoreLoader.__PACKAGE_PATH)
        with open(root_path, 'r') as f:
            return json.load(f)

    @staticmethod
    def __load_user_score_module(file_path: str, score_package_info: dict) -> callable:
        __MAIN_SCORE = 'main_score'
        __MAIN_FILE = 'main_file'

        dir_path = dirname(file_path)

        if dir_path in sys_path:
            Logger.error(f"sys.path has the score path: {dir_path}", ICON_LOADER_LOG_TAG)
        else:
            sys_path.append(dir_path)

        try:
            package_module = importlib.machinery.SourceFileLoader(
                score_package_info[__MAIN_SCORE], file_path).load_module()
            module = getattr(package_module, score_package_info[__MAIN_FILE])
            importlib.reload(module)
        finally:
            sys_path.remove(dir_path)

        return getattr(module, score_package_info[__MAIN_SCORE])

    @staticmethod
    def __get_score_path_by_score_id(score_root_path: str, address_body: str, score_id: str) -> str:
        address_path = path.join(score_root_path, address_body)
        return path.join(address_path, score_id)

    def load_score(self, address_body: str, score_id: str) -> callable:
        last_version_path = self.__get_score_path_by_score_id(self.__score_root_path, address_body, score_id)

        score_package_info = self.__load_json(last_version_path)
        score_package_init_file_path = path.join(last_version_path, IconScoreLoader.__SCORE_ENTERANCE_FILE_PATH)
        score = self.__load_user_score_module(score_package_init_file_path, score_package_info)
        return score
