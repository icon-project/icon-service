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
from inspect import isfunction, getmembers, signature, Parameter
from abc import abstractmethod
from functools import partial

from iconservice.iconscore.icon_score_event_log import INDEXED_ARGS_LIMIT, EventLog
from .icon_score_api_generator import ScoreApiGenerator
from .icon_score_base2 import *
from .icon_score_step import StepType
from .icon_score_context import IconScoreContextType
from .icon_score_context import ContextGetter
from .icx import Icx
from ..base.exception import *
from ..base.type_converter import TypeConverter
from ..database.db import IconScoreDatabase, DatabaseObserver

from typing import TYPE_CHECKING, Callable, Any, List

if TYPE_CHECKING:
    from .icon_score_context import IconScoreContext
    from ..base.address import Address
    from ..base.transaction import Transaction
    from ..base.message import Message
    from ..base.block import Block


def interface(func):
    cls_name, func_name = str(func.__qualname__).split('.')
    if not isfunction(func):
        raise InterfaceException(FORMAT_IS_NOT_FUNCTION_OBJECT.format(func, cls_name))

    if getattr(func, CONST_BIT_FLAG, 0) & ConstBitFlag.Interface:
        raise IconScoreException(FORMAT_DECORATOR_DUPLICATED.format('interface', func_name, cls_name))

    bit_flag = getattr(func, CONST_BIT_FLAG, 0) | ConstBitFlag.Interface
    setattr(func, CONST_BIT_FLAG, bit_flag)

    @wraps(func)
    def __wrapper(calling_obj: Any, *args, **kwargs):
        if not isinstance(calling_obj, InterfaceScore):
            raise InterfaceException(FORMAT_IS_NOT_DERIVED_OF_OBJECT.format(InterfaceScore.__name__))

        call_method = getattr(calling_obj, '_InterfaceScore__call_method')
        ret = call_method(func_name, args, kwargs)
        return ret

    return __wrapper


def eventlog(func=None, *, indexed_args_count=0):
    if func is None:
        return partial(eventlog, indexed_args_count=indexed_args_count)

    cls_name, func_name = str(func.__qualname__).split('.')
    if not isfunction(func):
        raise EventLogException(
            FORMAT_IS_NOT_FUNCTION_OBJECT.format(func, cls_name))

    if getattr(func, CONST_BIT_FLAG, 0) & ConstBitFlag.EventLog:
        raise IconScoreException(
            FORMAT_DECORATOR_DUPLICATED.format('eventlog', func_name, cls_name))

    bit_flag = getattr(func, CONST_BIT_FLAG, 0) | ConstBitFlag.EventLog
    setattr(func, CONST_BIT_FLAG, bit_flag)

    parameters = signature(func).parameters.values()
    event_signature = __retrieve_event_signature(func_name, parameters)

    @wraps(func)
    def __wrapper(calling_obj: Any, *args, **kwargs):
        if not (isinstance(calling_obj, IconScoreBase)):
            raise EventLogException(
                FORMAT_IS_NOT_DERIVED_OF_OBJECT.format(IconScoreBase.__name__))
        try:
            arguments = __resolve_arguments(func_name, parameters, args, kwargs)
        except TypeError as e:
            raise EventLogException(str(e))

        call_method = getattr(calling_obj, '_IconScoreBase__put_eventlog')
        return call_method(event_signature, arguments, indexed_args_count)

    return __wrapper


def __retrieve_event_signature(function_name, parameters) -> str:
    """
    Retrieves a event signature from the function name and parameters
    :param function_name: name of event function
    :param parameters: Arguments description of the function declaration
    :return: event signature
    """
    type_names: List[str] = []
    for i, param in enumerate(parameters):
        if i > 0:
            type_names.append(str(param.annotation.__name__))
    return f"{function_name}({','.join(type_names)})"


def __resolve_arguments(function_name, parameters, args, kwargs) -> List[Any]:
    """
    Resolves arguments with keeping order as the function declaration
    :param parameters: Arguments description of the function declaration
    :param args: input ordered arguments
    :param kwargs: input keyword arguments
    :return: an ordered list of arguments
    """
    arguments = []
    for i, parameter in enumerate(parameters, -1):
        if i < 0:
            # pass the self parameter
            continue
        name = parameter.name
        annotation = parameter.annotation
        if i < len(args):
            # the argument is in the ordered args
            value = args[i]
            if name in kwargs:
                raise TypeError(
                    f"Duplicated argument value for '{function_name}': {name}")
        else:
            # If arg is over, the argument should be searched on kwargs
            try:
                value = kwargs[name]
            except KeyError:
                raise TypeError(
                    f"Missing argument value for '{function_name}': {name}")
        # If there's no hint of argument in the function declaration,
        # raise an exception
        if annotation is Parameter.empty:
            raise TypeError(
                f"Missing argument hint for '{function_name}': '{name}'")
        if hasattr(annotation, '_subs_tree'):
            # Generic type has a '_subs_tree'
            sub_tree = annotation._subs_tree()
            if isinstance(sub_tree, tuple):
                # Generic declaration with sub type. `Generic[T1,...]`
                main_type = sub_tree[0]
            else:
                # Generic declaration only
                main_type = sub_tree
        else:
            main_type = annotation
        if not isinstance(value, main_type):
            raise TypeError(f"Mismatch type type of '{name}': "
                            f"{type(value)}, expected: {main_type}")
        arguments.append(value)
    return arguments


