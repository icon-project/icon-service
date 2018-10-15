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
from os import walk

from ..base.exception import ServerErrorException

# cpython
IMPORT_STAR = 84
IMPORT_NAME = 108
IMPORT_FROM = 109
IMPORT_TABLE = [IMPORT_STAR, IMPORT_NAME, IMPORT_FROM]

LOAD_BUILD_CLASS = 71

CODE_ATTR = 'co_code'
CODE_NAMES_ATTR = 'co_names'

BLACKLIST_RESERVED_KEYWORD = ['exec', 'eval', 'compile']


class ScorePackageValidator(object):
    PREV_IMPORT_NAME = None
    PREV_LOAD_BUILD_CLASS = None
    WHITELIST_IMPORT = {}
    CUSTOM_IMPORT_LIST = []

    @staticmethod
    def execute(whitelist_table: dict, pkg_root_path: str, pkg_import_root: str) -> callable:
        ScorePackageValidator.PREV_IMPORT_NAME = None
        ScorePackageValidator.WHITELIST_IMPORT = whitelist_table
        ScorePackageValidator.CUSTOM_IMPORT_LIST = ScorePackageValidator._make_custom_import_list(pkg_root_path)

        # in order for the new module to be noticed by the import system
        importlib.invalidate_caches()

        for imp in ScorePackageValidator.CUSTOM_IMPORT_LIST:
            full_name = ''.join((pkg_import_root, '.', imp))
            spec = importlib.util.find_spec(full_name)
            code = spec.loader.get_code(full_name)

            # using Test AST Module
            # have to sandbox environment
            # because call compile function that codes

            # import ast
            # source = spec.loader.get_source(full_name)
            # mode = ast.parse(source)
            # for node in ast.walk(mode):
            #     if isinstance(node, ast.Import) or isinstance(node, ast.ImportFrom):
            #         if not ScorePackageValidator._is_contain_custom_import(node.module):
            #             if node.module not in ScorePackageValidator.WHITELIST_IMPORT:
            #                 raise ServerErrorException(f'invalid import '
            #                                            f'import_name: {node.module}')
            #     elif isinstance(node, ast.Name):
            #         if node.id in BLACKLIST_RESERVED_KEYWORD:
            #             raise ServerErrorException(f'invalid import '
            #                                        f'import_name: {node.module}')
            #     else:
            #         pass

            ScorePackageValidator._validate_import_from_code(code)
            ScorePackageValidator._validate_import_from_const(code.co_consts)
            ScorePackageValidator._validate_blacklist_keyword_from_names(code.co_names)

    @staticmethod
    def _make_custom_import_list(pkg_root_path: str) -> list:
        tmp_list = []
        for root_path, _, files in walk(pkg_root_path):
            for file in files:
                if file.endswith('.py'):
                    file_name = file.replace('.py', '')
                    sub_pkg_path = root_path.replace(pkg_root_path, "")
                    if sub_pkg_path is not str():
                        sub_pkg_path = sub_pkg_path[1:]
                        pkg_path = ''.join((sub_pkg_path, '.', file_name))
                    else:
                        pkg_path = file_name
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

        for index in range(0, int(len(byte_code_list)), 2):
            key = byte_code_list[index]
            value = byte_code_list[index + 1]
            ScorePackageValidator._validate_import(key, value, code.co_names)

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
    def _validate_import(key: int, value: int, co_names: tuple):
        if key not in IMPORT_TABLE:
            return

        if key == IMPORT_NAME:
            import_name = co_names[value]
            ScorePackageValidator.PREV_IMPORT_NAME = import_name
            if import_name not in ScorePackageValidator.WHITELIST_IMPORT:
                if not ScorePackageValidator._is_contain_custom_import(import_name):
                    raise ServerErrorException(f'invalid import '
                                               f'import_name: {import_name}')
        elif key == IMPORT_STAR:
            if ScorePackageValidator.PREV_IMPORT_NAME not in ScorePackageValidator.WHITELIST_IMPORT:
                if not ScorePackageValidator._is_contain_custom_import(ScorePackageValidator.PREV_IMPORT_NAME):
                    raise ServerErrorException(f'invalid import '
                                               f'import_name: {ScorePackageValidator.PREV_IMPORT_NAME}')
        elif key == IMPORT_FROM:
            if ScorePackageValidator.PREV_IMPORT_NAME in ScorePackageValidator.WHITELIST_IMPORT:
                from_list = ScorePackageValidator.WHITELIST_IMPORT[ScorePackageValidator.PREV_IMPORT_NAME]
                if co_names[value] not in from_list:
                    raise ServerErrorException(f'invalid import '
                                               f'import_name: {ScorePackageValidator.PREV_IMPORT_NAME}')
            elif ScorePackageValidator._is_contain_custom_import(ScorePackageValidator.PREV_IMPORT_NAME):
                pass
            else:
                raise ServerErrorException(f'invalid import '
                                           f'import_name: {ScorePackageValidator.PREV_IMPORT_NAME}')

    @staticmethod
    def _is_contain_custom_import(import_name: str) -> bool:
        for custom_import in ScorePackageValidator.CUSTOM_IMPORT_LIST:
            if import_name == custom_import:
                return True
            else:
                import_list = custom_import.split('.')
                if import_list is not None:
                    for imp in import_list:
                        if import_name == imp:
                            return True
        return False

