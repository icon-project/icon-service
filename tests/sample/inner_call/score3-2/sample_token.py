from iconservice import *


class TestInterface(InterfaceScore):
    @interface
    def writable_func(self, value: int) -> None: pass

    @interface
    def readonly_func(self) -> int: pass


class SampleToken2(IconScoreBase):
    _TEST = 'test'
    _SCORE_ADDR = 'score_addr'
    _TEST2 = 'test2'

    def __init__(self, db: IconScoreDatabase) -> None:
        super().__init__(db)
        self._value = VarDB(self._TEST, db, value_type=int)
        self._addr_score = VarDB(self._SCORE_ADDR, db, value_type=Address)
        self._test_value = VarDB(self._TEST, db, value_type=int)

    def on_install(self) -> None:
        super().on_install()

    def on_update(self) -> None:
        super().on_update()

    @external(readonly=False)
    def add_score_func(self, score_addr: Address) -> None:
        self._addr_score.set(score_addr)

    @external(readonly=False)
    def writable_func(self, value: int) -> None:
        test_interface = self.create_interface_score(self._addr_score.get(), TestInterface)
        test_interface.writable_func(value)
        test_interface.readonly_func()

    @external(readonly=True)
    def readonly_func1(self) -> int:
        test_interface = self.create_interface_score(self._addr_score.get(), TestInterface)
        test_interface.writable_func(10)
        ret = test_interface.readonly_func()
        return ret

    @external(readonly=True)
    def readonly_func2(self) -> int:
        test_interface = self.create_interface_score(self._addr_score.get(), TestInterface)
        ret = test_interface.readonly_func()
        return ret

