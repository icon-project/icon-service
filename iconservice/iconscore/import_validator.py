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


IMPORT_STAR = 84
IMPORT_NAME = 108
IMPORT_FROM = 109
IMPORT_TABLE = [IMPORT_STAR, IMPORT_NAME, IMPORT_FROM]

LOAD_BUILD_CLASS = 71

CODE_ATTR = 'co_code'

ICONSERVICE = 'iconservice'
ICONSERVICE_BASE_ADDRESS = 'iconservice.base.address'
ICONSERVICE_BASE_EXCEPTION = 'iconservice.base.exception'
ICONSERVICE_ICONSCORE_ICON_CONTAINER_DB = 'iconservice.iconscore.icon_container_db'
ICONSERVICE_ICONSCORE_ICON_SCORE_BASE = 'iconservice.icon_score_base'
ICONSERVICE_ICONSCORE_ICON_SCORE_BASE2 = 'iconservice.icon_score_base2'
ICONCOMMONS_LOGGER = 'iconcommons.logger'
INSPECT = 'inspect'
FUNC_TOOLS = 'functools'
ABC = 'abc'

WHITE_IMPORT_LIST = \
    {
        ICONSERVICE: [],
        ICONSERVICE_BASE_ADDRESS: ['Address', 'ZERO_SCORE_ADDRESS'],
        ICONSERVICE_BASE_EXCEPTION: ['IconScoreException'],
        ICONSERVICE_ICONSCORE_ICON_CONTAINER_DB: ['VarDB', 'DictDB', 'ArrayDB'],
        ICONSERVICE_ICONSCORE_ICON_SCORE_BASE: ['interface', 'eventlog', 'external', 'payable', 'IconScoreBase'],
        ICONSERVICE_ICONSCORE_ICON_SCORE_BASE2: ['InterfaceScore'],
        ICONCOMMONS_LOGGER: ['Logger'],
        INSPECT: ['isfunction'],
        FUNC_TOOLS: ['wraps'],
        ABC: ['ABCMeta', 'abstractmethod', 'ABC']
    }


class ImportValidator(object):
    PREV_IMPORT_NAME = None
    PREV_LOAD_BUILD_CLASS = None
    CUSTOM_IMPORT_LIST = []

    @staticmethod
    def validator(parent_imp_path: str, parent_imp: str) -> callable:
        ImportValidator.PREV_IMPORT_NAME = None

        ImportValidator.CUSTOM_IMPORT_LIST = ImportValidator._make_custom_import_list(parent_imp_path)

        for imp in ImportValidator.CUSTOM_IMPORT_LIST:
            full_name = ''.join((parent_imp, '.', imp))
            spec = importlib.util.find_spec(full_name)
            code = spec.loader.get_code(full_name)
            ImportValidator._validate_import_from_code(code)
            ImportValidator._validate_import_from_const(code.co_consts)

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
    def _validate_import_from_code(code):
        if not hasattr(code, CODE_ATTR):
            return

        byte_code_list = [x for x in code.co_code]

        for index in range(0, int(len(byte_code_list)), 2):
            key = byte_code_list[index]
            value = byte_code_list[index + 1]
            ImportValidator._validate_import(key, value, code.co_names)

    @staticmethod
    def _validate_import_from_const(co_consts: tuple):
        for co_const in co_consts:
            if not hasattr(co_const, CODE_ATTR):
                continue
            ImportValidator._validate_import_from_code(co_const)
            ImportValidator._validate_import_from_const(co_const.co_consts)

    @staticmethod
    def _validate_import(key: int, value: int, co_names: tuple):
        if key not in IMPORT_TABLE:
            return

        if key == IMPORT_NAME:
            import_name = co_names[value]
            ImportValidator.PREV_IMPORT_NAME = import_name
            if import_name not in WHITE_IMPORT_LIST:
                if not ImportValidator._is_contain_custom_import(import_name):
                    raise ServerErrorException(f'invalid import '
                                               f'import_name: {import_name}')
        elif key == IMPORT_STAR:
            if ImportValidator.PREV_IMPORT_NAME not in WHITE_IMPORT_LIST:
                if not ImportValidator._is_contain_custom_import(ImportValidator.PREV_IMPORT_NAME):
                    raise ServerErrorException(f'invalid import '
                                               f'import_name: {ImportValidator.PREV_IMPORT_NAME}')
        elif key == IMPORT_FROM:
            if ImportValidator.PREV_IMPORT_NAME in WHITE_IMPORT_LIST:
                from_list = WHITE_IMPORT_LIST[ImportValidator.PREV_IMPORT_NAME]
                if co_names[value] not in from_list:
                    raise ServerErrorException(f'invalid import '
                                               f'import_name: {ImportValidator.PREV_IMPORT_NAME}')
            elif ImportValidator._is_contain_custom_import(ImportValidator.PREV_IMPORT_NAME):
                pass
            else:
                raise ServerErrorException(f'invalid import '
                                           f'import_name: {ImportValidator.PREV_IMPORT_NAME}')

    @staticmethod
    def _is_contain_custom_import(import_name: str) -> bool:
        for custom_import in ImportValidator.CUSTOM_IMPORT_LIST:
            import_list = custom_import.split('.')
            if import_list is not None:
                for imp in import_list:
                    if import_name == imp:
                        return True
        return False
