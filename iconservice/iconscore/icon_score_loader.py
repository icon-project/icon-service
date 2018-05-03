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
import os, sys, importlib.machinery
from collections import defaultdict
from ..base.address import Address

# ImportWarning: can't resolve package from __spec__ or __package__, falling back on __name__ and __path__ return f(*args, **kwds)
from ..iconscore.icon_score_base import IconScoreBase

ICON_ROOT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))


class IconScoreLoader(object):
    _PACKAGE_PATH = 'package.json'

    def __init__(self, icon_score_root_path: str):
        self.__score_root_path = os.path.join(ICON_ROOT_PATH, icon_score_root_path)

    @staticmethod
    def __load_json(root_path: str) -> dict:
        path = os.path.join(root_path, IconScoreLoader._PACKAGE_PATH)
        with open(path, 'r') as f:
            return json.load(f)

    @staticmethod
    def __load_user_score_module(path: str, call_class_name: str):

        dir_path = os.path.dirname(path)

        if dir_path in sys.path:
            print(f"sys.path has the score path: {dir_path}")
        else:
            sys.path.append(dir_path)

        module = importlib.machinery.SourceFileLoader(call_class_name, path).load_module()
        return getattr(module, call_class_name)

    @staticmethod
    def __get_last_version_path(score_root_path: str, address_body: str):
        address_path = os.path.join(score_root_path, str(address_body))

        tmp_dict = defaultdict(list)
        for dir_name in os.listdir(address_path):
            block_height, tx_index = dir_name.split('_')
            tmp_dict[block_height].append(tx_index)

        last_block_height = sorted(tmp_dict.keys(), key=int)[-1]
        last_tx_index = sorted(tmp_dict[last_block_height], key=int)[-1]

        last_version = '{}_{}'.format(last_block_height, last_tx_index)
        return os.path.join(address_path, last_version)

    def load_score(self, address_body: str):
        last_version_path = self.__get_last_version_path(self.__score_root_path, address_body)
        score_package_info = self.__load_json(last_version_path)
        score_main_file_path = os.path.join(last_version_path, score_package_info["main_file"] + ".py")
        score = self.__load_user_score_module(score_main_file_path, score_package_info["main_score"])
        return score
