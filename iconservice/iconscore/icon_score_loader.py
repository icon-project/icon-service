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
import sys
from os import path

from typing import TYPE_CHECKING

from .score_package_validator import ScorePackageValidator
from ..icon_constant import IconScoreLoaderFlag

if TYPE_CHECKING:
    from ..base.address import Address


class IconScoreLoader(object):
    _PACKAGE_PATH = 'package.json'
    _MAIN_SCORE = 'main_score'
    _MAIN_FILE = 'main_file'

    def __init__(self, score_root_path: str, flag: int):
        self._score_root_path = score_root_path
        self._flag = flag
        if score_root_path not in sys.path:
            sys.path.append(score_root_path)

    def _is_flag_on(self, flag: 'IconScoreLoaderFlag') -> bool:
        return (self._flag & flag) == flag

    @property
    def score_root_path(self):
        return self._score_root_path

    @staticmethod
    def _load_json(score_path: str) -> dict:
        pkg_json_path = path.join(score_path, IconScoreLoader._PACKAGE_PATH)
        with open(pkg_json_path, 'r') as f:
            return json.load(f)

    def make_score_path(self, score_addr: 'Address', tx_hash: 'bytes') -> str:
        converted_tx_hash = f'0x{bytes.hex(tx_hash)}'
        return path.join(self._score_root_path, score_addr.to_bytes().hex(), converted_tx_hash)

    def load_score(self, score_path: str) -> callable:
        score_package_info = self._load_json(score_path)
        pkg_root_import: str = self._make_pkg_root_import(score_path)

        if self._is_flag_on(IconScoreLoaderFlag.ENABLE_SCORE_PACKAGE_VALIDATOR):
            ScorePackageValidator().validator(score_path, pkg_root_import)

        spec = importlib.util.find_spec(f".{score_package_info[self._MAIN_FILE]}", pkg_root_import)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return getattr(mod, score_package_info[self._MAIN_SCORE])

    def _make_pkg_root_import(self, score_path: str) -> str:
        # str = .score/addr/tx_hash
        # str = /addr/tx_hash
        # arr = str.split('/')
        # arr = [addr, tx_hash]
        # '.'.join -> .addr.tx_hash
        # str[1:] = addr.tx_hash
        score_path = score_path.replace(self.score_root_path, "", 1)
        return '.'.join(score_path.split('/'))[1:]