def external(func=None, *, readonly=False):
    if func is None:
        return partial(external, readonly=readonly)

    cls_name, func_name = str(func.__qualname__).split('.')
    if not isfunction(func):
        raise IconScoreException(FORMAT_IS_NOT_FUNCTION_OBJECT.format(func, cls_name))

    if func_name == STR_FALLBACK:
        raise IconScoreException(f"can't locate external to this func func: {func_name}, cls: {cls_name}")

    if getattr(func, CONST_BIT_FLAG, 0) & ConstBitFlag.External:
        raise IconScoreException(FORMAT_DECORATOR_DUPLICATED.format('external', func_name, cls_name))

    bit_flag = getattr(func, CONST_BIT_FLAG, 0) | ConstBitFlag.External | int(readonly)
    setattr(func, CONST_BIT_FLAG, bit_flag)

    @wraps(func)
    def __wrapper(calling_obj: Any, *args, **kwargs):
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
    def __wrapper(calling_obj: Any, *args, **kwargs):

        if not (isinstance(calling_obj, IconScoreBase)):
            raise PayableException(
                FORMAT_IS_NOT_DERIVED_OF_OBJECT.format(IconScoreBase.__name__), func_name, cls_name)
        res = func(calling_obj, *args, **kwargs)
        return res

    return __wrapper


class IconScoreObject(ABC):
    """ 오직 __init__ 파라미터 상속용
        이것이 필요한 이유는 super().__init__이 우리 예상처럼 부모, 자식일 수 있으나 다중상속일때는 조금 다르게 흘러간다.
        class.__mro__로 하기때문에 다음과 같이 init에 매개변수를 받게 자유롭게 하려면 다음처럼 래핑 클래스가 필요하다.
        ex)최상위1 상위1 부모1 상위2 부모 object 이렇게 흘러간다 보통..
        물론 기본 __init__이 매개변수가 없기때문에 매개변수가 필요없다면 다음은 필요 없다.
    """

    def __init__(self, *args, **kwargs) -> None:
        pass

    def on_install(self, **kwargs) -> None:
        pass

    def on_update(self, **kwargs) -> None:
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
            raise IconScoreException(f"Readonly method cannot be payable: {readonly_payables}")

        if external_funcs:
            setattr(cls, CONST_CLASS_EXTERNALS, external_funcs)
        if payable_funcs:
            payable_funcs = {func.__name__: signature(func) for func in payable_funcs}
            setattr(cls, CONST_CLASS_PAYABLES, payable_funcs)

        api_list = ScoreApiGenerator.generate(custom_funcs)
        setattr(cls, CONST_CLASS_API, api_list)

        return cls


