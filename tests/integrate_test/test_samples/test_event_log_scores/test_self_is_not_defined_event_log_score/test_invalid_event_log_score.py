from iconservice import *


class TestInvalidEventLogScore(IconScoreBase):
    @eventlog
    def EventLogWithOutSelf(value: str):
        pass

    @eventlog(indexed=1)
    def EventLogWithOutSelf(value: str):
        pass


    def __init__(self, db: IconScoreDatabase) -> None:
        super().__init__(db)
        self._value = VarDB('value', db, value_type=str)

    def on_install(self, value: str="default") -> None:
        super().on_install()
        self.set_value(value)

    def on_update(self) -> None:
        super().on_update()

    @external
    def call_event_log_self_is_not_defined(self):
        self.EventLogWithOutSelf("test")
