from iconservice import *


class TestWrongRevert(IconScoreBase):
    def __init__(self, db: IconScoreDatabase) -> None:
        super().__init__(db)
        self._value1 = VarDB('value1', db, value_type=int)

    def on_install(self) -> None:
        super().on_install()

    def on_update(self) -> None:
        super().on_update()

    @external(readonly=True)
    def get_value1(self) -> int:
        return self._value1.get()

    @external(readonly=False)
    def set_value1(self, value: int) -> None:
        revert(None, "wrong")
        self._value1.set(value)

    @payable
    def fallback(self) -> None:
        print("fallback!!")
