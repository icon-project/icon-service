from iconservice import *


class TestDefaultValue(IconScoreBase):

    @eventlog(indexed=1)
    def Changed(self, value: int):
        pass

    def __init__(self, db: IconScoreDatabase) -> None:
        super().__init__(db)
        self._value1 = VarDB('value1', db, value_type=Address)

    def on_install(self, value: 'Address' = None, value1: Address = None, value2: int = None) -> None:
        super().on_install()
        print(value, value1, value2)

    def on_update(self, value: 'Address' = "aaa", value1: Address = None, value2: int = None) -> None:
        super().on_update()
        print(value, value1, value2)

    @external(readonly=True)
    def get_value1(self) -> int:
        return self._value1.get()

    @external(readonly=False)
    def set_value1(self, value: int = None) -> None:
        print(value)
        self._value1.set(value)
