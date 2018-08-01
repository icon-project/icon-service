from iconservice import *


class TestScore(object):

    @eventlog(indexed=1)
    def Changed(self, value: int):
        pass

    def __init__(self, db: IconScoreDatabase) -> None:
        self._value = VarDB('value', db, value_type=int)

    def on_install(self, value: int) -> None:
        self._value.set(value)

    def on_update(self) -> None:
        pass

    @external(readonly=True)
    def hello(self) -> str:
        return "Hello"

    @external(readonly=True)
    def get_value(self) -> int:
        return self._value.get()

    @external
    def set_value(self, value: int):
        self._value.set(value)
        self.Changed(value)