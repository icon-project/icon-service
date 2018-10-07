from iconservice import *

class ScoreBInterFace(InterfaceScore):
    @interface
    def called_by_score_a(self) -> None: pass

    @interface
    def read_only_method_called_by_score_a(self) -> str: pass

    @interface
    def read_only_method_call_score_c(self) -> str: pass

class TestEventLogScoreA(IconScoreBase):
    @eventlog
    def EventLogA(self, score_name: str):
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
    def call_score_b_event_log_interface_call(self, addr: Address):
        self.EventLogA("A")
        score_b = self.create_interface_score(addr, ScoreBInterFace)
        score_b.called_by_score_a()

    @external
    def call_score_b_event_log_call(self, addr: Address):
        self.EventLogA("A")
        self.call(addr_to=addr,
                  func_name="called_by_score_a",
                  kw_dict={})

    @external
    def call_score_b_read_only_method(self, addr: Address):
        self.EventLogA("A")
        score_b = self.create_interface_score(addr, ScoreBInterFace)
        score_b.read_only_method_called_by_score_a()

    @external
    def call_score_b_to_score_c_event_log(self, score_addr_b: Address, score_addr_c: Address):
        self.EventLogA("A")
        score_b = self.create_interface_score(score_addr_b, ScoreBInterFace)
        score_b.read_only_method_call_score_c(score_addr_c)
