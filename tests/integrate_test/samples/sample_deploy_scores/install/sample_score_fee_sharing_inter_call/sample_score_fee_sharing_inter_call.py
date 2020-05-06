from iconservice import *


class SampleInterface(InterfaceScore):
    @interface
    def set_value(self, value: int, proportion: int = 0) -> None:
        pass


class SampleScoreFeeSharingInterCall(IconScoreBase):
    @eventlog(indexed=1)
    def Changed(self, value: int):
        pass

    def __init__(self, db: IconScoreDatabase) -> None:
        super().__init__(db)
        self._score_address = VarDB("score", db, value_type=Address)
        self._value = VarDB("value", db, value_type=int)

    def on_install(self, score_address: Address, value: int = 1000) -> None:
        super().on_install()
        self._value.set(value)
        self._score_address.set(score_address)

    def on_update(self) -> None:
        super().on_update()

    @external(readonly=True)
    def hello(self) -> str:
        return "Hello"

    @external(readonly=True)
    def get_value(self) -> int:
        return self._value.get()

    @external
    def set_value(self, value: int, proportion: int = 0):
        self.set_fee_sharing_proportion(proportion)
        self._value.set(value)
        self.Changed(value)

    @external
    def set_other_score_value(
        self, value: int, proportion: int, other_score_proportion: int
    ):
        self.set_fee_sharing_proportion(proportion)
        score = self.create_interface_score(self._score_address.get(), SampleInterface)
        score.set_value(value, other_score_proportion)
