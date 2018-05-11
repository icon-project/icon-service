from iconservice import *


@score
class SampleCrowdSale(IconScoreBase):
    _ADDR_BENEFICIARY = 'addr_beneficiary'
    _FUNDING_GOAL = 'funding_goal'
    _AMOUNT_RAISE = 'amount_raise'
    _DEAD_LINE = 'dead_line'
    _PRICE = 'price'
    _BALANCES = 'balances'
    _ADDR_TOKEN_SCORE = 'addr_token_score'
    _FUNDING_GOAL_REACHED = 'funding_goal_reached'
    _CROWD_SALE_CLOSED = 'crowd_sale_closed'
    _JOINER_LIST = 'joiner_list'

    def __init__(self, db: IconScoreDatabase, owner: Address) -> None:
        super().__init__(db, owner)

        self._addr_beneficiary = VarDB(self._ADDR_BENEFICIARY, db, value_type=Address)
        self._addr_token_score = VarDB(self._ADDR_TOKEN_SCORE, db, value_type=Address)
        self._funding_goal = VarDB(self._FUNDING_GOAL, db, value_type=int)
        self._amount_raise = VarDB(self._AMOUNT_RAISE, db, value_type=int)
        self._dead_line = VarDB(self._DEAD_LINE, db, value_type=int)
        self._price = VarDB(self._PRICE, db, value_type=int)
        self._balances = DictDB(self._BALANCES, db, value_type=int)
        self._joiner_list = ArrayDB(self._JOINER_LIST, db, value_type=Address)
        self._funding_goal_reached = VarDB(self._FUNDING_GOAL_REACHED, db, value_type=bool)
        self._crowd_sale_closed = VarDB(self._CROWD_SALE_CLOSED, db, value_type=bool)

    def genesis_init(self, *args, **kwargs) -> None:
        super().genesis_init(*args, **kwargs)

        one_icx = 1 * 10 ** 18
        one_minute_to_sec = 1 * 60
        one_second_to_microsec = 1 * 10 ** 6
        now_seconds = self.now()

        # genesis params
        if_successful_send_to = self.msg.sender
        addr_token_score = Address.from_string('cxe338f4a22eea1ef4327512b6eca37102d4ec1f84')

        funding_goal_in_icx = 100
        duration_in_minutes = 10
        icx_cost_of_each_token = 0.001

        self._addr_beneficiary.set(if_successful_send_to)
        self._addr_token_score.set(addr_token_score)
        self._funding_goal.set(funding_goal_in_icx * one_icx)
        self._dead_line.set(now_seconds + duration_in_minutes * one_minute_to_sec * one_second_to_microsec)
        price = int(icx_cost_of_each_token * one_icx)
        self._price.set(price)

    @external(readonly=True)
    def total_joiner_count(self):
        return len(self._joiner_list)

    @payable
    def fallback(self) -> None:
        if self._crowd_sale_closed.get():
            raise IconScoreBaseException('crowd sale is closed')

        amount = self.msg.value
        self._balances[self.msg.sender] = self._balances[self.msg.sender] + amount
        self._amount_raise.set(self._amount_raise.get() + amount)
        value = int(amount / self._price.get())
        self.call(self._addr_token_score.get(), 'transfer', {'addr_to': self.msg.sender, 'value': value})

        if self.msg.sender not in self._joiner_list:
            self._joiner_list.put(self.msg.sender)

        # event FundTransfer(msg.sender, amount, True)

    @external
    def check_goal_reached(self):
        if not self.__after_dead_line():
            raise IconScoreBaseException('before deadline')

        if self._amount_raise.get() >= self._funding_goal.get():
            self._funding_goal_reached.set(True)
            # event GoalReached(beneficiary, amountRaised)
        self._crowd_sale_closed.set(True)

    def __after_dead_line(self):
        return self.now() >= self._dead_line.get()

    @external
    def safe_withdrawal(self):
        if not self.__after_dead_line():
            raise IconScoreBaseException('before deadline')

        if not self._funding_goal_reached.get():
            amount = self._balances[self.msg.sender]
            if amount > 0:
                if self.send(self.msg.sender, amount):
                    # event FundTransfer(msg.sender, amount, False)
                    pass
                else:
                    self._balances[self.msg.sender] = amount

        if self._funding_goal_reached.get() and self._addr_beneficiary.get() == self.msg.sender:
            if self.send(self._addr_beneficiary.get(), self._amount_raise.get()):
                # event FundTransfer(beneficiary, amountRaised, False)
                pass
            else:
                self._funding_goal_reached.set(False)
