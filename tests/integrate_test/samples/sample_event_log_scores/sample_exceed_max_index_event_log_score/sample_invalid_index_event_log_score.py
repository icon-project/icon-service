from iconservice import *


class SampleInvalidIndexEventLogScore(IconScoreBase):
    @eventlog(indexed=4)
    def EventLogIndexExceedLimit(
        self, value1: str, value2: str, value3: str, value4: str
    ):
        pass

    def __init__(self, db: IconScoreDatabase) -> None:
        super().__init__(db)
        self._value = VarDB("value", db, value_type=str)

    def on_install(self, value: str = "default") -> None:
        super().on_install()
        self.set_value(value)

    def on_update(self) -> None:
        super().on_update()

    @external(readonly=True)
    def get_value(self) -> str:
        return self._value.get()

    @external
    def set_value(self, value: str):
        self._value.set(value)

    @external
    def call_event_log_index_exceed_limit(self):
        self.EventLogIndexExceedLimit("1", "2", "3", "4")
