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
import os

from ..base.exception import ServerErrorException

CODE_ATTR = 'co_code'
CODE_NAMES_ATTR = 'co_names'

BLACKLIST_RESERVED_KEYWORD = ['exec', 'eval', 'compile']

# cpython
IMPORT_STAR = 84
IMPORT_NAME = 108
IMPORT_FROM = 109
IMPORT_TABLE = [IMPORT_STAR, IMPORT_NAME, IMPORT_FROM]

LOAD_BUILD_CLASS = 71


class ScorePackageValidator(object):
    WHITELIST_IMPORT = {}
    CUSTOM_IMPORT_LIST = []
    PREV_IMPORT_NAME = None
    PREV_LOAD_BUILD_CLASS = None

    @staticmethod
    def execute(whitelist_table: dict,
                pkg_root_path: str,
                pkg_root_package: str) -> callable:

        ScorePackageValidator.PREV_IMPORT_NAME = None
        ScorePackageValidator.WHITELIST_IMPORT = whitelist_table
        ScorePackageValidator.CUSTOM_IMPORT_LIST = ScorePackageValidator._make_custom_import_list(pkg_root_path)

        # in order for the new module to be noticed by the import system
        importlib.invalidate_caches()

        for imp in ScorePackageValidator.CUSTOM_IMPORT_LIST:
            full_name = ''.join((pkg_root_package, '.', imp))
            spec = importlib.util.find_spec(full_name)
            code = spec.loader.get_code(full_name)
            ScorePackageValidator._validate_import_from_code(code)
            ScorePackageValidator._validate_import_from_const(code.co_consts)
            ScorePackageValidator._validate_blacklist_keyword_from_names(code.co_names)

    @staticmethod
    def _make_custom_import_list(pkg_root_path: str) -> list:
        tmp_list = []
        for root_path, _, files in os.walk(pkg_root_path):
            for file in files:
                file_name, extension = os.path.splitext(file)
                if extension != '.py':
                    continue
                sub_pkg_path = os.path.relpath(root_path, pkg_root_path)
                if sub_pkg_path == '.':
                    pkg_path = file_name
                else:
                    # sub_package
                    sub_pkg_path = sub_pkg_path.replace('/', '.')
                    pkg_path = ''.join((sub_pkg_path, '.', file_name))
                tmp_list.append(pkg_path)
        return tmp_list

    @staticmethod
    def _validate_blacklist_keyword_from_names(co_names: tuple):
        for co_name in co_names:
            if co_name in BLACKLIST_RESERVED_KEYWORD:
                raise ServerErrorException(f'invalid blacklist keyword: {co_name}')

    @staticmethod
    def _validate_import_from_code(code):
        if not hasattr(code, CODE_ATTR):
            return

        byte_code_list = [x for x in code.co_code]

        tmp_stack = []
        for index, code_index in enumerate(range(0, int(len(byte_code_list)), 2)):
            key = byte_code_list[code_index]
            value = byte_code_list[code_index + 1]
            tmp_stack.append((key, value))
            ScorePackageValidator._validate_import(index, tmp_stack, code.co_names, code.co_consts)

    @staticmethod
    def _validate_import_from_const(co_consts: tuple):
        for co_const in co_consts:
            if not hasattr(co_const, CODE_ATTR):
                continue
            ScorePackageValidator._validate_import_from_code(co_const)
            ScorePackageValidator._validate_import_from_const(co_const.co_consts)
            if hasattr(co_const, CODE_NAMES_ATTR):
                ScorePackageValidator._validate_blacklist_keyword_from_names(co_const.co_names)

    @staticmethod
    def _validate_import(current_index: int, stack_list: list, co_names: tuple, co_consts: tuple):
        key, value = stack_list[current_index]
        if key not in IMPORT_TABLE:
            return

        # import name
        if key == IMPORT_NAME:
            # use 0, 2 indexed values
            # 1 indexed valude is class_name
            # <class 'list'>: [(100, 0), (100, 1), (108, 0)]
            _, level_key = stack_list[current_index - 2]
            level = co_consts[level_key]

            if level > 0:
                return

            import_name = co_names[value]
            if import_name not in ScorePackageValidator.WHITELIST_IMPORT:
                raise ServerErrorException(f'invalid import '
                                           f'import_name: {import_name}')
        elif key == IMPORT_FROM:
            # use 0, 2, 3 indexed values
            # <class 'list'>: [(100, 0), (100, 1), (108, 0), (109, 1)]
            _, level_key = stack_list[current_index - 3]
            level = co_consts[level_key]

            if level > 0:
                return

            _, import_from_index = stack_list[current_index - 1]
            import_name = co_names[value]
            import_from = co_names[import_from_index]

            # duplicated function, but have to check
            # we can't check about only import situation
            if import_from not in ScorePackageValidator.WHITELIST_IMPORT:
                raise ServerErrorException(f'invalid import '
                                           f'import_from: {import_from} import_name: {import_name}')
            elif '*' not in ScorePackageValidator.WHITELIST_IMPORT[import_from] and \
                    import_name not in ScorePackageValidator.WHITELIST_IMPORT[import_from]:
                raise ServerErrorException(f'invalid import '
                                           f'import_name: {import_name}')
        elif key == IMPORT_STAR:
            # use 0, 2, 3 indexed values
            # 1 indexed valude is *
            # <class 'list'>: [(100, 0), (100, 1), (108, 0), (84, 0)]
            _, level_key = stack_list[current_index - 3]
            level = co_consts[level_key]

            if level > 0:
                return

            _, import_name_index = stack_list[current_index - 1]
            import_from = co_names[import_name_index]

            if import_from not in ScorePackageValidator.WHITELIST_IMPORT:
                raise ServerErrorException(f'invalid import '
                                           f'import_name: {import_from}')
