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


_thread_local_data = threading.local()

class ContextContainer(object):
    """ContextContainer mixin
    
    Every class inherit ContextContainer can share IconScoreContext instance
    in the current thread.
    """
    def get_context(self) -> 'IconScoreContext':
        return getattr(_thread_local_data, 'context', None)

    def put_context(self, value: 'IconScoreContext') -> None:
        _thread_local_data.context = value


class ContextGetter(object):
    @property
    def _context(self):
        return getattr(_thread_local_data, 'context', None)
