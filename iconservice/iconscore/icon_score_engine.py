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
"""IconScoreEngine module
"""


from collections import namedtuple
from os import path, symlink, makedirs

from ..base.address import Address
from ..base.exception import ExceptionCode, IconException, check_exception
from .icon_score_context import ContextContainer
from .icon_score_context import IconScoreContext, call_method, call_fallback
from .icon_score_info_mapper import IconScoreInfoMapper
from ..utils.type_converter import TypeConverter

from typing import TYPE_CHECKING, Optional
if TYPE_CHECKING:
    from ..icx.icx_storage import IcxStorage
    from .icon_score_base import IconScoreBase


class IconScoreEngine(ContextContainer):
    """Calls external functions provided by each IconScore
    """

    def __init__(self,
                 icx_storage: 'IcxStorage',
                 icon_score_info_mapper: IconScoreInfoMapper) -> None:
        """Constructor

        :param icx_storage: Get IconScore owner info from icx_storage
        :param icon_score_info_mapper:
        """
        super().__init__()

        self.__icx_storage = icx_storage
        self.__icon_score_info_mapper = icon_score_info_mapper

        self._Task = namedtuple(
            'Task',
            ('block', 'tx', 'msg', 'icon_score_address', 'data_type', 'data'))
        self._deferred_tasks = []

    @check_exception
    def invoke(self,
               context: IconScoreContext,
               icon_score_address: Address,
               data_type: str,
               data: dict) -> None:
        """Handle calldata contained in icx_sendTransaction message

        :param icon_score_address:
        :param context:
        :param data_type:
        :param data: calldata
        """

        if data_type == 'call':
                self.__call(context, icon_score_address, data)
        elif data_type == 'install' or data_type == 'update':
                self.__put_task(context, icon_score_address, data_type, data)
        else:
            raise IconException(
                ExceptionCode.INVALID_PARAMS,
                f'Invalid data type ({data_type})')

    @check_exception
    def query(self,
              context: IconScoreContext,
              icon_score_address: Address,
              data_type: str,
              data: dict) -> object:
        """Execute an external method of iconscore without state changing

        Handles messagecall of icx_call
        """

        if data_type == 'call':
            return self.__call(context, icon_score_address, data)
        else:
            raise IconException(
                ExceptionCode.INVALID_PARAMS,
                f'Invalid data type ({data_type})')

    def __put_task(self,
                   context: 'IconScoreContext',
                   icon_score_address: Address,
                   data_type: str,
                   data: dict) -> None:
        """Queue a deferred task to install, update or remove a score

        :param context:
        :param data_type:
        :param icon_score_address:
        :param data:
        """
        task = self._Task(
            block=context.block,
            tx=context.tx,
            msg=context.msg,
            icon_score_address=icon_score_address,
            data_type=data_type,
            data=data)
        self._deferred_tasks.append(task)

    def __call(self,
               context: IconScoreContext,
               icon_score_address: Address,
               calldata: dict) -> object:
        """Handle jsonrpc

        :param icon_score_address:
        :param context:
        :param calldata:
        """
        method: str = calldata['method']
        kw_params: dict = calldata['params']

        try:
            self._put_context(context)
            icon_score = self.__icon_score_info_mapper.get_icon_score(icon_score_address)
            return call_method(icon_score=icon_score, func_name=method,
                               kw_params=self.__type_converter(icon_score, method, kw_params))
        finally:
            self._delete_context(context)

    @staticmethod
    def __type_converter(icon_score: 'IconScoreBase', func_name: str, kw_params: dict) -> dict:
        param_type_table = {}
        func_params = icon_score.get_api()[func_name].parameters

        for key, value in kw_params.items():
            param = func_params.get(key)
            if param:
                param_type = param.annotation
                if param_type is Address:
                    param_type_table[key] = TypeConverter.CONST_ADDRESS
                elif param_type is int:
                    param_type_table[key] = TypeConverter.CONST_INT
                elif param_type is str:
                    param_type_table[key] = TypeConverter.CONST_STRING
                elif param_type is bytes:
                    param_type_table[key] = TypeConverter.CONST_BYTES
                elif param_type is bool:
                    param_type_table[key] = TypeConverter.CONST_BOOL

        converter = TypeConverter(param_type_table)
        return converter.convert(kw_params, True)

    def __fallback(self, icon_score_address: Address):
        """When an IconScore receives some coins and calldata is None,
        fallback function is called.

        :param icon_score_address:
        """

        # TODO: Call fallback method of iconscore
        icon_score = self.__icon_score_info_mapper.get_icon_score(icon_score_address)
        call_fallback(icon_score)

    @check_exception
    def commit(self, context: 'IconScoreContext') -> None:
        """It is called when the previous block has been confirmed

        Execute a deferred tasks in queue (install, update or remove a score)

        Process Order
        - Install IconScore package file to file system
        - Load IconScore wrapper
        - Create Database
        - Create an IconScore instance with owner and database
        - Execute IconScoreBase.genesis_invoke() only if task.type is 'install'
        - Add IconScoreInfo to IconScoreInfoMapper
        - Write the owner of score to icx database

        """
        for task in self._deferred_tasks:
            context.block = task.block
            context.tx = task.tx
            context.msg = task.msg
            icon_score_address = task.icon_score_address
            data_type = task.data_type
            data = task.data

            if data_type == 'install':
                self.__install(context, icon_score_address, data)
            elif data_type == 'update':
                self.__update(context, icon_score_address, data)
            # Invalid task.type has been already filtered in invoke()

        self._deferred_tasks.clear()

    def __install(self,
                  context: Optional[IconScoreContext],
                  icon_score_address: Address,
                  data: dict) -> None:
        """Install an icon score

        Owner check has been already done in IconServiceEngine
        - Install IconScore package file to file system

        """
        content_type = data.get('content_type')
        content = data.get('content')

        if content_type == 'application/tbears':
            self.__icon_score_info_mapper.delete_icon_score(icon_score_address)
            score_root_path = self.__icon_score_info_mapper.score_root_path
            target_path = path.join(score_root_path, icon_score_address.body.hex())
            makedirs(target_path, exist_ok=True)
            target_path = path.join(
                target_path, f'{context.block.height}_{context.tx.index}')
            try:
                symlink(content, target_path, target_is_directory=True)
            except FileExistsError:
                pass
        else:
            pass

        self.__icx_storage.put_score_owner(context,
                                           icon_score_address,
                                           context.tx.origin)
        score = self.__icon_score_info_mapper.get_icon_score(icon_score_address)

        try:
            self._put_context(context)
            score.genesis_init()
        except Exception as e:
            print(e)
        finally:
            self._delete_context(context)

    def __update(self,
                 context: Optional[IconScoreContext],
                 icon_score_address: Address,
                 data: dict) -> None:
        """Update an icon score

        Owner check has been already done in IconServiceEngine
        """
        raise NotImplementedError('Score update is not implemented')

    def rollback(self) -> None:
        """It is called when the previous block has been canceled

        Rollback install, update or remove tasks cached in the previous block
        """
        self._deferred_tasks.clear()
