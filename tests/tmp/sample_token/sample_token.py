from iconservice import *


@score
class SampleToken(IconScoreBase):

    _BALANCES = 'balances'
    _TOTAL_SUPPLY = 'total_supply'

    def __init__(self, db: IconScoreDatabase, addr_owner: Address) -> None:
        super().__init__(db, addr_owner)
        self._total_supply = VarDB(self._TOTAL_SUPPLY, db, value_type=int)
        self._balances = DictDB(self._BALANCES, db, value_type=int)

    def genesis_init(self, *args, **kwargs) -> None:
        super().genesis_init(*args, **kwargs)

        init_supply = 1000
        decimal = 18
        total_supply = init_supply * 10 ** decimal

        self._total_supply.set(total_supply)
        self._balances[self.msg.sender] = total_supply

    @external(readonly=True)
    def total_supply(self) -> int:
        return self._total_supply.get()

    @external(readonly=True)
    def balance_of(self, addr_from: Address) -> int:
        return self._balances[addr_from]

    def _transfer(self, _addr_from: Address, _addr_to: Address, _value: int) -> bool:

        if self.balance_of(_addr_from) < _value:
            raise IconScoreBaseException(f"{_addr_from}'s balance < {_value}")

        self._balances[_addr_from] = self._balances[_addr_from] - _value
        self._balances[_addr_to] = self._balances[_addr_to] + _value
        return True

    @external
    def transfer(self, addr_to: Address, value: int) -> bool:
        return self._transfer(self.msg.sender, addr_to, value)

    def fallback(self) -> None:
        pass

