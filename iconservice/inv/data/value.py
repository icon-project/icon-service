from abc import ABCMeta, abstractmethod
from copy import copy, deepcopy
from typing import Any, List, Dict

from ... import Address
from ...base.exception import InvalidParamsException
from ...icon_constant import IconNetworkValueType, IconScoreContextType, IconServiceFlag
from ...iconscore.icon_score_step import StepType
from ...utils.msgpack_for_db import MsgPackForDB


class Value(metaclass=ABCMeta):
    PREFIX: bytes = b'inv'
    # All subclass must have 'TYPE' constant variable
    TYPE: 'IconNetworkValueType' = None

    def __init__(self):
        self._value = None

    @property
    def value(self) -> Any:
        """
        ================================================
        =================== WARNING!!! =================
        ================================================

        Return Icon Network Value.
        If return data is mutable (e.g. dict), should copy (or deepcopy if need) and return.
        :return:
        """
        if not isinstance(self._value, (int, str, bool, bytes, Address)):
            raise TypeError(f"you must implement copy: {type(self._value)}")
        return self._value

    def make_key(self) -> bytes:
        key: bytes = self.TYPE.value
        return self.PREFIX + key

    @abstractmethod
    def to_bytes(self) -> bytes:
        pass

    @classmethod
    @abstractmethod
    def from_bytes(cls, bytes_: bytes) -> 'Value':
        pass


class StepCosts(Value):
    TYPE: 'IconNetworkValueType' = IconNetworkValueType.STEP_COSTS

    def __init__(self, value: Dict[StepType, int], need_check_value: bool = True):
        super().__init__()

        if need_check_value:
            self._check_value_is_valid(value)

        self._value: Dict[StepType, int] = value

    @classmethod
    def _check_value_is_valid(cls, value: dict):
        if not isinstance(value, dict):
            raise TypeError(f"Invalid Step costs type: {type(value)}")

        for step_type, cost in value.items():
            if cost < 0:
                if step_type != StepType.CONTRACT_DESTRUCT and step_type != StepType.DELETE:
                    raise InvalidParamsException(f"Invalid step costs: {step_type} {cost}")

    @property
    def value(self) -> Dict[StepType, int]:
        """
        ================================================
        =================== WARNING!!! =================
        ================================================

        Return Icon Network Value.
        If return data is mutable (e.g. dict), should copy (or deepcopy if need) and return.
        :return:
        """
        return copy(self._value)

    def to_bytes(self) -> bytes:
        version: int = 0
        value: dict = {key.value: value for key, value in self._value.items()}
        items: List[version, dict] = [version, value]
        return MsgPackForDB.dumps(items)

    @classmethod
    def from_bytes(cls, bytes_: bytes) -> 'StepCosts':
        items: list = MsgPackForDB.loads(bytes_)
        version: int = items[0]
        value: dict = items[1]
        converted_value: Dict[StepType, int] = {StepType(key): val for key, val in value.items()}

        assert version == 0
        return cls(converted_value, need_check_value=False)


class StepPrice(Value):
    TYPE: 'IconNetworkValueType' = IconNetworkValueType.STEP_PRICE

    def __init__(self, value: int):
        super().__init__()

        if not isinstance(value, int):
            raise TypeError(f"Invalid step price type. must be integer: {type(value)}")
        if value < 0:
            raise InvalidParamsException(f"Invalid step price. should not be negative value {value}")

        self._value: int = value

    def to_bytes(self) -> bytes:
        version: int = 0
        items: List[version, int] = [version, self._value]
        return MsgPackForDB.dumps(items)

    @classmethod
    def from_bytes(cls, bytes_: bytes) -> 'StepPrice':
        items: list = MsgPackForDB.loads(bytes_)
        version: int = items[0]
        value: int = items[1]

        assert version == 0
        return cls(value)


class MaxStepLimits(Value):
    TYPE: 'IconNetworkValueType' = IconNetworkValueType.MAX_STEP_LIMITS

    def __init__(self, value: Dict[IconScoreContextType, int], need_check_value: bool = True):
        super().__init__()

        if need_check_value:
            self._check_value_is_valid(value)
            self._supplements_value(value)

        self._value: Dict[IconScoreContextType, int] = value

    @classmethod
    def _supplements_value(cls, value: dict):
        if value.get(IconScoreContextType.INVOKE) is None:
            value[IconScoreContextType.INVOKE] = 0
        if value.get(IconScoreContextType.QUERY) is None:
            value[IconScoreContextType.QUERY] = 0

    @classmethod
    def _check_value_is_valid(cls, value: dict):
        if not isinstance(value, dict):
            raise TypeError(f"Invalid import white list: {value}")
        for context_type, val in value.items():
            if val < 0:
                raise InvalidParamsException(f"Invalid max step limits value: {context_type.name}, {val}")

    @property
    def value(self) -> Dict[IconScoreContextType, int]:
        """
        ================================================
        =================== WARNING!!! =================
        ================================================

        Return Icon Network Value.
        If return data is mutable (e.g. dict), should copy (or deepcopy if need) and return.
        :return:
        """
        return copy(self._value)

    def to_bytes(self) -> bytes:
        version: int = 0
        value: dict = {key.value: value for key, value in self._value.items()}
        items: List[version, dict] = [version, value]
        return MsgPackForDB.dumps(items)

    @classmethod
    def from_bytes(cls, bytes_: bytes) -> 'MaxStepLimits':
        items: list = MsgPackForDB.loads(bytes_)
        version: int = items[0]
        value: dict = items[1]
        converted_value: Dict[IconScoreContextType, int] = {IconScoreContextType(key): val
                                                            for key, val in value.items()}

        assert version == 0
        return cls(converted_value, need_check_value=False)


