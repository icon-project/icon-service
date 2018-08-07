from iconservice import *


class TestLinkScoreSend(IconScoreBase):
    _EOA_ADDR1 = 'eoa_addr1'
    _EOA_ADDR2 = 'eoa_addr2'

    @eventlog(indexed=1)
    def Changed(self, value: int):
        pass

    def __init__(self, db: IconScoreDatabase) -> None:
        super().__init__(db)
        self._value = VarDB('value', db, value_type=int)
        self._addr_eoa1 = VarDB(self._EOA_ADDR1, db, value_type=Address)
        self._addr_eoa2 = VarDB(self._EOA_ADDR2, db, value_type=Address)

    def on_install(self, value: int=0) -> None:
        super().on_install()
        self._value.set(value)

    def on_update(self) -> None:
        super().on_update()

    @external(readonly=False)
    def add_user_addr1(self, eoa_addr: Address) -> None:
        self._addr_eoa1.set(eoa_addr)

    @external(readonly=False)
    def add_user_addr2(self, eoa_addr: Address) -> None:
        self._addr_eoa2.set(eoa_addr)

    @payable
    def fallback(self) -> None:
        amount = self.msg.value
        target1 = self._addr_eoa1.get()
        target2 = self._addr_eoa2.get()
        value = int(amount / 2)
        result1 = self.icx.send(target1, value)
        result2 = self.icx.send(target2, value)
