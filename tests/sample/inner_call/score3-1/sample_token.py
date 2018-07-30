from iconservice import *


class SampleToken1(IconScoreBase):
    _TEST = 'test'

    def __init__(self, db: IconScoreDatabase) -> None:
        super().__init__(db)
        self._value = VarDB(self._TEST, db, value_type=int)

    def on_install(self) -> None:
        super().on_install()

    def on_update(self) -> None:
        super().on_update()

    @external(readonly=True)
    def hello(self) -> str:
        print(f'Hello, world!')
        return "Hello"

    @external(readonly=False)
    def writable_func(self, value: int) -> None:
        self._value.set(value)

    @external(readonly=True)
    def readonly_func(self) -> int:
        return self._value.get()

