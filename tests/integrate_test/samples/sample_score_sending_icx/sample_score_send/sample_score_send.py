from iconservice import *


class SampleScoreSend(IconScoreBase):
    _SCORE_ADDR = "score_addr"

    @eventlog(indexed=1)
    def SendResult(self, result: bool):
        pass

    @eventlog(indexed=2)
    def MsgCheck(self, before: Address, after: Address):
        pass

    @eventlog(indexed=1)
    def TransferResult(self, has_result: bool):
        pass

    def __init__(self, db: IconScoreDatabase) -> None:
        super().__init__(db)

    def on_install(self) -> None:
        super().on_install()

    def on_update(self) -> None:
        super().on_update()

    @payable
    @external
    def send(self, _to: Address, _amount: int) -> None:
        msg_sender_before = self.msg.sender
        result = self.icx.send(_to, _amount)
        msg_sender_after = self.msg.sender
        self.SendResult(result)
        self.MsgCheck(msg_sender_before, msg_sender_after)

    @payable
    @external
    def transfer(self, _to: Address, _amount: int) -> None:
        msg_sender_before = self.msg.sender
        result = self.icx.transfer(_to, _amount)
        msg_sender_after = self.msg.sender
        self.TransferResult(result is not None)
        self.MsgCheck(msg_sender_before, msg_sender_after)
