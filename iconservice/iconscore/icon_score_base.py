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
import warnings
from inspect import isfunction, getmembers, signature
from abc import ABC, ABCMeta, abstractmethod
from functools import partial

from iconservice.iconscore.icon_score_step import StepType
from .icon_score_context import IconScoreContextType
from .icon_score_context import ContextGetter
from ..database.db import IconScoreDatabase, DatabaseObserver
from ..base.exception import *
from ..base.message import Message
from ..base.transaction import Transaction
from ..base.address import Address
from ..base.block import Block

from typing import TYPE_CHECKING, TypeVar, Type, Callable
if TYPE_CHECKING:
    from .icon_score_context import IconScoreContext

T = TypeVar('T')

CONST_CLASS_EXTERNALS = '__externals'
CONST_CLASS_PAYABLES = '__payables'

CONST_BIT_FLAG = '__bit_flag'


@unique
class ConstBitFlag(IntEnum):
    NonFlag = 0
    ReadOnly = 1
    External = 2
    Payable = 4
    EventLog = 8
    Interface = 16


CONST_BIT_FLAG_EXTERNAL_READONLY = ConstBitFlag.ReadOnly | ConstBitFlag.External

STR_IS_NOT_CALLABLE = 'is not callable'
FORMAT_IS_NOT_FUNCTION_OBJECT = "isn't function object: {}, cls: {}"
FORMAT_IS_NOT_DERIVED_OF_OBJECT = "isn't derived of {}"
FORMAT_DECORATOR_DUPLICATED = "can't duplicated {} decorator func: {}, cls: {}"


def interface(func):
    cls_name, func_name = str(func.__qualname__).split('.')
    if not isfunction(func):
        raise InterfaceException(FORMAT_IS_NOT_FUNCTION_OBJECT.format(func, cls_name))

    if getattr(func, CONST_BIT_FLAG, 0) & ConstBitFlag.Interface:
        raise IconScoreException(FORMAT_DECORATOR_DUPLICATED.format('interface', func_name, cls_name))

    bit_flag = getattr(func, CONST_BIT_FLAG, 0) | ConstBitFlag.Interface
    setattr(func, CONST_BIT_FLAG, bit_flag)

    @wraps(func)
    def __wrapper(calling_obj: object, *args, **kwargs):
        if not isinstance(calling_obj, InterfaceScore):
            raise InterfaceException(FORMAT_IS_NOT_DERIVED_OF_OBJECT.format(InterfaceScore.__name__))

        call_method = getattr(calling_obj, '_InterfaceScore__call_method')
        ret = call_method(func_name, args, kwargs)
        return ret

    return __wrapper


def eventlog(func):
    cls_name, func_name = str(func.__qualname__).split('.')
    if not isfunction(func):
        raise EventLogException(FORMAT_IS_NOT_FUNCTION_OBJECT.format(func, cls_name))

    if getattr(func, CONST_BIT_FLAG, 0) & ConstBitFlag.EventLog:
        raise IconScoreException(FORMAT_DECORATOR_DUPLICATED.format('eventlog', func_name, cls_name))

    bit_flag = getattr(func, CONST_BIT_FLAG, 0) | ConstBitFlag.EventLog
    setattr(func, CONST_BIT_FLAG, bit_flag)

    @wraps(func)
    def __wrapper(calling_obj: object, *args, **kwargs):
        if not (isinstance(calling_obj, IconScoreBase)):
            raise EventLogException(FORMAT_IS_NOT_DERIVED_OF_OBJECT.format(IconScoreBase.__name__))

        call_method = getattr(calling_obj, '_IconScoreBase__write_eventlog')
        ret = call_method(func_name, args, kwargs)
        return ret

    return __wrapper


def external(func=None, *, readonly=False):
    if func is None:
        return partial(external, readonly=readonly)

    cls_name, func_name = str(func.__qualname__).split('.')
    if not isfunction(func):
        raise IconScoreException(FORMAT_IS_NOT_FUNCTION_OBJECT.format(func, cls_name))

    if func_name == 'fallback':
        raise IconScoreException(f"can't locate external to this func func: {func_name}, cls: {cls_name}")

    if getattr(func, CONST_BIT_FLAG, 0) & ConstBitFlag.External:
        raise IconScoreException(FORMAT_DECORATOR_DUPLICATED.format('external', func_name, cls_name))

    bit_flag = getattr(func, CONST_BIT_FLAG, 0) | ConstBitFlag.External | int(readonly)
    setattr(func, CONST_BIT_FLAG, bit_flag)

    @wraps(func)
    def __wrapper(calling_obj: object, *args, **kwargs):
        if not (isinstance(calling_obj, IconScoreBase)):
            raise ExternalException(
                FORMAT_IS_NOT_DERIVED_OF_OBJECT.format(IconScoreBase.__name__), func_name, cls_name)
        res = func(calling_obj, *args, **kwargs)
        return res

    return __wrapper


