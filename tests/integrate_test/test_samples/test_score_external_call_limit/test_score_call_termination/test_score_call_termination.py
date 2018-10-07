from iconservice import *


class TestScoreCallTermination(IconScoreBase):

    def __init__(self, db: IconScoreDatabase) -> None:
        super().__init__(db)
        self._value = VarDB('value', db, value_type=int)

    def on_install(self) -> None:
        super().on_install()

    def on_update(self) -> None:
        super().on_update()

    @external
    def invoke(self) -> None:
        self._value.set(self._value.get() + 1)

    @external(readonly=True)
    def query(self) -> int:
        return 1

    @external(readonly=True)
    def getValue(self) -> int:
        return self._value.get()
