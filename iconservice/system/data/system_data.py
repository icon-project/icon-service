from abc import ABCMeta, abstractmethod
from typing import Any, List

from iconservice.icon_constant import SystemValueType
from iconservice.iconscore.icon_score_step import StepType
from iconservice.system.value import SystemValueConverter
from iconservice.utils.msgpack_for_db import MsgPackForDB


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
    def from_bytes(cls, bytes_: bytes) -> 'StepCosts':
        items: list = MsgPackForDB.loads(bytes_)
        version: int = items[0]
        value: dict = items[1]
        converted_value: dict = {StepType(key): value for key, val in value.items()}

        assert version == 0
        return cls(converted_value)


SYSTEM_DATA_MAPPER = {
    SystemValueType.REVISION_CODE: "",
    SystemValueType.REVISION_NAME: "",
    SystemValueType.SCORE_BLACK_LIST: "",
    SystemValueType.STEP_PRICE: "",
    SystemValueType.STEP_COSTS: StepCosts,
    SystemValueType.MAX_STEP_LIMITS: "",
    SystemValueType.SERVICE_CONFIG: "",
    SystemValueType.IMPORT_WHITE_LIST: ""
}
