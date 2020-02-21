from abc import ABCMeta, abstractmethod
from typing import Any, List

from ...icon_constant import SystemValueType, IconScoreContextType
from ...iconscore.icon_score_step import StepType
from ...utils.msgpack_for_db import MsgPackForDB


class SystemData(metaclass=ABCMeta):
    PREFIX: bytes = b'sv'
    SYSTEM_TYPE: 'SystemValueType' = None

    def __init__(self, value: Any):
        self.value: Any = value

    @abstractmethod
    def make_key(self) -> bytes:
        pass

    @abstractmethod
    def to_bytes(self) -> bytes:
        pass

    @abstractmethod
    def from_bytes(self, bytes_: bytes) -> 'SystemData':
        pass


class StepCosts(SystemData):
    SYSTEM_TYPE: 'SystemValueType' = SystemValueType.STEP_COSTS

    def __init__(self, value: dict):
        super().__init__(value)

    def make_key(self) -> bytes:
        return self.PREFIX + self.SYSTEM_TYPE.value

    def to_bytes(self) -> bytes:
        version: int = 0
        value: dict = {key.value: value for key, value in self.value.items()}
        items: List[version, Any] = [version, value]
        return MsgPackForDB.dumps(items)

    @classmethod
    def from_bytes(cls, bytes_: bytes) -> 'StepCosts':
        items: list = MsgPackForDB.loads(bytes_)
        version: int = items[0]
        value: dict = items[1]
        converted_value: dict = {StepType(key): value for key, val in value.items()}

        assert version == 0
        return cls(converted_value)


class StepPrice(SystemData):
    SYSTEM_TYPE: 'SystemValueType' = SystemValueType.STEP_PRICE

    def __init__(self, value: Any):
        super().__init__(value)

    def make_key(self) -> bytes:
        return self.PREFIX + self.SYSTEM_TYPE.value

    def to_bytes(self) -> bytes:
        version: int = 0
        items: List[version, Any] = [version, self.value]
        return MsgPackForDB.dumps(items)

    @classmethod
    def from_bytes(cls, bytes_: bytes) -> 'StepPrice':
        items: list = MsgPackForDB.loads(bytes_)
        version: int = items[0]
        value: dict = items[1]

        assert version == 0
        return cls(value)


class MaxStepLimits(SystemData):
    SYSTEM_TYPE: 'SystemValueType' = SystemValueType.MAX_STEP_LIMITS

    def __init__(self, value: Any):
        super().__init__(value)

    def make_key(self) -> bytes:
        return self.PREFIX + self.SYSTEM_TYPE.value

    def to_bytes(self) -> bytes:
        version: int = 0
        value: dict = {key.value: value for key, value in self.value.items()}
        items: List[version, Any] = [version, value]
        return MsgPackForDB.dumps(items)

    @classmethod
    def from_bytes(cls, bytes_: bytes) -> 'MaxStepLimits':
        items: list = MsgPackForDB.loads(bytes_)
        version: int = items[0]
        value: dict = items[1]
        converted_value: dict = {IconScoreContextType(key): value for key, val in value.items()}

        assert version == 0
        return cls(converted_value)


class ScoreBlackList(SystemData):
    SYSTEM_TYPE: 'SystemValueType' = SystemValueType.SCORE_BLACK_LIST

    def __init__(self, value: Any):
        super().__init__(value)

    def make_key(self) -> bytes:
        return self.PREFIX + self.SYSTEM_TYPE.value

    def to_bytes(self) -> bytes:
        version: int = 0
        items: List[version, Any] = [version, self.value]
        return MsgPackForDB.dumps(items)

    @classmethod
    def from_bytes(cls, bytes_: bytes) -> 'ScoreBlackList':
        items: list = MsgPackForDB.loads(bytes_)
        version: int = items[0]
        value: dict = items[1]

        assert version == 0
        return cls(value)


class RevisionCode(SystemData):
    SYSTEM_TYPE: 'SystemValueType' = SystemValueType.REVISION_CODE

    def __init__(self, value: Any):
        super().__init__(value)

    def make_key(self) -> bytes:
        return self.PREFIX + self.SYSTEM_TYPE.value

    def to_bytes(self) -> bytes:
        version: int = 0
        items: List[version, Any] = [version, self.value]
        return MsgPackForDB.dumps(items)

    @classmethod
    def from_bytes(cls, bytes_: bytes) -> 'RevisionCode':
        items: list = MsgPackForDB.loads(bytes_)
        version: int = items[0]
        value: dict = items[1]

        assert version == 0
        return cls(value)


class RevisionName(SystemData):
    SYSTEM_TYPE: 'SystemValueType' = SystemValueType.REVISION_NAME

    def __init__(self, value: Any):
        super().__init__(value)

    def make_key(self) -> bytes:
        return self.PREFIX + self.SYSTEM_TYPE.value

    def to_bytes(self) -> bytes:
        version: int = 0
        items: List[version, Any] = [version, self.value]
        return MsgPackForDB.dumps(items)

    @classmethod
    def from_bytes(cls, bytes_: bytes) -> 'RevisionName':
        items: list = MsgPackForDB.loads(bytes_)
        version: int = items[0]
        value: dict = items[1]

        assert version == 0
        return cls(value)


class ImportWhiteList(SystemData):
    SYSTEM_TYPE: 'SystemValueType' = SystemValueType.IMPORT_WHITE_LIST

    def __init__(self, value: Any):
        super().__init__(value)

    def make_key(self) -> bytes:
        return self.PREFIX + self.SYSTEM_TYPE.value

    def to_bytes(self) -> bytes:
        version: int = 0
        items: List[version, Any] = [version, self.value]
        return MsgPackForDB.dumps(items)

    @classmethod
    def from_bytes(cls, bytes_: bytes) -> 'ImportWhiteList':
        items: list = MsgPackForDB.loads(bytes_)
        version: int = items[0]
        value: dict = items[1]

        assert version == 0
        return cls(value)


class ServiceConfig(SystemData):
    SYSTEM_TYPE: 'SystemValueType' = SystemValueType.SERVICE_CONFIG

    def __init__(self, value: Any):
        super().__init__(value)

    def make_key(self) -> bytes:
        return self.PREFIX + self.SYSTEM_TYPE.value

    def to_bytes(self) -> bytes:
        version: int = 0
        items: List[version, Any] = [version, self.value]
        return MsgPackForDB.dumps(items)

    @classmethod
    def from_bytes(cls, bytes_: bytes) -> 'ServiceConfig':
        items: list = MsgPackForDB.loads(bytes_)
        version: int = items[0]
        value: dict = items[1]

        assert version == 0
        return cls(value)


SYSTEM_DATA_MAPPER = {
    SystemValueType.REVISION_CODE: RevisionCode,
    SystemValueType.REVISION_NAME: RevisionName,
    SystemValueType.SCORE_BLACK_LIST: ScoreBlackList,
    SystemValueType.STEP_PRICE: StepPrice,
    SystemValueType.STEP_COSTS: StepCosts,
    SystemValueType.MAX_STEP_LIMITS: MaxStepLimits,
    SystemValueType.SERVICE_CONFIG: ServiceConfig,
    SystemValueType.IMPORT_WHITE_LIST: ImportWhiteList
}