def payable(func):
    cls_name, func_name = str(func.__qualname__).split('.')
    if not isfunction(func):
        raise IconScoreException(FORMAT_IS_NOT_FUNCTION_OBJECT.format(func, cls_name))

    if getattr(func, CONST_BIT_FLAG, 0) & ConstBitFlag.Payable:
        raise IconScoreException(FORMAT_DECORATOR_DUPLICATED.format('payable', func_name, cls_name))

    bit_flag = getattr(func, CONST_BIT_FLAG, 0) | ConstBitFlag.Payable
    setattr(func, CONST_BIT_FLAG, bit_flag)

    @wraps(func)
    def __wrapper(calling_obj: object, *args, **kwargs):

        if not (isinstance(calling_obj, IconScoreBase)):
            raise PayableException(
                FORMAT_IS_NOT_DERIVED_OF_OBJECT.format(IconScoreBase.__name__), func_name, cls_name)
        res = func(calling_obj, *args, **kwargs)
        return res

    return __wrapper


class InterfaceScoreMeta(ABCMeta):
    def __new__(mcs, name, bases, namespace, **kwargs):
        if ABC in bases:
            return super().__new__(mcs, name, bases, namespace, **kwargs)

        cls = super().__new__(mcs, name, bases, namespace, **kwargs)
        return cls


class InterfaceScore(ABC, metaclass=InterfaceScoreMeta):
    def __init__(self, addr_to: 'Address', call_func: callable):
        self.__addr_to = addr_to
        self.__call_func = call_func

    def __call_method(self, func_name: str, arg_list: list, kw_dict: dict):
        if self.__call_func is None:
            raise InterfaceException('self.__call_func is None')

        if callable(self.__call_func):
            self.__call_func(self.__addr_to, func_name, arg_list, kw_dict)
        else:
            raise InterfaceException(STR_IS_NOT_CALLABLE)


class IconScoreObject(ABC):
    """ 오직 __init__ 파라미터 상속용
        이것이 필요한 이유는 super().__init__이 우리 예상처럼 부모, 자식일 수 있으나 다중상속일때는 조금 다르게 흘러간다.
        class.__mro__로 하기때문에 다음과 같이 init에 매개변수를 받게 자유롭게 하려면 다음처럼 래핑 클래스가 필요하다.
        ex)최상위1 상위1 부모1 상위2 부모 object 이렇게 흘러간다 보통..
        물론 기본 __init__이 매개변수가 없기때문에 매개변수가 필요없다면 다음은 필요 없다.
    """

    def __init__(self, *args, **kwargs) -> None:
        pass

    def on_install(self, params: dict) -> None:
        pass

    def on_update(self, params: dict) -> None:
        pass

    def on_selfdestruct(self, recipient: 'Address') -> None:
        pass


class IconScoreBaseMeta(ABCMeta):
    def __new__(mcs, name, bases, namespace, **kwargs):
        if IconScoreObject in bases:
            return super().__new__(mcs, name, bases, namespace, **kwargs)

        cls = super().__new__(mcs, name, bases, namespace, **kwargs)

        if not isinstance(namespace, dict):
            raise IconScoreException('attr is not dict!')

        custom_funcs = [value for key, value in getmembers(cls, predicate=isfunction)
                        if not key.startswith('__')]

        external_funcs = {func.__name__: signature(func) for func in custom_funcs
                          if getattr(func, CONST_BIT_FLAG, 0) & ConstBitFlag.External}
        payable_funcs = [func for func in custom_funcs
                         if getattr(func, CONST_BIT_FLAG, 0) & ConstBitFlag.Payable]

        readonly_payables = [func for func in payable_funcs
                             if getattr(func, CONST_BIT_FLAG, 0) & ConstBitFlag.ReadOnly]
        if bool(readonly_payables):
            raise IconScoreException(f"can't payable readonly func: {readonly_payables}")

        if external_funcs:
            setattr(cls, CONST_CLASS_EXTERNALS, external_funcs)
        if payable_funcs:
            payable_funcs = {func.__name__: signature(func) for func in payable_funcs}
            setattr(cls, CONST_CLASS_PAYABLES, payable_funcs)
        return cls


