from iconservice import *


class Score(IconScoreBase):

    def __init__(self, db: IconScoreDatabase) -> None:
        super().__init__(db)
        self._bool = VarDB("bool", db, bool)
        self._bytes = VarDB("bytes", db, bytes)
        self._int = VarDB("int", db, int)
        self._str = VarDB("str", db, str)
        self._address = VarDB("Address", db, Address)

    def on_install(self, value: int=0) -> None:
        super().on_install()
        self.__init()

    def on_update(self) -> None:
        super().on_update()
        self.__init()

    def __init(self):
        self._bool.set(False)
        self._bytes.set(b"")
        self._int.set(0)
        self._str.set("")
        self._address.set(Address.from_prefix_and_int(AddressPrefix.EOA, 0))

    @payable
    @external
    def setBool(self, value: bool):
        self._bool.set(value)

    @external(readonly=True)
    def getBool(self) -> bool:
        return self._bool.get()

    @payable
    @external
    def setBytes(self, value: bytes):
        self._bytes.set(value)

    @external(readonly=True)
    def getBytes(self) -> bytes:
        return self._bytes.get()

    @payable
    @external
    def setInt(self, value: int):
        self._int.set(value)

    @external
    def getInt(self) -> int:
        return self._int.get()

    @payable
    @external
    def setStr(self, value: str):
        self._str.set(value)

    @external(readonly=True)
    def getStr(self) -> str:
        return self._str.get()

    @payable
    @external
    def setAddress(self, value: Address):
        self._address.set(value)

    @external(readonly=True)
    def getAddress(self) -> Address:
        return self._address.get()

    @payable
    @external
    def func_payable(self):
        pass

    @external
    def func_non_payable(self):
        pass

    @payable
    def fallback(self) -> None:
        pass
