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

    def on_update(self, value: int) -> None:
        super().on_update()
        var = self._value.get()
        self._value.set(var + value)

    @external(readonly=True)
    def hello(self) -> str:
        return "Hello"

    @external(readonly=True)
    def get_value(self) -> int:
        return self._value.get()

    @external
    def set_value(self, value: int):
        self._value.set(value * 2)
        self.Changed(value)
