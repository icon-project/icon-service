from iconservice import *
from .standard_token_support_blacklist import StandardTokenSupportBlacklist, only_operator
from .ownership.role import Role
from .ownership.ownable import only_owner


class LinkExchangerInterface(InterfaceScore):
    @interface
    def exchange(self, fromServiceName: str, toServiceName: str, to: Address, value: int) -> bool:
        pass

    @interface
    def addContract(self, score: Address):
        pass


LinkCoinScore_Version = "0.4.0"


class LinkCoin(StandardTokenSupportBlacklist):
    __DBKEY_SERVICE_OPERATORS = 'service_operators'
    __DBKEY_MINTABLE_OPERATORS = 'mintable_operators'
    __ROLE_SERVICE_OPERATOR = 'service_operator'
    __DBKEY_LINK_EXCHANGER = 'link_exchanger'

    @eventlog(indexed=2)
    def Mint(self, operator: Address, amount: int, message: str):
        pass

    @eventlog(indexed=2)
    def Burn(self, who: Address, value: int, message: str):
        pass

    @eventlog(indexed=3)
    def ExchangeTo(self, serviceName: str, fromAddr: Address, toAddr: Address, value: int):
        pass

    @eventlog(indexed=3)
    def ExchangeFrom(self, serviceName: str, fromAddr: Address, toAddr: Address, value: int):
        pass

    def __init__(self, db: IconScoreDatabase) -> None:
        super().__init__(db)
        self._service_operator = Role(db, self.__ROLE_SERVICE_OPERATOR)
        self._mintable_operators = DictDB(self.__DBKEY_MINTABLE_OPERATORS, db, value_type=bool)
        self._exchanger_address = VarDB(self.__DBKEY_LINK_EXCHANGER, db, value_type=Address)

        self.__exchanger = self.create_interface_score(self._exchanger_address.get(), LinkExchangerInterface)

    def on_install(self, exchangerAddress: Address = None, decimals: int = 18, name: str = None,
                   symbol: str = None, message: str = None) -> None:
        super().on_install(decimals=decimals, name=name, symbol=symbol, message=message)

        if exchangerAddress is not None:
            Logger.debug(f"LinkCoin __init__ exchangerAddress : {exchangerAddress}, type : {type(exchangerAddress)}")
            self._exchanger_address.set(exchangerAddress)
            self.__exchanger = self.create_interface_score(exchangerAddress, LinkExchangerInterface)
        Logger.debug(f"LinkCoin on_install self address : {self.address}")

    def __is_operator(self, who: Address) -> bool:
        return self._service_operator.has(who)

    def __can_mint(self, operator: Address) -> bool:
        return self._mintable_operators[operator]

    @only_operator
    @external
    def addServiceOperator(self, operator: Address, message: str = None) -> bool:
        if not isinstance(operator, Address) or operator.is_contract:
            self.revert("The service operator is invalid")

        if self.__is_operator(operator):
            return False

        self._service_operator.add(operator)
        Logger.debug(f"add {operator} operator.")
        return True

    @only_operator
    @external
    def removeServiceOperator(self, operator: Address, message: str = None) -> bool:
        if not isinstance(operator, Address) or operator.is_contract:
            self.revert("The service operator is invalid")

        if not self.__is_operator(operator):
            return False

        self._service_operator.remove(operator)

    @only_operator
    @external
    def enableMint(self, operator: Address, message: str = None) -> bool:
        if not self.__is_operator(operator):
            self.revert(f"'{operator}' is not service operator.")

        self._mintable_operators[operator] = True
        return True

    @only_operator
    @external
    def disableMint(self, operator: Address, message: str = None) -> bool:
        if not self.__is_operator(operator):
            self.revert(f"'{operator}' is not service operator.")

        self._mintable_operators[operator] = False
        return True

    @only_operator
    @external
    def mintToken(self, operator: Address, value: int, message: str = None) -> bool:
        if not self.__is_operator(operator):
            self.revert(f"{operator} doesn't have mint permission.")

        if not self.__can_mint(operator):
            self.revert(f"{operator} can't mint")

        if message is None:
            message = 'None'

        self._balances[operator] = self._balances[operator] + value
        self._total_supply.set(self._total_supply.get() + value)
        self._mintable_operators[operator] = False

        self.Mint(operator, value, message)
        self.Transfer(self.msg.sender, operator, value, message)

        return True

    def __burn(self, who: Address, value: int, message: str):
        if self._balances[who] < value:
            self.revert(f"User balance is not enough")

        self._balances[who] -= value
        self._total_supply.set(self._total_supply.get() - value)

        self.Burn(who, value, message)
        self.Transfer(who, ZERO_SCORE_ADDRESS, value, message)

    @external
    def burn(self, value: int, message: str = None):
        if message is None:
            message = 'None'

        self.__burn(self.msg.sender, value, message)

    @external(readonly=True)
    def version(self) -> str:
        return LinkCoinScore_Version

    @only_owner
    @external
    def setExchangerAddress(self, score: Address):
        try:
            exchanger_address = self._exchanger_address.get()
        except ValueError:
            revert(f"The exchanger address is already setted.")
        else:
            if exchanger_address is not None:
                revert(f"The exchanger address is already setted.")

        self.__exchanger = self.create_interface_score(score, LinkExchangerInterface)
        self._exchanger_address.set(score)

    @external
    def exchangeFrom(self, serviceName: str, to: Address, value: int) -> bool:
        if self.msg.sender != self._exchanger_address.get():
            self.revert(f"The caller contract cannot be trusted.")

        if value < 0 or self.name() == serviceName:
            self.revert(f"Invalid parameters.")

        self._balances[to] += value
        self._total_supply.set(self._total_supply.get() + value)

        self.ExchangeFrom(serviceName, self.tx.origin, to, value)

        return True

    @external
    def exchangeTo(self, serviceName: str, to: Address, value: int) -> bool:
        from_addr = self.msg.sender
        if value < 0:
            self.revert("invalid parameters.")
        if self._balances[from_addr] < value:
            self.revert(f"User balance is not enough.")

        self._balances[from_addr] -= value
        self._total_supply.set(self._total_supply.get() - value)

        exchanger = self.create_interface_score(self._exchanger_address.get(), LinkExchangerInterface)
        exchanger.exchange(self.name(), serviceName, to, value)

        self.ExchangeTo(serviceName, from_addr, to, value)

        return True
