from iconservice import *


class TestScorePass(IconScoreBase):

    @eventlog(indexed=1)
    def Changed(self, value: int):
        pass

    def __init__(self, db: IconScoreDatabase) -> None:
        super().__init__(db)
        self._value1 = VarDB('value1', db, value_type=int)
        self._value2 = VarDB('value2', db, value_type=str)
        self._value3 = VarDB('value3', db, value_type=bytes)
        self._value4 = VarDB('value3', db, value_type=Address)
        self._value5 = VarDB('value1', db, value_type=bool)

    def on_install(self, value: int=0) -> None:
        super().on_install()
        # self._value.set(value)

    def on_update(self) -> None:
        super().on_update()

    @external(readonly=True)
    def get_value1(self) -> int:
        return self._value1.get()

    @external(readonly=True)
    def get_value2(self) -> str:
        return self._value2.get()

    @external(readonly=True)
    def get_value3(self) -> bytes:
        return self._value3.get()

    @external(readonly=True)
    def get_value4(self) -> Address:
        return self._value4.get()

    @external(readonly=True)
    def get_value5(self) -> bool:
        return self._value5.get()

    @payable
    def fallback(self) -> None:
        print("fallback!!")
