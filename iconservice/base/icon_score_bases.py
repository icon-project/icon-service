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

import inspect
import abc
from functools import wraps
from ..iconscore.icon_score_context import IconScoreContext
from ..database.db import IconServiceDatabase
from .exception import ExternalException, PayableException
from .message import Message

CONST_CLASS_EXTERNALS = '__externals'
CONST_EXTERNAL_FLAG = '__external_flag'


# score decorator는 반드시 최종 클래스에만 붙어야 한다.
# 상속 불가
# 클래스를 한번 감싸서 진행하는 것이기 때문에, 데코레이터 상속이 되버리면 미정의 동작이 발생
# TypeError: metaclass conflict: the metaclass of a derived class must be a (non-strict) subclass of the metaclasses of all its bases

def score(cls):
    setattr(cls, CONST_CLASS_EXTERNALS, dict())

    for c in inspect.getmro(cls):
        custom_funcs = [value for key, value in inspect.getmembers(c, predicate=inspect.isfunction) if not key.startswith('__')]
        external_funcs = {func.__name__: func for func in custom_funcs if hasattr(func, CONST_EXTERNAL_FLAG)}
        getattr(cls, CONST_CLASS_EXTERNALS).update(external_funcs)

    @wraps(cls)
    def __wrapper(*args, **kwargs):
        res = cls(*args, **kwargs)
        return res
    return __wrapper


def external(func):
    cls_name, func_name = str(func.__qualname__).split('.')

    if not inspect.isfunction(func):
        raise ExternalException("isn't function", func, cls_name)

    setattr(func, CONST_EXTERNAL_FLAG, 0)

    @wraps(func)
    def __wrapper(calling_obj: object, *args, **kwargs):

        if not (isinstance(calling_obj, IconScoreBase)):
            raise ExternalException('is Not derived of ContractBase', func_name, cls_name)

        res = func(calling_obj, *args, **kwargs)
        return res

    return __wrapper


def payable(func):
    cls_name, func_name = str(func.__qualname__).split('.')

    if not inspect.isfunction(func):
        raise PayableException("isn't function", func, cls_name)

    @wraps(func)
    def __wrapper(calling_obj: object, *args, **kwargs):

        if not (isinstance(calling_obj, IconScoreBase)):
            raise PayableException('is Not derived of ContractBase', func_name, cls_name)

        # 0 it's ok
        # if not context.msg.value > 0:
        #     raise PayableException('have to context.value > 0', func_name, cls_name)

        res = func(calling_obj, *args, **kwargs)
        return res

    return __wrapper


class IconScoreObject(abc.ABC):
    """ 오직 __init__ 파라미터 상속용
        이것이 필요한 이유는 super().__init__이 우리 예상처럼 부모, 자식일 수 있으나 다중상속일때는 조금 다르게 흘러간다.
        class.__mro__로 하기때문에 다음과 같이 init에 매개변수를 받게 자유롭게 하려면 다음처럼 래핑 클래스가 필요하다.
        ex)최상위1 상위1 부모1 상위2 부모 object 이렇게 흘러간다 보통..
        물론 기본 __init__이 매개변수가 없기때문에 매개변수가 필요없다면 다음은 필요 없다.
    """

    def __init__(self, *args, **kwargs) -> None:
        pass

    def genesis_init(self, *args, **kwargs) -> None:
        pass


class IconScoreBase(IconScoreObject):

    @abc.abstractmethod
    def genesis_init(self, *args, **kwargs) -> None:
        super().genesis_init(*args, **kwargs)

    @abc.abstractmethod
    def __init__(self, db: IconServiceDatabase, *args, **kwargs) -> None:
        super().__init__(db, *args, **kwargs)
        self.__context = None

        if not self.get_api():
            raise ExternalException('empty abi! have to position decorator(@init_abi) above class definition',
                                    '__init__', str(type(self)))

    @classmethod
    def get_api(cls) -> dict:
        if not hasattr(cls, CONST_CLASS_EXTERNALS):
            return dict()

        return dict(getattr(cls, CONST_CLASS_EXTERNALS))

    def call_method(self, func_name: str, *args, **kwargs):

        if func_name not in self.get_api():
            raise ExternalException(f"can't call", func_name, type(self).__name__)

        score_func = getattr(self, func_name)
        return score_func(*args, **kwargs)

    def set_context(self, context: IconScoreContext) -> None:
        self.__context = context

    @property
    def msg(self) -> Message:
        return self.__context.msg
