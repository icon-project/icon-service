from iconservice import *


class SampleScoreRevert(IconScoreBase):
    @eventlog(indexed=1)
    def Changed(self, value: int):
        pass

    def __init__(self, db: IconScoreDatabase) -> None:
        super().__init__(db)
        self._value = VarDB("value", db, value_type=int)

    def on_install(self, value: int = 0) -> None:
        super().on_install()
        self._value.set(value)

    def on_update(self) -> None:
        super().on_update()

    @external(readonly=True)
    def get_value(self) -> int:
        return self._value.get()

    @payable
    def fallback(self) -> None:
        self.revert("fallback!!")
