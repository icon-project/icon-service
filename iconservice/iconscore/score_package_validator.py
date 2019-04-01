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
import os

from ..base.exception import IllegalFormatException

CODE_ATTR = 'co_code'
CODE_NAMES_ATTR = 'co_names'

BLACKLIST_RESERVED_KEYWORD = ['exec', 'eval', 'compile', '__import__']

LOAD_CONST = 100
IMPORT_STAR = 84
IMPORT_NAME = 108
IMPORT_FROM = 109


class ScorePackageValidator(object):
    WHITELIST_IMPORT = {}
    CUSTOM_IMPORT_LIST = []

    @staticmethod
    def execute(whitelist_table: dict,
                pkg_root_path: str,
                pkg_root_package: str) -> callable:

        ScorePackageValidator.WHITELIST_IMPORT = whitelist_table
        ScorePackageValidator.CUSTOM_IMPORT_LIST = ScorePackageValidator._make_custom_import_list(pkg_root_path)

        # in order for the new module to be noticed by the import system
        importlib.invalidate_caches()

        for imp in ScorePackageValidator.CUSTOM_IMPORT_LIST:
            full_name = f'{pkg_root_package}.{imp}'

            spec = importlib.util.find_spec(full_name)
            code = spec.loader.get_code(full_name)

            ScorePackageValidator._validate_import_from_code(code)
            ScorePackageValidator._validate_import_from_const(code.co_consts)
            ScorePackageValidator._validate_blacklist_keyword_from_names(code.co_names)

    @staticmethod
    def _make_custom_import_list(pkg_root_path: str) -> list:
        tmp_list = []
        for dirpath, _, filenames in os.walk(pkg_root_path):
            for file in filenames:
                file_name, extension = os.path.splitext(file)
                if extension != '.py':
                    continue
                sub_pkg_path = os.path.relpath(dirpath, pkg_root_path)
                if sub_pkg_path == '.':
                    pkg_path = file_name
                else:
                    # sub_package
                    sub_pkg_path = sub_pkg_path.replace('/', '.')
                    pkg_path = f'{sub_pkg_path}.{file_name}'
                tmp_list.append(pkg_path)
        return tmp_list

    @staticmethod
    def _validate_blacklist_keyword_from_names(co_names: tuple):
        for co_name in co_names:
            if co_name in BLACKLIST_RESERVED_KEYWORD:
                raise IllegalFormatException(f'Blacklist keyword found: {co_name}')

    @staticmethod
    def _validate_import_from_code(code):
        if not hasattr(code, CODE_ATTR):
            return

        byte_code_list = [x for x in code.co_code]

        length_byte_code_list = len(byte_code_list)
        for code_index in range(0, length_byte_code_list, 2):
            key = byte_code_list[code_index]
            if IMPORT_NAME == key:
                ScorePackageValidator._validate_import(code_index, byte_code_list, code.co_names, code.co_consts)

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
    def _validate_import(current_index: int, byte_code_list: list, co_names: tuple, co_consts: tuple):
        """ example
        20 LOAD_CONST               0 (0)
        22 LOAD_CONST               3 (('pack', 'unpack', 'iter_unpack'))
        24 IMPORT_NAME              1 (struct)
        26 IMPORT_FROM              3 (pack)
        28 STORE_NAME               3 (pack)
        30 IMPORT_FROM              4 (unpack)
        32 STORE_NAME               4 (unpack)
        34 IMPORT_FROM              5 (iter_unpack)
        36 STORE_NAME               5 (iter_unpack)

        6 LOAD_CONST                0 (0)
        18 LOAD_CONST               2 (None)
        20 IMPORT_NAME              2 (os)
        22 STORE_NAME               2 (os)
        24 LOAD_CONST               0 (0)
        26 LOAD_CONST               2 (None)
        28 IMPORT_NAME              3 (json)
        30 STORE_NAME               3 (json)
        """

        from_list_op_code_key = byte_code_list[current_index - 2]
        level_op_code_key = byte_code_list[current_index - 4]
        if LOAD_CONST != from_list_op_code_key or LOAD_CONST != level_op_code_key:
            raise IllegalFormatException('Invalid import opcode')

        import_name_index = byte_code_list[current_index + 1]
        from_list_index = byte_code_list[current_index - 1]
        level_index = byte_code_list[current_index - 3]

        import_name = co_names[import_name_index]
        from_list = co_consts[from_list_index]
        level = co_consts[level_index]

        if level > 0:
            return

        if import_name not in ScorePackageValidator.WHITELIST_IMPORT:
            raise IllegalFormatException(f'Invalid import name: {import_name}')

        if from_list is None:
            # only using import
            return
        else:
            next_op_code_key = byte_code_list[current_index + 2]
            if IMPORT_STAR == next_op_code_key:
                # import_star
                if from_list[0] != '*':
                    raise IllegalFormatException(f'Invalid star import: {import_name}')
            elif IMPORT_FROM == next_op_code_key:
                # import from
                for import_from in from_list:
                    if '*' not in ScorePackageValidator.WHITELIST_IMPORT[import_name] and \
                            import_from not in ScorePackageValidator.WHITELIST_IMPORT[import_name]:
                        raise IllegalFormatException(f'Invalid import name: {import_name}')
            else:
                raise IllegalFormatException('Invalid import opcode')
