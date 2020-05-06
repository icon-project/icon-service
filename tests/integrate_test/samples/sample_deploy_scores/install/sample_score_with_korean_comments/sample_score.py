from iconservice import *

# 주석 종류도 여러개로 하자


class TestScore(IconScoreBase):
    """한글로 주석을 달면 무슨 일이 발생할까?
    """

    @eventlog(indexed=1)
    def Changed(self, value: int):
        pass

    def __init__(self, db: IconScoreDatabase) -> None:
        super().__init__(db)
        self._value = VarDB("value", db, value_type=int)

    def on_install(self, value: int) -> None:
        super().on_install()
        self._value.set(value)

    def on_update(self) -> None:
        super().on_update()

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
