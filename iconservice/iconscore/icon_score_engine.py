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
from ..base.exception import IconScoreException
from ..base.type_converter import TypeConverter
from ..logger import Logger
from .icon_score_context import ContextContainer
from .icon_score_context import IconScoreContext, call_method, call_fallback
from .icon_score_info_mapper import IconScoreInfoMapper
from .icon_score_deployer import IconScoreDeployer

from typing import TYPE_CHECKING, Optional, Callable

if TYPE_CHECKING:
    from ..icx.icx_storage import IcxStorage


class IconScoreEngine(ContextContainer):
    """Calls external functions provided by each IconScore
    """

    def __init__(self,
                 icx_storage: 'IcxStorage',
                 icon_score_info_mapper: 'IconScoreInfoMapper',
                 icon_score_deployer: 'IconScoreDeployer') -> None:
        """Constructor

        :param icx_storage: Get IconScore owner info from icx_storage
        :param icon_score_info_mapper:
        """
        super().__init__()

        self.__icx_storage = icx_storage
        self.__icon_score_info_mapper = icon_score_info_mapper
        self.__icon_score_deployer = icon_score_deployer

        self._Task = namedtuple(
            'Task',
            ('block', 'tx', 'msg', 'icon_score_address', 'data_type', 'data'))
        self._deferred_tasks = []

    def invoke(self,
               context: 'IconScoreContext',
               icon_score_address: 'Address',
               data_type: str,
               data: dict) -> None:
        """Handle calldata contained in icx_sendTransaction message

        :param icon_score_address:
        :param context:
        :param data_type:
        :param data: calldata
        """

        if data_type == 'call':
            self._call(context, icon_score_address, data)
        elif data_type == 'install' or data_type == 'update':
            self._deploy_on_invoke(context, icon_score_address, data)
            self._put_task(context, icon_score_address, data_type, data)
        else:
            self._fallback(context, icon_score_address)

    def query(self,
              context: IconScoreContext,
              icon_score_address: Address,
              data_type: str,
              data: dict) -> object:
        """Execute an external method of iconscore without state changing

        Handles messagecall of icx_call
        """

        if data_type == 'call':
            return self._call(context, icon_score_address, data)
        else:
            raise IconScoreException(
                f'Invalid data type ({data_type})')

    def get_score_api(self,
                      context: 'IconScoreContext',
                      icon_score_address: 'Address') -> object:
        """Handle get score api

        :param context:
        :param icon_score_address:
        """

        try:
            self._put_context(context)

            icon_score = self.__icon_score_info_mapper.get_icon_score(
                icon_score_address)
            if icon_score is None:
                raise IconScoreException(
                    f'IconScore({icon_score_address}) not found')

            return icon_score.get_api()
        finally:
            self._delete_context(context)

    def _put_task(self,
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

    def _call(self,
              context: 'IconScoreContext',
              icon_score_address: 'Address',
              data: dict) -> object:
        """Handle jsonrpc including both invoke and query

        :param context:
        :param icon_score_address:
        :param data: data to call the method of score
        """
        method: str = data['method']
        kw_params: dict = data['params']

        try:
            self._put_context(context)

            icon_score = self.__icon_score_info_mapper.get_icon_score(
                icon_score_address)
            if icon_score is None:
                raise IconScoreException(
                    f'IconScore({icon_score_address}) not found')
            return call_method(icon_score=icon_score, func_name=method, kw_params=kw_params)
        finally:
            self._delete_context(context)

    def _fallback(self,
                  context: 'IconScoreContext',
                  icon_score_address: 'Address'):
        """When an IconScore receives some coins and calldata is None,
        fallback function is called.

        :param icon_score_address:
        """

        try:
            self._put_context(context)
            icon_score = self.__icon_score_info_mapper.get_icon_score(
                icon_score_address)
            call_fallback(icon_score)
        finally:
            self._delete_context(context)

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

            try:
                if data_type == 'install':
                    self._install_on_commit(context, icon_score_address, data)
                elif data_type == 'update':
                    self._update_on_commit(context, icon_score_address, data)
                # Invalid task.type has been already filtered in invoke()
            except BaseException as e:
                Logger.exception(e)
                
        self._deferred_tasks.clear()

    def _deploy_on_invoke(
            self, context: 'IconScoreContext',
            icon_score_address: 'Address',
            data: dict):
        content_type = data.get('contentType')

        if content_type == 'application/tbears':
            return
        elif content_type != 'application/zip':
            raise IconScoreException(
                f'Invalid content type ({content_type})')

        content = data.get('content')[2:]
        content_bytes = bytes.fromhex(content)

        self.__icon_score_deployer.deploy(
            icon_score_address, content_bytes,
            context.block.height, context.tx.index)

    def _install_on_commit(self,
                           context: Optional[IconScoreContext],
                           icon_score_address: Address,
                           data: dict) -> None:
        """Install an icon score on commit

        Owner check has been already done in IconServiceEngine
        - Install IconScore package file to file system

        """

        content_type = data.get('contentType')
        content = data.get('content')
        params = data.get('params', {})

        if content_type == 'application/tbears':
            self.__icon_score_info_mapper.delete_icon_score(icon_score_address)
            score_root_path = self.__icon_score_info_mapper.score_root_path
            target_path = path.join(score_root_path,
                                    icon_score_address.body.hex())
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
        db_exist = self.__icon_score_info_mapper.is_exist_db(icon_score_address)
        score = self.__icon_score_info_mapper.get_icon_score(icon_score_address)

        if not db_exist:
            self._call_on_init_of_score(
                context=context,
                on_init=score.on_install,
                params=params)

    def _update_on_commit(self,
                          context: Optional[IconScoreContext],
                          icon_score_address: Address,
                          data: dict) -> None:
        """Update an icon score

        Owner check has been already done in IconServiceEngine
        """
        raise NotImplementedError('Score update is not implemented')

    def _call_on_init_of_score(self,
                               context: 'IconScoreContext',
                               on_init: Callable[[dict], None],
                               params: dict) -> None:
        """on_init(on_init_type, params) of score is called
        only once when installed or updated

        :param context:
        :param on_init: score.on_install() or score.on_update()
        :param params: paramters passed to on_init()
        """

        annotations = TypeConverter.make_annotations_from_method(on_init)
        TypeConverter.convert_params(annotations, params)

        try:
            self._put_context(context)
            on_init(**params)
        finally:
            self._delete_context(context)

    def rollback(self) -> None:
        """It is called when the previous block has been canceled

        Rollback install, update or remove tasks cached in the previous block
        """
        self._deferred_tasks.clear()