class ScoreBlackList(Value):
    TYPE: 'IconNetworkValueType' = IconNetworkValueType.SCORE_BLACK_LIST

    def __init__(self, value: List['Address'], need_check_value: bool = True):
        super().__init__()

        if need_check_value:
            self._check_value_is_valid(value)

        self._value: List['Address'] = value

    @classmethod
    def _check_value_is_valid(cls, value: list):
        if not isinstance(value, list):
            raise TypeError(f"Invalid score black list type: {type(value)}")

        for address in value:
            if not isinstance(address, Address):
                raise TypeError(f"Invalid score black list value type: {type(address)}")

    @property
    def value(self) -> List['Address']:
        """
        ================================================
        =================== WARNING!!! =================
        ================================================

        Return Icon Network Value.
        If return data is mutable (e.g. dict), should copy (or deepcopy if need) and return.
        :return:
        """
        return copy(self._value)

    def to_bytes(self) -> bytes:
        version: int = 0
        items: List[version, List['Address']] = [version, self._value]
        return MsgPackForDB.dumps(items)

    @classmethod
    def from_bytes(cls, bytes_: bytes) -> 'ScoreBlackList':
        items: list = MsgPackForDB.loads(bytes_)
        version: int = items[0]
        value: List['Address'] = items[1]

        assert version == 0
        return cls(value, need_check_value=False)


class RevisionCode(Value):
    TYPE: 'IconNetworkValueType' = IconNetworkValueType.REVISION_CODE

    def __init__(self, value: int):
        super().__init__()

        self._value: int = value

    def to_bytes(self) -> bytes:
        version: int = 0
        items: List[version, int] = [version, self._value]
        return MsgPackForDB.dumps(items)

    @classmethod
    def from_bytes(cls, bytes_: bytes) -> 'RevisionCode':
        items: list = MsgPackForDB.loads(bytes_)
        version: int = items[0]
        value: int = items[1]

        assert version == 0
        return cls(value)


class RevisionName(Value):
    TYPE: 'IconNetworkValueType' = IconNetworkValueType.REVISION_NAME

    def __init__(self, value: str):
        super().__init__()

        self._value: str = value

    def to_bytes(self) -> bytes:
        version: int = 0
        items: List[version, str] = [version, self._value]
        return MsgPackForDB.dumps(items)

    @classmethod
    def from_bytes(cls, bytes_: bytes) -> 'RevisionName':
        items: list = MsgPackForDB.loads(bytes_)
        version: int = items[0]
        value: str = items[1]

        assert version == 0
        return cls(value)


class ImportWhiteList(Value):
    TYPE: 'IconNetworkValueType' = IconNetworkValueType.IMPORT_WHITE_LIST

    def __init__(self, value: Dict[str, List[str]], need_check_value: bool = True):
        super().__init__()

        if need_check_value:
            self._check_value_is_valid(value)
        self._value: Dict[str, List[str]] = value

    @classmethod
    def _check_value_is_valid(cls, value: dict):
        if not isinstance(value, dict):
            raise TypeError(f"Invalid import white list: {value}")

        for key, val in value.items():
            if not isinstance(key, str):
                raise TypeError("Key must be of type `str`")

            if not isinstance(val, list):
                raise TypeError("Value must be of type `list`")
            else:
                for v in val:
                    if not isinstance(v, str):
                        raise TypeError("Element of value must be of type `str`")

    @property
    def value(self) -> Dict[str, List[str]]:
        """
        ================================================
        =================== WARNING!!! =================
        ================================================

        Return Icon Network Value.
        If return data is mutable (e.g. dict), should copy (or deepcopy if need) and return.
        :return:
        """
        return deepcopy(self._value)

    def to_bytes(self) -> bytes:
        version: int = 0
        items: List[int, Dict[str, List[str]]] = [version, self._value]
        return MsgPackForDB.dumps(items)

    @classmethod
    def from_bytes(cls, bytes_: bytes) -> 'ImportWhiteList':
        items: list = MsgPackForDB.loads(bytes_)
        version: int = items[0]
        value: Dict[str, List[str]] = items[1]

        assert version == 0
        return cls(value, need_check_value=False)


class ServiceConfig(Value):
    TYPE: 'IconNetworkValueType' = IconNetworkValueType.SERVICE_CONFIG

    def __init__(self, value: int):
        super().__init__()

        if value < 0 or value > sum(IconServiceFlag):
            raise InvalidParamsException(f"Invalid service config value: {value}")
        self._value: int = value

    def to_bytes(self) -> bytes:
        version: int = 0
        items: List[version, int] = [version, self._value]
        return MsgPackForDB.dumps(items)

    @classmethod
    def from_bytes(cls, bytes_: bytes) -> 'ServiceConfig':
        items: list = MsgPackForDB.loads(bytes_)
        version: int = items[0]
        value: int = items[1]

        assert version == 0
        return cls(value)


class IRep(Value):
    TYPE: 'IconNetworkValueType' = IconNetworkValueType.IREP

    def __init__(self, value: int):
        super().__init__()

        if not isinstance(value, int):
            raise TypeError(f"Invalid I-Rep type. must be integer: {type(value)}")
        if value < 0:
            raise InvalidParamsException(f"Invalid I-Rep. should not be negative value {value}")

        self._value: int = value

    def to_bytes(self) -> bytes:
        version: int = 0
        items: List[version, int] = [version, self._value]
        return MsgPackForDB.dumps(items)

    @classmethod
    def from_bytes(cls, bytes_: bytes) -> 'IRep':
        items: list = MsgPackForDB.loads(bytes_)
        version: int = items[0]
        value: int = items[1]

        assert version == 0
        return cls(value)


VALUE_MAPPER = {val.TYPE: val for val in Value.__subclasses__()}
