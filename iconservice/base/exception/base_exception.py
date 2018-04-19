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

from exception_code import ExceptionCode


# 아이콘 서비스에서 사용하는 모든 예외는 다음을 상속받는다.
class IconServiceBaseException(BaseException):

    def __init__(self, message: str):
        self._message = message

    @property
    def message(self):
        return self._message


class IcxException(IconServiceBaseException):
    """Defines Icx Errors
    """

    def __init__(self, code: ExceptionCode, message: str = None) -> None:
        if message is None or message == '':
            message = str(code)

        super(IcxException, self).__init__(message)
        self._code = code

    @property
    def code(self):
        return self._code

    def __str__(self):
        return f'msg: {self.message} code: {self.code}'


class ScoreBaseException(IconServiceBaseException):
    def __init__(self, message: str, func_name: str, cls_name: str) -> None:
        super(ScoreBaseException, self).__init__(message)
        self._func_name = func_name
        self._cls_name = cls_name

    @property
    def func_name(self):
        return self._func_name

    @property
    def cls_name(self):
        return self._cls_name

    def __str__(self):
        return f'msg: {self.message} func: {self.func_name} cls: {self.cls_name}'
