import abc
from iconservice import *


class TokenScoreInterface(InterfaceScore):
    """
    Interface of called contract, when transfer the coin to other contract.
    """
    @interface
    def tokenFallback(self, from_addr: Address, value: int, message: str):
        pass


class IRC2Basic(abc.ABC):
    @abc.abstractmethod
    def name(self) -> str:
        pass

    @abc.abstractmethod
    def symbol(self) -> str:
        pass

    @abc.abstractmethod
    def decimals(self) -> int:
        pass

    @abc.abstractmethod
    def totalSupply(self) -> int:
        pass

    @abc.abstractmethod
    def balanceOf(self, _owner: Address) -> int:
        pass

    @abc.abstractmethod
    def transfer(self, _to: Address, _value: int, _message: str = None) -> bool:
        pass


class BasicToken(IconScoreBase, IRC2Basic):
    """
        Basic version of StandardToken, with no allowances.
        support IRC2 Protocol (based on ERC223 and ERC20)
    """
    __DBKEY_BALANCES = 'balances'
    __DBKEY_TOTAL_SUPPLY = 'total_supply'
    __DBKEY_DECIMALS = 'decimals'
    __DBKEY_NAME = 'name'
    __DBKEY_SYMBOL = 'symbol'

    @eventlog(indexed=3)
    def Transfer(self, from_addr: Address, to_addr: Address, value: int, message: str):
        pass

    def __init__(self, db: IconScoreDatabase) -> None:
        super().__init__(db)
        self._balances = DictDB(self.__DBKEY_BALANCES, db, value_type=int)
        self._total_supply = VarDB(self.__DBKEY_TOTAL_SUPPLY, db, value_type=int)
        self._decimals = VarDB(self.__DBKEY_DECIMALS, db, value_type=int)
        self._name = VarDB(self.__DBKEY_NAME, db, value_type=str)
        self._symbol = VarDB(self.__DBKEY_SYMBOL, db, value_type=str)

    def on_install(self, decimals: int = 18, name: str = None, symbol: str = None, message: str = None) -> None:
        super().on_install()

        if name is None:
            name = 'LinkCoin'
        if symbol is None:
            symbol = 'LNK'

        if isinstance(decimals, str):
            if decimals.startswith('0x'):
                decimals = int(decimals, 16)
            else:
                decimals = int(decimals)

        self._decimals.set(decimals)
        self._name.set(name)
        self._symbol.set(symbol)
        Logger.debug(f"BasicToken called on_install decimals : {decimals}, {self._decimals.get()}, "
                     f"name : {name}, {self._name.get()}, symbol : {symbol}, {self._symbol.get()}")

    def on_update(self, **kwargs) -> None:
        super().on_update(**kwargs)

    def _transfer(self, from_addr: Address, to_addr: Address, value: int, message: str) -> bool:
        if from_addr == to_addr or value < 0:
            self.revert(f"invalid parameter")
        if self._balances[from_addr] < value:
            self.revert(f"User balance is not enough")

        self._balances[from_addr] -= value
        self._balances[to_addr] += value

        if to_addr.is_contract:
            token_score = self.create_interface_score(to_addr, TokenScoreInterface)
            token_score.tokenFallback(from_addr, value, message)

        self.Transfer(from_addr, to_addr, value, message)
        Logger.debug(f"transfer {from_addr} -> {to_addr}, value : {value}, message : {message}")
        return True

    @external(readonly=True)
    def totalSupply(self) -> int:
        return self._total_supply.get()

    @external(readonly=True)
    def balanceOf(self, owner: Address) -> int:
        return self._balances[owner]

    @external(readonly=True)
    def decimals(self) -> int:
        return self._decimals.get()

    @external
    def transfer(self, to_addr: Address, value: int, message: str = None) -> bool:
        if message is None:
            message = 'None'

        return self._transfer(self.msg.sender, to_addr, value, message)

    @external(readonly=True)
    def name(self) -> str:
        return self._name.get()

    @external(readonly=True)
    def symbol(self) -> str:
        return self._symbol.get()
