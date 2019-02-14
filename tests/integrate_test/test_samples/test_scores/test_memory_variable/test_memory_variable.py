from iconservice import *


class TestMemoryVariable(IconScoreBase):

    def __init__(self, db: IconScoreDatabase) -> None:
        super().__init__(db)
        self._value1 = VarDB('value1', db, value_type=int)
        self._value2 = ArrayDB("value2", db, value_type=int)
        self._value3 = DictDB("value3", db, value_type=int)

    def on_install(self) -> None:
        super().on_install()

    def on_update(self) -> None:
        super().on_update()

    @external(readonly=True)
    def get_value1(self) -> int:
        return self._value1.get()

    @external(readonly=False)
    def set_value1(self, value: int) -> None:
        self._value1 = value

    @external(readonly=False)
    def set_value2(self, value: int) -> None:
        self._value2 = value

    @external(readonly=False)
    def set_value3(self, value: int) -> None:
        self._value3 = value

    @payable
    def fallback(self) -> None:
        print("fallback!!")
