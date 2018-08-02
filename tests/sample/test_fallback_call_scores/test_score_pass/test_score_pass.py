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
        self._value4 = VarDB('value4', db, value_type=Address)
        self._value5 = VarDB('value5', db, value_type=bool)

    def on_install(self, value: int=0) -> None:
        super().on_install()

    def on_update(self) -> None:
        super().on_update()

    @external(readonly=True)
    def get_value1(self) -> int:
        return self._value1.get()

    @external(readonly=False)
    def set_value1(self, value: int) -> None:
        self._value1.set(value)

    @external(readonly=True)
    def get_value2(self) -> str:
        return self._value2.get()

    @external(readonly=False)
    def set_value2(self, value: str) -> None:
        self._value2.set(value)

    @external(readonly=True)
    def get_value3(self) -> bytes:
        return self._value3.get()

    @external(readonly=False)
    def set_value3(self, value: bytes) -> None:
        self._value3.set(value)

    @external(readonly=True)
    def get_value4(self) -> Address:
        return self._value4.get()

    @external(readonly=False)
    def set_value4(self, value: Address) -> None:
        self._value4.set(value)

    @external(readonly=True)
    def get_value5(self) -> bool:
        return self._value5.get()

    @external(readonly=False)
    def set_value5(self, value: bool) -> None:
        self._value5.set(value)

    @payable
    def fallback(self) -> None:
        print("fallback!!")
