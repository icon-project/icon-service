from iconservice import *


class SampleScore(IconScoreBase):
    def __init__(self, db: IconScoreDatabase) -> None:
        super().__init__(db)
        self._value = VarDB('value', db, value_type=int)

    def on_install(self, value: int=0) -> None:
        super().on_install()
        self._value.set(value)

    def on_update(self) -> None:
        super().on_update()

    @external
    @payable
    def func_params_icxunit_loop_with_icx(self, value: icxunit.Loop):
        pass
