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

from .icon_score_context import ContextGetter
from ..database.db import IconScoreDatabase
from ..base.exception import ExternalException, PayableException
from ..base.message import Message
from ..base.transaction import Transaction
from ..base.address import Address

CONST_CLASS_EXTERNALS = '__externals'
CONST_EXTERNAL_FLAG = '__external_flag'
CONST_CLASS_PAYABLES = '__payables'
CONST_PAYABLE_FLAG = '__payable_flag'

# score decorator는 반드시 최종 클래스에만 붙어야 한다.
# 상속 불가
# 클래스를 한번 감싸서 진행하는 것이기 때문에, 데코레이터 상속이 되버리면 미정의 동작이 발생
# TypeError: metaclass conflict: the metaclass of a derived class must be a (non-strict) subclass of the metaclasses of all its bases


def score(cls):
    setattr(cls, CONST_CLASS_EXTERNALS, dict())
    setattr(cls, CONST_CLASS_PAYABLES, dict())

    for c in inspect.getmro(cls):
        custom_funcs = [value for key, value in inspect.getmembers(c, predicate=inspect.isfunction) if not key.startswith('__')]
        external_funcs = {func.__name__: func for func in custom_funcs if hasattr(func, CONST_EXTERNAL_FLAG)}
        payable_funcs = {func.__name__: func for func in custom_funcs if hasattr(func, CONST_PAYABLE_FLAG)}
        if external_funcs:
            getattr(cls, CONST_CLASS_EXTERNALS).update(external_funcs)
        if payable_funcs:
            getattr(cls, CONST_CLASS_PAYABLES).update(payable_funcs)

    @wraps(cls)
    def __wrapper(*args, **kwargs):
        res = cls(*args, **kwargs)
        return res
    return __wrapper


def external(readonly=False):
    def __inner_func(func):
        cls_name, func_name = str(func.__qualname__).split('.')
        if not inspect.isfunction(func):
            raise ExternalException("isn't function", func, cls_name)

        if func_name == 'fallback':
            raise ExternalException("can't locate external to this func", func_name, cls_name)

        setattr(func, CONST_EXTERNAL_FLAG, int(readonly))

        @wraps(func)
        def __wrapper(calling_obj: object, *args, **kwargs):
            if not (isinstance(calling_obj, IconScoreBase)):
                raise ExternalException('is Not derived of ContractBase', func_name, cls_name)
            res = func(calling_obj, *args, **kwargs)
            return res
        return __wrapper
    return __inner_func


def payable(func):
    cls_name, func_name = str(func.__qualname__).split('.')
    if not inspect.isfunction(func):
        raise PayableException("isn't function", func, cls_name)

    if hasattr(func, CONST_EXTERNAL_FLAG) and getattr(func, CONST_EXTERNAL_FLAG) > 0:
            raise PayableException("have to non readonly", func, cls_name)

    setattr(func, CONST_PAYABLE_FLAG, 0)

    @wraps(func)
    def __wrapper(calling_obj: object, *args, **kwargs):

        if not (isinstance(calling_obj, IconScoreBase)):
            raise PayableException('is Not derived of ContractBase', func_name, cls_name)
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


class IconScoreBase(IconScoreObject, ContextGetter):

    @abc.abstractmethod
    def genesis_init(self, *args, **kwargs) -> None:
        super().genesis_init(*args, **kwargs)

    @abc.abstractmethod
    def __init__(self, db: IconScoreDatabase, owner: Address) -> None:
        super().__init__(db, owner)
        self.__db = db
        self.__owner = owner
        self.__address = db.address

        if not self.get_api():
            raise ExternalException(
                'empty abi! have to position decorator(@init_abi) above class definition',
                '__init__', str(type(self)))

    @classmethod
    def get_api(cls) -> dict:
        return cls.__get_attr_dict(CONST_CLASS_EXTERNALS)

    @classmethod
    def __get_attr_dict(cls, attr: str) -> dict:
        if not hasattr(cls, attr):
            return dict()
        return getattr(cls, attr)

    def call_method(self, func_name: str, *args, **kwargs):

        if func_name not in self.get_api():
            raise ExternalException(f"can't external call", func_name, type(self).__name__)

        self.__check_payable(func_name, self.__get_attr_dict(CONST_CLASS_PAYABLES))

        score_func = getattr(self, func_name)
        return score_func(*args, **kwargs)

    def __call_fallback(self):
        func_name = 'fallback'
        payable_dict = self.__get_attr_dict(CONST_CLASS_PAYABLES)
        self.__check_payable(func_name, payable_dict)

        score_func = getattr(self, func_name)
        score_func()

    def __check_payable(self, func_name: str, payable_dict: dict):
        if func_name not in payable_dict:
            if self.msg.value > 0:
                raise PayableException(f"can't have msg.value", func_name, type(self).__name__)

    @property
    def msg(self) -> Message:
        return self._context.msg

    @property
    def address(self) -> Address:
        return self.__address

    @property
    def tx(self) -> Transaction:
        return self._context.tx

    @property
    def db(self) -> IconScoreDatabase:
        return self.__db

    @property
    def owner(self) -> Address:
        return self.__owner

    def call(self, addr_to: Address, func_name: str, *args, **kwargs):
        return self._context.call(addr_to, func_name, *args, **kwargs)

    def transfer(self, addr_to: Address, amount: int):
        return self._context.transfer(self.__address, addr_to, amount)

    def send(self, addr_to: Address, amount: int):
        return self._context.send(self.__address, addr_to, amount)

    def revert(self) -> None:
        return self._context.revert(self.__address)
