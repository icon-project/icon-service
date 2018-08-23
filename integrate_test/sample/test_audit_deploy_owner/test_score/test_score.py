from iconservice import *


class TestScore(IconScoreBase):

    @eventlog(indexed=2)
    def Hello(self, msg_sender: Address, tx_origin: Address): pass

    def __init__(self, db: IconScoreDatabase) -> None:
        super().__init__(db)

    def on_install(self) -> None:
        super().on_install()

    def on_update(self) -> None:
        super().on_update()

    @external
    def hello(self) -> None:
        self.Hello(self.msg.sender, self.tx.origin)
        print('hello')
