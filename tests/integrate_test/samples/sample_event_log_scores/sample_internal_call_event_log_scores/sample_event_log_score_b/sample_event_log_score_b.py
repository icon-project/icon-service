from iconservice import *

class ScoreCInterFace(InterfaceScore):
    @interface
    def called_by_score_b(self) -> None: pass

class SampleEventLogScoreB(IconScoreBase):
    @eventlog
    def EventLogB(self, score_name: str):
        pass

    def __init__(self, db: IconScoreDatabase) -> None:
        super().__init__(db)
        self._value = VarDB('value', db, value_type=str)

    def on_install(self, value: str="default") -> None:
        super().on_install()
        self.set_value(value)

    def on_update(self) -> None:
        super().on_update()

    @external(readonly=True)
    def get_value(self) -> str:
        return self._value.get()

    @external
    def set_value(self, value: str):
        self._value.set(value)

    @external
    def called_by_score_a(self):
        self.EventLogB("B")

    @external(readonly=True)
    def read_only_method_called_by_score_a(self) -> str:
        self.EventLogB("B")
        return "B"

    @external(readonly=True)
    def read_only_method_call_score_c(self, score_addr_c: Address) -> str:
        score_c = self.create_interface_score(score_addr_c, ScoreCInterFace)
        score_c.called_by_score_b()
        return "BC"

