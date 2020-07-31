from iconservice import *


class SampleInterface(InterfaceScore):
    @interface
    def func_params_int_with_icx(self, value: int, amount: icxunit.Loop): pass

    @interface
    def func_params_str_with_icx(self, value: str, amount: icxunit.Loop): pass

    @interface
    def first_order_with_icx(self, amount: icxunit.Loop, invalid_value: int): pass


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

    @external
    def test_func_params_int_with_icx(self, value: int, amount: int):
        test_interface = self.create_interface_score(self._addr_score.get(), SampleInterface)
        test_interface.func_params_int_with_icx(value=value, amount=icxunit.Loop(amount))

    @external
    def test_func_params_int_with_icx(self, value: str, amount: int):
        test_interface = self.create_interface_score(self._addr_score.get(), SampleInterface)
        test_interface.func_params_str_with_icx(value=value, amount=icxunit.Loop(amount))

    @external
    def test_first_order_with_icx(self, value: int, amount: int):
        test_interface = self.create_interface_score(self._addr_score.get(), SampleInterface)
        test_interface.first_order_with_icx(
            value=value,
            amount=icxunit.Loop(amount)
        )

    @payable
    def fallback(self) -> None:
        pass
