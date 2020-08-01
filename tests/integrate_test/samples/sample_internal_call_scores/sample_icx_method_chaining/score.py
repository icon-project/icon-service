from iconservice import *


class SampleInterface(InterfaceScore):
    @interface(payable=True)
    def set_value(self, value: int) -> None: pass


class Score(IconScoreBase):
    _SCORE_ADDR = 'score_addr'

    @eventlog(indexed=1)
    def Changed(self, value: int):
        pass

    def __init__(self, db: IconScoreDatabase) -> None:
        super().__init__(db)
        self._value = VarDB('value', db, value_type=int)
        self._addr_score = VarDB(self._SCORE_ADDR, db, value_type=Address)

    def on_install(self, value: int=0) -> None:
        super().on_install()
        self._value.set(value)

    def on_update(self) -> None:
        super().on_update()

    @external(readonly=False)
    def add_score_func(self, score_addr: Address) -> None:
        self._addr_score.set(score_addr)

    @external
    def set_value(self, value: int):
        test_interface = self.create_interface_score(self._addr_score.get(), SampleInterface)
        test_interface.icx(100).set_value(value)
        self.Changed(value)
