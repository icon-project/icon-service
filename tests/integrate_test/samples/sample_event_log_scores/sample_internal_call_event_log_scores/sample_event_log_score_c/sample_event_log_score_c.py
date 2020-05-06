from iconservice import *


class SampleEventLogScoreC(IconScoreBase):
    @eventlog
    def EventLogC(self, score_name: str):
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
    def called_by_score_b(self):
        self.EventLogC("C")
