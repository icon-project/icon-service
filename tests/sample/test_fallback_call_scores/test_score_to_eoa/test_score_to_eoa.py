from iconservice import *


class TestScoreToEoa(IconScoreBase):
    _ADDR = 'addr'

    @eventlog(indexed=1)
    def Changed(self, value: int):
        pass

    def __init__(self, db: IconScoreDatabase) -> None:
        super().__init__(db)
        self._value = VarDB('value', db, value_type=int)
        self._addr = VarDB(self._ADDR, db, value_type=Address)

    def on_install(self, value: int=0) -> None:
        super().on_install()
        self._value.set(value)

    def on_update(self) -> None:
        super().on_update()

    @external(readonly=False)
    def set_addr_func(self, addr: Address) -> None:
        self._addr.set(addr)

    @payable
    def fallback(self) -> None:
        amount = self.msg.value
        addr = self._addr.get()
        self.icx.transfer(addr, amount)
