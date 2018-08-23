from iconservice import *


class TestInterface(InterfaceScore):
    @interface
    def hello(self) -> None: pass


class TestLinkScore(IconScoreBase):
    _SCORE_ADDR = 'score_addr'

    @eventlog(indexed=2)
    def BeforeInstall(self, msg_sender: Address, tx_origin: Address): pass

    @eventlog(indexed=2)
    def AfterInstall(self, msg_sender: Address, tx_origin: Address): pass

    def __init__(self, db: IconScoreDatabase) -> None:
        super().__init__(db)
        self._value = VarDB('value', db, value_type=int)
        self._addr_score = VarDB(self._SCORE_ADDR, db, value_type=Address)

    def on_install(self, score_addr: 'Address' = None) -> None:
        super().on_install()
        self._addr_score.set(score_addr)
        test_interface = self.create_interface_score(self._addr_score.get(), TestInterface)
        self.BeforeInstall(self.msg.sender, self.tx.origin)
        test_interface.hello()
        self.AfterInstall(self.msg.sender, self.tx.origin)

    def on_update(self) -> None:
        super().on_update()

    @external(readonly=True)
    def hello(self) -> str:
        return "hello"

