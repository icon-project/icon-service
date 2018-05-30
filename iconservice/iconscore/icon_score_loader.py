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
from os import path, listdir
from os.path import dirname
from collections import defaultdict
from ..logger import Logger

from ..icon_service_engine import ICON_SERVICE_LOG_TAG
ICON_LOADER_LOG_TAG = f'{ICON_SERVICE_LOG_TAG}_Loader'


class IconScoreLoader(object):
    __PACKAGE_PATH = 'package.json'
    __SCORE_ENTERANCE_FILE_PATH = '__init__.py'

    def __init__(self, icon_score_root_path: str):
        self.__score_root_path = icon_score_root_path

    @property
    def score_root_path(self):
        return self.__score_root_path

    @staticmethod
    def __load_json(root_path: str) -> dict:
        root_path = path.join(root_path, IconScoreLoader.__PACKAGE_PATH)
        with open(root_path, 'r') as f:
            return json.load(f)

    @staticmethod
    def __load_user_score_module(file_path: str, call_class_name: str) -> callable:

        dir_path = dirname(file_path)

        if dir_path in sys_path:
            Logger.log_error(f"sys.path has the score path: {dir_path}", ICON_LOADER_LOG_TAG)
        else:
            sys_path.append(dir_path)

        module = importlib.machinery.SourceFileLoader(call_class_name, file_path).load_module()
        sys_path.remove(dir_path)

        return getattr(module, call_class_name)

    @staticmethod
    def __get_last_version_path(score_root_path: str, address_body: str) -> str:
        address_path = path.join(score_root_path, str(address_body))

        tmp_dict = defaultdict(list)
        for dir_name in listdir(address_path):
            block_height, tx_index = dir_name.split('_')
            tmp_dict[block_height].append(tx_index)

        last_block_height = sorted(tmp_dict.keys(), key=int)[-1]
        last_tx_index = sorted(tmp_dict[last_block_height], key=int)[-1]

        last_version = '{}_{}'.format(last_block_height, last_tx_index)
        return path.join(address_path, last_version)

    def load_score(self, address_body: str) -> callable:
        last_version_path = self.__get_last_version_path(self.__score_root_path, address_body)

        score_package_info = self.__load_json(last_version_path)
        score_package_init_file_path = path.join(last_version_path, IconScoreLoader.__SCORE_ENTERANCE_FILE_PATH)
        score = self.__load_user_score_module(score_package_init_file_path, score_package_info["main_score"])
        return score
