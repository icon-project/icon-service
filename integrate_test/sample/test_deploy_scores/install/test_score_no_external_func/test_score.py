# No external functions in SCORE

from iconservice import *


class TestScore(IconScoreBase):

    @eventlog(indexed=1)
    def Changed(self, value: int):
        pass

    def __init__(self, db: IconScoreDatabase) -> None:
        super().__init__(db)
        self._value = VarDB('value', db, value_type=int)

    def on_install(self, value: int) -> None:
        super().on_install()
        self._value.set(value)

    def on_update(self) -> None:
        super().on_update()

    def hello(self) -> str:
        return "Hello"

    def get_value(self) -> int:
        return self._value.get()

    def set_value(self, value: int):
        self._value.set(value)
        self.Changed(value)