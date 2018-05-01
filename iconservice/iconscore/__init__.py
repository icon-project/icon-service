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


import threading

from ..base.exception import ExceptionCode, IconException


_thread_local_data = threading.local()


class ContextContainer(object):
    """ContextContainer mixin
    
    Every class inherit ContextContainer can share IconScoreContext instance
    in the current thread.
    """
    def _get_context(self) -> 'IconScoreContext':
        return getattr(_thread_local_data, 'context', None)

    def _put_context(self, value: 'IconScoreContext') -> None:
        setattr(_thread_local_data, 'context', value)

    def _delete_context(self, context: 'IconScoreContext') -> None:
        """Delete the context of the current thread
        """
        if context is not _thread_local_data.context:
            raise IconException(
                ExceptionCode.INTERNAL_ERROR,
                'Critical error in context management')

        del _thread_local_data.context


class ContextGetter(object):
    """The class which refers to IconScoreContext should inherit ContextGetter
    """
    @property
    def _context(self):
        return getattr(_thread_local_data, 'context', None)
