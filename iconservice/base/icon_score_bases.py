import inspect
import abc
from functools import wraps
from ..iconscore.icon_score_context import IconScoreContext
from .exception import ExternalException, PayableException
from .message import Message

CONST_CLASS_EXTERNALS = '__externals'
CONST_EXTERNAL_FLAG = '__external_flag'


# TODO external을 사용하기 위한 컨텍스트 클래스 최상단에 붙여준다.
# score decorator는 반드시 최종 클래스에만 붙어야 한다.
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


# TODO 외부에서 부를때 다음 키워드가 없다면 부를 수 없게 해야한다.
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


# TODO payable 기능구현
# TODO 1. 함수에서 icx거래가 가능. 즉 그 함수에서 Context의 value값이 없다면 해당 함수가 실행 되지 않는다. (롤백)
# TODO 2. 만약 스코어 주소로 전송이 들어오면 '_'함수를 콜한다. 다음에서도 Context를 체크하여 함수를 진행.
# TODO 3. 익명함수를 미리 선언 할 수가 없는거 같아서 다음처럼 '_'대신 명시적으로 만들었다. 그리고 ERC20 인터페이스에 선언 예정 (이름이 맞는지는 검수필요)
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


class IconScoreDatabase(abc.ABC):

    @abc.abstractmethod
    def get(self, key: bytes):
        pass

    @abc.abstractmethod
    def put(self, key: bytes, value: bytes):
        pass

    @abc.abstractmethod
    def delete(self, key: bytes):
        pass

    @abc.abstractmethod
    def close(self):
        pass

    @abc.abstractmethod
    def get_sub_db(self, key: bytes):
        pass

    @abc.abstractmethod
    def iterator(self):
        pass


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
    def __init__(self, db: IconScoreDatabase, *args, **kwargs) -> None:
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