class IconScoreBase(IconScoreObject, ContextGetter, DatabaseObserver,
                    metaclass=IconScoreBaseMeta):

    @abstractmethod
    def on_install(self, params: dict) -> None:
        """DB initialization on score install

        :param params:
        """
        super().on_install(params)

    @abstractmethod
    def on_update(self, params: dict) -> None:
        """DB initialization on score update

        :param params:
        """
        super().on_update(params)

    def on_selfdestruct(self, recipient: 'Address') -> None:
        raise NotImplementedError()

    @abstractmethod
    def __init__(self, db: 'IconScoreDatabase', owner: 'Address') -> None:
        super().__init__(db, owner)
        self.__db = db
        self.__owner = owner
        self.__address = db.address

        if not self.get_api():
            raise ExternalException('empty abi!', '__init__', str(type(self)))

        self.__db.set_observer(self)

    @classmethod
    def get_api(cls) -> dict:
        return cls.__get_attr_dict(CONST_CLASS_EXTERNALS)

    @classmethod
    def __get_attr_dict(cls, attr: str) -> dict:
        return getattr(cls, attr, {})

    def __call_method(self, func_name: str, arg_params: list, kw_params: dict):

        if func_name not in self.get_api():
            raise ExternalException(f"can't external call", func_name, type(self).__name__)

        self.__check_readonly(func_name)
        self.__check_payable(func_name, self.__get_attr_dict(CONST_CLASS_PAYABLES))

        score_func = getattr(self, func_name)
        return score_func(*arg_params, **kw_params)

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

    def __check_readonly(self, func_name: str):
        func = getattr(self, func_name)
        readonly = bool(getattr(func, CONST_BIT_FLAG, 0) & ConstBitFlag.ReadOnly)
        if readonly != self._context.readonly:
            raise IconScoreException(f'context type is mismatch func: {func_name}, cls: {type(self).__name__}')

    def __call_interface_score(self, addr_to: 'Address', func_name: str, arg_list: list, kw_dict: dict):
        """Call external function provided by other IconScore with arguments without fallback

        :param addr_to: the address of other IconScore
        :param func_name: function name provided by other IconScore
        :param arg_list:
        :param kw_dict:
        """
        self._context.step_counter.increase_step(StepType.CALL, 1)
        return self._context.call(self.address, addr_to, func_name, arg_list, kw_dict)

    def __write_eventlog(self, func_name: str, arg_list: list, kw_dict: dict):
        """

        :param func_name: function name provided by other IconScore
        :param arg_list:
        :param kw_dict:
        """
        # raise NotImplementedError
        pass

    @property
    def msg(self) -> 'Message':
        return self._context.msg

    @property
    def address(self) -> 'Address':
        return self.__address

    @property
    def tx(self) -> 'Transaction':
        return self._context.tx

    @property
    def block(self) -> 'Block':
        return self._context.block

    @property
    def db(self) -> 'IconScoreDatabase':
        return self.__db

    @property
    def owner(self) -> 'Address':
        return self.__owner

    def now(self):
        return self.block.timestamp

    def create_interface_score(self, addr_to: 'Address', interface_cls: Callable[[Address, callable], Type[T]]) -> T:
        if interface_cls is InterfaceScore:
            raise InterfaceException(FORMAT_IS_NOT_DERIVED_OF_OBJECT.format(InterfaceScore.__name__))
        return interface_cls(addr_to, self.__call_interface_score)

    def call(self, addr_to: 'Address', func_name: str, arg_list: list, kw_dict: dict):

        warnings.warn('Use create_interface_score() instead.', DeprecationWarning, stacklevel=2)

        """Call external function provided by other IconScore with arguments without fallback

        :param addr_to: the address of other IconScore
        :param func_name: function name provided by other IconScore
        :param arg_list:
        :param kw_dict:
        """
        self._context.step_counter.increase_step(StepType.TRANSFER, 1)
        return self._context.call(self.address, addr_to, func_name, arg_list, kw_dict)

    def transfer(self, addr_to: 'Address', amount: int) -> bool:
        ret = self._context.transfer(self.__address, addr_to, amount)
        if amount > 0:
            self._context.step_counter.increase_step(StepType.TRANSFER, 1)
        return ret

    def send(self, addr_to: 'Address', amount: int) -> bool:
        ret = self._context.send(self.__address, addr_to, amount)
        if amount > 0:
            self._context.step_counter.increase_step(StepType.TRANSFER, 1)
        return ret

    def revert(self) -> None:
        return self._context.revert(self.__address)

    def on_put(self,
               context: 'IconScoreContext',
               key: bytes,
               old_value: bytes,
               new_value: bytes):
        """Invoked when `put` is called in `ContextDatabase`.

        :param context: SCORE context
        :param key: key
        :param old_value: old value
        :param new_value: new value
        """
        if new_value and context and context.type == IconScoreContextType.INVOKE:
            if old_value:
                # modifying a value
                context.step_counter.increase_step(
                    StepType.STORAGE_REPLACE, len(new_value))
            else:
                # newly storing a value
                context.step_counter.increase_step(
                    StepType.STORAGE_DELETE, len(new_value))

    def on_delete(self,
                  context: 'IconScoreContext',
                  key: bytes,
                  old_value: bytes):
        """Invoked when `delete` is called in `ContextDatabase`.

        :param context: SCORE context
        :param key: key
        :param old_value: old value
        """
        if context and context.type == IconScoreContextType.INVOKE:
            context.step_counter.increase_step(
                StepType.STORAGE_DELETE, len(old_value))
