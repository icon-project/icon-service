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

from ..base.address import Address
from ..base.exception import ExceptionCode, IconException
from .icon_score_context import ContextContainer
from .icon_score_context import IconScoreContext, call_method, call_fallback
from .icon_score_info_mapper import IconScoreInfoMapper

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..icx.icx_storage import IcxStorage


class IconScoreEngine(ContextContainer):
    """Calls external functions provided by each IconScore
    """

    def __init__(self,
                 icx_storage: 'IcxStorage',
                 icon_score_info_mapper: IconScoreInfoMapper) -> None:
        """Constructor

        :param icx_storage: Get IconScore owner info from icx_storage
        :param icon_score_info_mapper:
        :param db_factory:
        """
        super().__init__()

        self.__icx_storage = icx_storage
        self.__icon_score_info_mapper = icon_score_info_mapper

        self._Task = namedtuple(
            'Task',
            ('type', 'address', 'owner', 'data', 'block_height', 'tx_index'))
        self._tasks = []

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
            self.__put_task(context, data_type, icon_score_address, data)
        else:
            raise IconException(
                ExceptionCode.INVALID_PARAMS,
                f'Invalid data type ({data_type})')

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
                   data_type: str,
                   icon_score_address: Address,
                   data: dict) -> None:
        """Queue a deferred task to install, update or remove a score

        :param context:
        :param data_type:
        :param icon_score_address:
        :param data:
        """
        task = self._Task(
            type=data_type,
            address=icon_score_address,
            owner=context.tx.origin,
            data=data,
            block_height=context.block.height,
            tx_index=context.tx.index
        )
        self._tasks.append(task)

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
        params: dict = calldata['params']

        try:
            self._put_context(context)
            icon_score = self.__icon_score_info_mapper.get_icon_score(icon_score_address)
            return call_method(icon_score=icon_score, func_name=method, *(), **params)
        finally:
            self._delete_context(context)

    def __fallback(self, icon_score_address: Address):
        """When an IconScore receives some coins and calldata is None,
        fallback function is called.

        :param icon_score_address:
        """

        # TODO: Call fallback method of iconscore
        icon_score = self.__icon_score_info_mapper.get_icon_score(icon_score_address)
        call_fallback(icon_score)

    def commit(self) -> None:
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

        :param context:
        """
        # If context is None, we assume that context type is GENESIS mode
        # Direct access to levelDB
        context = None

        for task in self._tasks:
            # TODO: install score package to 'address/block_height_tx_index' directory
            if task.type == 'install':
                self.__install(context, task)
            elif task.type == 'update':
                self.__update(context, task)
            # Invalid task.type has been already filtered in invoke()

        self._tasks.clear()

    def __install(self, context: IconScoreContext, task: namedtuple) -> None:
        """Install an icon score

        Owner check has been already done in IconServiceEngine
        - Install IconScore package file to file system

        """
        self.__icx_storage.put_score_owner(context, task.address, task.owner)
        score = self.__icon_score_info_mapper.get_icon_score(task.address)

        try:
            score.genesis_init(task.data)
        except Exception as e:
            print(e)

    def __update(self, context: IconScoreContext, task: namedtuple) -> None:
        """Update an icon score

        Owner check has been already done in IconServiceEngine
        """
        raise NotImplementedError('Score update is not implemented')

    def rollback(self) -> None:
        """It is called when the previous block has been canceled

        Rollback install, update or remove tasks cached in the previous block

        :param context:
        """
        self._tasks.clear()