class IconScoreBase(IconScoreObject, ContextGetter,
                    metaclass=IconScoreBaseMeta):

    @abstractmethod
    def on_install(self, **kwargs) -> None:
        """DB initialization on score install
        """
        super().on_install(**kwargs)

    @abstractmethod
    def on_update(self, **kwargs) -> None:
        """DB initialization on score update
        """
        super().on_update(**kwargs)

    @abstractmethod
    def __init__(self, db: 'IconScoreDatabase', owner: 'Address') -> None:
        super().__init__(db, owner)
        self.__db = db
        self.__owner = owner
        self.__address = db.address
        self.__icx = None

        if not self.__get_attr_dict(CONST_CLASS_EXTERNALS):
            raise ExternalException('empty abi!', '__init__', str(type(self)))

        self.__db.set_observer(self.__create_db_observer())

    def on_selfdestruct(self, recipient: 'Address') -> None:
        raise NotImplementedError()

    def fallback(self) -> None:
        pass

    @classmethod
    def get_api(cls) -> dict:
        return getattr(cls, CONST_CLASS_API, "")

    @classmethod
    def __get_attr_dict(cls, attr: str) -> dict:
        return getattr(cls, attr, {})

    def __create_db_observer(self) -> 'DatabaseObserver':
        return DatabaseObserver(self.__on_db_put, self.__on_db_delete)

    def __call_method(self, func_name: str, arg_params: list, kw_params: dict):

        if func_name not in self.__get_attr_dict(CONST_CLASS_EXTERNALS):
            raise ExternalException(f"Cannot call external method", func_name, type(self).__name__,
                                    ExceptionCode.METHOD_NOT_FOUND)

        self.__check_readonly(func_name)
        self.__check_payable(func_name, self.__get_attr_dict(CONST_CLASS_PAYABLES))

        score_func = getattr(self, func_name)

        annotation_params = TypeConverter.make_annotations_from_method(score_func)
        TypeConverter.convert_params(annotation_params, kw_params)
        return score_func(*arg_params, **kw_params)

    def __call_fallback(self):
        func_name = STR_FALLBACK
        payable_dict = self.__get_attr_dict(CONST_CLASS_PAYABLES)
        self.__check_payable(func_name, payable_dict)

        score_func = getattr(self, func_name)
        score_func()

    def __check_payable(self, func_name: str, payable_dict: dict):
        if func_name not in payable_dict:
            if self.msg.value > 0:
                raise PayableException(f"This is not payable", func_name, type(self).__name__)

    def __check_readonly(self, func_name: str):
        func = getattr(self, func_name)
        readonly = bool(getattr(func, CONST_BIT_FLAG, 0) & ConstBitFlag.ReadOnly)
        if readonly != self._context.readonly:
            raise IconScoreException(f'Context type mismatch, func: {func_name}, cls: {type(self).__name__}')

    def __call_interface_score(self, addr_to: 'Address', func_name: str, arg_list: list, kw_dict: dict):
        """Call external function provided by other IconScore with arguments without fallback

        :param addr_to: the address of other IconScore
        :param func_name: function name provided by other IconScore
        :param arg_list:
        :param kw_dict:
        """
        self._context.step_counter.increase_step(StepType.CALL, 1)
        return self._context.call(self.address, addr_to, func_name, arg_list, kw_dict)

    def __put_eventlog(self,
                       event_signature: str,
                       arguments: List[Any],
                       indexed_args_count: int):
        """
        Puts a eventlog to the context running

        :param event_signature: signature of eventlog
        :param arguments: arguments of eventlog call
        """
        if indexed_args_count > INDEXED_ARGS_LIMIT:
            raise EventLogException(
                f'indexed arguments are overflow: limit={INDEXED_ARGS_LIMIT}')

        if indexed_args_count > len(arguments):
            raise EventLogException(
                f'declared indexed_args_count is {indexed_args_count}, '
                f'but argument count is {len(arguments)}')

        indexed: List[BaseType] = [event_signature]
        data: List[BaseType] = []
        for i, argument in enumerate(arguments):
            # Raises an exception if the types are not supported
            if not IconScoreBase.__is_base_type(argument):
                raise EventLogException(
                    f'Not supported type: {type(argument)}')

            # Separates indexed type and base type with keeping order.
            if i < indexed_args_count:
                indexed.append(argument)
            else:
                data.append(argument)

        event = EventLog(self.address, indexed, data)
        self._context.event_logs.append(event)

    @staticmethod
    def __is_base_type(value) -> bool:
        for base_type in BaseType.__constraints__:
            if isinstance(value, base_type):
                return True
        return False

    @staticmethod
    def __on_db_put(context: 'IconScoreContext',
                    key: bytes,
                    old_value: bytes,
                    new_value: bytes):
        """Invoked when `put` is called in `ContextDatabase`.

        # All steps are managed in the score
        # Don't move to another codes

        :param context: SCORE context
        :param key: key
        :param old_value: old value
        :param new_value: new value
        """

        if new_value and context and \
                context.type == IconScoreContextType.INVOKE:
            if old_value:
                # modifying a value
                context.step_counter.increase_step(
                    StepType.STORAGE_REPLACE, len(new_value))
            else:
                # newly storing a value
                context.step_counter.increase_step(
                    StepType.STORAGE_SET, len(new_value))

    @staticmethod
    def __on_db_delete(context: 'IconScoreContext',
                       key: bytes,
                       old_value: bytes):
        """Invoked when `delete` is called in `ContextDatabase`.

        # All steps are managed in the score
        # Don't move to another codes
        :param context: SCORE context
        :param key: key
        :param old_value: old value
        """

        if old_value and context and \
                context.type == IconScoreContextType.INVOKE:
            context.step_counter.increase_step(
                StepType.STORAGE_DELETE, len(old_value))

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

    @property
    def icx(self) -> 'Icx':
        if self.__icx is None:
            self.__icx = Icx(self._context, self.__address)
        return self.__icx

    def now(self):
        return self.block.timestamp

    def create_interface_score(self, addr_to: 'Address', interface_cls: Callable[['Address', callable], T]) -> T:
        if interface_cls is InterfaceScore:
            raise InterfaceException(FORMAT_IS_NOT_DERIVED_OF_OBJECT.format(InterfaceScore.__name__))
        return interface_cls(addr_to, self.__call_interface_score)

    def call(self, addr_to: 'Address', func_name: str, kw_dict: dict):

        warnings.warn('Use create_interface_score() instead.', DeprecationWarning, stacklevel=2)

        """Call external function provided by other IconScore with arguments without fallback

        :param addr_to: the address of other IconScore
        :param func_name: function name provided by other IconScore
        :param arg_list:
        :param kw_dict:
        """
        self._context.step_counter.increase_step(StepType.TRANSFER, 1)
        return self._context.call(self.address, addr_to, func_name, [], kw_dict)

    def revert(self, message: Optional[str] = None,
               code: Union[ExceptionCode, int] = ExceptionCode.SCORE_ERROR) -> None:
        self._context.revert(message, code)
