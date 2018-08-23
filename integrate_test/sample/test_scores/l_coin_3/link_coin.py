from iconservice import *
from .standard_token_support_blacklist import StandardTokenSupportBlacklist, only_operator
from .ownership.role import Role


class LinkCoin(StandardTokenSupportBlacklist):
    __DBKEY_SERVICE_OPERATORS = 'service_operators'
    __DBKEY_MINTABLE_OPERATORS = 'mintable_operators'
    __ROLE_SERVICE_OPERATOR = 'service_operator'

    @eventlog(indexed=3)
    def Mint(self, operator: Address, amount: int, message: str = None):
        pass

    @eventlog(indexed=2)
    def Burn(self, who: Address, value: int):
        pass

    def __init__(self, db: IconScoreDatabase) -> None:
        super().__init__(db)
        self._service_operator = Role(db, self.__ROLE_SERVICE_OPERATOR)
        self._mintable_operators = DictDB(self.__DBKEY_MINTABLE_OPERATORS, db, value_type=bool)

    def _is_operator(self, who: Address) -> bool:
        return self._service_operator.has(who)

    def _can_mint(self, operator: Address) -> bool:
        return self._mintable_operators[operator]

    @only_operator
    @external
    def add_service_operator(self, operator: Address, message: str = None) -> bool:
        if not isinstance(operator, Address) or operator.is_contract:
            self.revert("The service operator is invalid")

        if self._is_operator(operator):
            return False

        self._service_operator.add(operator)
        Logger.debug(f"add {operator} operator.")
        return True

    @only_operator
    @external
    def remove_service_operator(self, operator: Address, message: str = None) -> bool:
        if not isinstance(operator, Address) or operator.is_contract:
            self.revert("The service operator is invalid")

        if not self._is_operator(operator):
            return False

        self._service_operator.remove(operator)

    @only_operator
    @external
    def enable_mint(self, operator: Address, message: str = None) -> bool:
        if not self._is_operator(operator):
            self.revert(f"'{operator}' is not service operator.")

        self._mintable_operators[operator] = True
        return True

    @only_operator
    @external
    def disable_mint(self, operator: Address, message: str = None) -> bool:
        if not self._is_operator(operator):
            self.revert(f"'{operator}' is not service operator.")

        self._mintable_operators[operator] = False
        return True

    @only_operator
    @external
    def mint_token(self, operator: Address, value: int, message: str = None) -> bool:
        if not self._is_operator(operator):
            self.revert(f"{operator} doesn't have mint permission.")

        if not self._can_mint(operator):
            self.revert(f"{operator} can't mint")

        if message is None:
            message = 'None'

        self._balances[operator] = self._balances[operator] + value
        self._total_supply.set(self._total_supply.get() + value)
        self._mintable_operators[operator] = False

        self.Mint(operator, value, message)
        self.Transfer(self.msg.sender, operator, value, message)

        return True

    def __burn(self, who: Address, value: int):
        if self._balances[who] < value:
            self.revert(f"User balance is not enough")

        self._balances[who] -= value
        self._total_supply.set(self._total_supply.get() - value)

        self.Burn(who, value)
        self.Transfer(who, ZERO_SCORE_ADDRESS, value, 'None')

    @external
    def burn(self, value: int):
        self.__burn(self.msg.sender, value)
