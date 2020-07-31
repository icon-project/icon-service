from iconservice import *


class SampleInterface(InterfaceScore):
    @interface
    def func(self, value1: icxunit.Loop): pass


class SampleLinkScore(IconScoreBase):
    _SCORE_ADDR = 'score_addr'

    def __init__(self, db: IconScoreDatabase) -> None:
        super().__init__(db)
        self._value = VarDB('value', db, value_type=int)
        self._addr_score = VarDB(self._SCORE_ADDR, db, value_type=Address)

    def on_install(self, value: int=0) -> None:
        super().on_install()
        self._value.set(value)

    def on_update(self) -> None:
        super().on_update()

    @external
    def add_score_func(self, score_addr: Address):
        self._addr_score.set(score_addr)

    @payable
    def fallback(self) -> None:
        pass
