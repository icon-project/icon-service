from abc import ABCMeta, abstractmethod
from typing import Any, List, Dict

from ... import Address
from ...icon_constant import IconNetworkValueType, IconScoreContextType
from ...iconscore.icon_score_step import StepType
from ...utils.msgpack_for_db import MsgPackForDB


class Value(metaclass=ABCMeta):
    PREFIX: bytes = b'inv'
    # All subclass must have 'TYPE' constant variable
    TYPE: 'IconNetworkValueType' = None

    def __init__(self, value: Any):
        self.value: Any = value

    def make_key(self) -> bytes:
        key: bytes = self.TYPE.value
        return self.PREFIX + key

    @abstractmethod
    def to_bytes(self) -> bytes:
        pass

    @abstractmethod
    def from_bytes(self, bytes_: bytes) -> 'Value':
        pass


class StepCosts(Value):
    TYPE: 'IconNetworkValueType' = IconNetworkValueType.STEP_COSTS

    def __init__(self, value: Dict[StepType, int]):
        super().__init__(value)

    def to_bytes(self) -> bytes:
        version: int = 0
        value: dict = {key.value: value for key, value in self.value.items()}
        items: List[version, dict] = [version, value]
        return MsgPackForDB.dumps(items)

    @classmethod
    def from_bytes(cls, bytes_: bytes) -> 'StepCosts':
        items: list = MsgPackForDB.loads(bytes_)
        version: int = items[0]
        value: dict = items[1]
        converted_value: Dict[StepType, int] = {StepType(key): value for key, val in value.items()}

        assert version == 0
        return cls(converted_value)


class StepPrice(Value):
    TYPE: 'IconNetworkValueType' = IconNetworkValueType.STEP_PRICE

    def __init__(self, value: int):
        super().__init__(value)

    def to_bytes(self) -> bytes:
        version: int = 0
        items: List[version, int] = [version, self.value]
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

    def __init__(self, value: Dict[IconScoreContextType, int]):
        super().__init__(value)

    def to_bytes(self) -> bytes:
        version: int = 0
        value: dict = {key.value: value for key, value in self.value.items()}
        items: List[version, dict] = [version, value]
        return MsgPackForDB.dumps(items)

    @classmethod
    def from_bytes(cls, bytes_: bytes) -> 'MaxStepLimits':
        items: list = MsgPackForDB.loads(bytes_)
        version: int = items[0]
        value: dict = items[1]
        converted_value: Dict[IconScoreContextType, int] = {IconScoreContextType(key): value for key, val in value.items()}

        assert version == 0
        return cls(converted_value)


class ScoreBlackList(Value):
    TYPE: 'IconNetworkValueType' = IconNetworkValueType.SCORE_BLACK_LIST

    def __init__(self, value: List['Address']):
        super().__init__(value)

    def to_bytes(self) -> bytes:
        version: int = 0
        items: List[version, List['Address']] = [version, self.value]
        return MsgPackForDB.dumps(items)

    @classmethod
    def from_bytes(cls, bytes_: bytes) -> 'ScoreBlackList':
        items: list = MsgPackForDB.loads(bytes_)
        version: int = items[0]
        value: List['Address'] = items[1]

        assert version == 0
        return cls(value)


class RevisionCode(Value):
    TYPE: 'IconNetworkValueType' = IconNetworkValueType.REVISION_CODE

    def __init__(self, value: int):
        super().__init__(value)

    def to_bytes(self) -> bytes:
        version: int = 0
        items: List[version, int] = [version, self.value]
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
        super().__init__(value)

    def to_bytes(self) -> bytes:
        version: int = 0
        items: List[version, str] = [version, self.value]
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

    def __init__(self, value: Dict[str, List[str]]):
        super().__init__(value)

    def to_bytes(self) -> bytes:
        version: int = 0
        items: List[int, Dict[str, List[str]]] = [version, self.value]
        return MsgPackForDB.dumps(items)

    @classmethod
    def from_bytes(cls, bytes_: bytes) -> 'ImportWhiteList':
        items: list = MsgPackForDB.loads(bytes_)
        version: int = items[0]
        value: Dict[str, List[str]] = items[1]

        assert version == 0
        return cls(value)


class ServiceConfig(Value):
    TYPE: 'IconNetworkValueType' = IconNetworkValueType.SERVICE_CONFIG

    def __init__(self, value: int):
        super().__init__(value)

    def to_bytes(self) -> bytes:
        version: int = 0
        items: List[version, int] = [version, self.value]
        return MsgPackForDB.dumps(items)

    @classmethod
    def from_bytes(cls, bytes_: bytes) -> 'ServiceConfig':
        items: list = MsgPackForDB.loads(bytes_)
        version: int = items[0]
        value: int = items[1]

        assert version == 0
        return cls(value)


VALUE_MAPPER = {val.TYPE: val for val in Value.__subclasses__()}
