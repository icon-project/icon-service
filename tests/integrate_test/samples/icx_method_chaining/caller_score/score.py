from iconservice import *


class CalleeInterface(InterfaceScore):
    @interface
    def setBool(self, value: bool): pass

    @interface
    def getBool(self) -> bool: pass

    @interface
    def setBytes(self, value: bool): pass

    @interface
    def getBytes(self) -> bytes: pass

    @interface
    def setInt(self, value: int): pass

    @interface
    def getInt(self) -> int: pass

    @interface
    def setStr(self, value: str): pass

    @interface
    def getStr(self) -> str: pass

    @interface
    def setAddress(self, value: Address): pass

    @interface
    def getAddress(self) -> Address: pass

    @interface
    def func_payable(self): pass

    @interface
    def func_non_payable(self): pass


class Score(IconScoreBase):

    def __init__(self, db: IconScoreDatabase) -> None:
        super().__init__(db)
        self._address = VarDB("address", db, value_type=Address)

    def on_install(self) -> None:
        super().on_install()

    def on_update(self) -> None:
        super().on_update()

    @external
    def setAddress(self, address: Address):
        self._address.set(address)

    @payable
    @external
    def setBool(self, value: bool):
        callee = self._get_callee()
        callee.icx(self.msg.value).setBool(value)

    @payable
    @external
    def setBytes(self, value: bytes):
        callee = self._get_callee()
        callee.icx(self.msg.value).setBytes(value)

    @payable
    @external
    def setInt(self, value: int):
        callee = self._get_callee()
        callee.icx(self.msg.value).setInt(value)

    @payable
    @external
    def setStr(self, value: str):
        callee = self._get_callee()
        callee.icx(self.msg.value).setStr(value)

    @payable
    @external
    def setAddress(self, value: Address):
        callee = self._get_callee()
        callee.icx(self.msg.value).setAddress(value)

    @payable
    @external
    def func_payable(self):
        callee = self._get_callee()
        callee.icx(self.msg.value).func_payable()

    @payable
    @external
    def func_non_payable(self):
        callee = self._get_callee()
        callee.icx(self.msg.value).func_non_payable()

    def _get_callee(self) -> CalleeInterface:
        address = self._address.get()
        return self.create_interface_score(address, CalleeInterface)

    @payable
    def fallback(self) -> None:
        pass
