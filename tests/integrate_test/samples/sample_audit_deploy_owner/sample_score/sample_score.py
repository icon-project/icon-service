from iconservice import *


class SampleScore(IconScoreBase):

    @eventlog(indexed=1)
    def Hello(self, msg_sender: Address): pass

    def __init__(self, db: IconScoreDatabase) -> None:
        super().__init__(db)

    def on_install(self) -> None:
        super().on_install()

    def on_update(self) -> None:
        super().on_update()

    @external
    def hello(self) -> None:
        self.Hello(self.msg.sender)
        print('hello')
