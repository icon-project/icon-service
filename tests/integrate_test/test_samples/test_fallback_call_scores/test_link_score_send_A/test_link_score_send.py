from iconservice import *


class TestLinkScoreSend(IconScoreBase):
    _EOA_ADDR = 'eoa_addr'
    _SCORE_ADDR = 'score_addr'

    @eventlog(indexed=1)
    def Changed(self, value: int):
        pass

    def __init__(self, db: IconScoreDatabase) -> None:
        super().__init__(db)
        self._value = VarDB('value', db, value_type=int)
        self._addr_eoa = VarDB(self._EOA_ADDR, db, value_type=Address)
        self._addr_score = VarDB(self._SCORE_ADDR, db, value_type=Address)

    def on_install(self, value: int=0) -> None:
        super().on_install()
        self._value.set(value)

    def on_update(self) -> None:
        super().on_update()

    @external(readonly=False)
    def add_user_addr(self, eoa_addr: Address) -> None:
        self._addr_eoa.set(eoa_addr)

    @external(readonly=False)
    def add_score_addr(self, score_addr: Address) -> None:
        self._addr_score.set(score_addr)

    @payable
    def fallback(self) -> None:
        amount = self.msg.value
        target1 = self._addr_score.get()
        target2 = self._addr_eoa.get()
        value = int(amount / 2)
        result1 = self.icx.send(target1, value)
        result2 = self.icx.send(target2, value)
