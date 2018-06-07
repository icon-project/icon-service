from iconservice import *


class SampleTokenInterface(InterfaceScore):
    @interface
    def transfer(self, addr_to: Address, value: int) -> bool: pass


class SampleCrowdSale(IconScoreBase):
    __ADDR_BENEFICIARY = 'addr_beneficiary'
    __FUNDING_GOAL = 'funding_goal'
    __AMOUNT_RAISE = 'amount_raise'
    __DEAD_LINE = 'dead_line'
    __PRICE = 'price'
    __BALANCES = 'balances'
    __ADDR_TOKEN_SCORE = 'addr_token_score'
    __FUNDING_GOAL_REACHED = 'funding_goal_reached'
    __CROWD_SALE_CLOSED = 'crowd_sale_closed'
    __JOINER_LIST = 'joiner_list'

    @eventlog
    def eventlog_fund_transfer(self, backer: Address, amount: int, is_contribution: bool): pass

    @eventlog
    def eventlog_goal_reached(self, recipient: Address, total_amount_raised: int): pass

    def __init__(self, db: IconScoreDatabase, owner: Address) -> None:
        super().__init__(db, owner)

        self.__addr_beneficiary = VarDB(self.__ADDR_BENEFICIARY, db, value_type=Address)
        self.__addr_token_score = VarDB(self.__ADDR_TOKEN_SCORE, db, value_type=Address)
        self.__funding_goal = VarDB(self.__FUNDING_GOAL, db, value_type=int)
        self.__amount_raise = VarDB(self.__AMOUNT_RAISE, db, value_type=int)
        self.__dead_line = VarDB(self.__DEAD_LINE, db, value_type=int)
        self.__price = VarDB(self.__PRICE, db, value_type=int)
        self.__balances = DictDB(self.__BALANCES, db, value_type=int)
        self.__joiner_list = ArrayDB(self.__JOINER_LIST, db, value_type=Address)
        self.__funding_goal_reached = VarDB(self.__FUNDING_GOAL_REACHED, db, value_type=bool)
        self.__crowd_sale_closed = VarDB(self.__CROWD_SALE_CLOSED, db, value_type=bool)

        self.__sample_token_score = self.create_interface_score(self.__addr_token_score.get(), SampleTokenInterface)

    def on_install(self, params) -> None:
        super().on_install(params)

        one_icx = 1 * 10 ** 18
        one_minute_to_sec = 1 * 60
        one_second_to_microsec = 1 * 10 ** 6
        now_seconds = self.now()

        # genesis params
        if_successful_send_to = self.msg.sender
        addr_token_score = Address.from_string('cxb8f2c9ba48856df2e889d1ee30ff6d2e002651cf')

        funding_goal_in_icx = 100
        duration_in_minutes = 1
        icx_cost_of_each_token = 1

        self.__addr_beneficiary.set(if_successful_send_to)
        self.__addr_token_score.set(addr_token_score)
        self.__funding_goal.set(funding_goal_in_icx * one_icx)
        self.__dead_line.set(now_seconds + duration_in_minutes * one_minute_to_sec * one_second_to_microsec)
        price = int(icx_cost_of_each_token * one_icx)
        self.__price.set(price)

        self.__sample_token_score = self.create_interface_score(self.__addr_token_score.get(), SampleTokenInterface)

    def on_update(self, params) -> None:
        super().on_update(params)

    @external(readonly=True)
    def total_joiner_count(self):
        return len(self.__joiner_list)

    @payable
    def fallback(self) -> None:
        if self.__crowd_sale_closed.get():
            raise IconScoreException('crowd sale is closed')

        amount = self.msg.value
        self.__balances[self.msg.sender] = self.__balances[self.msg.sender] + amount
        self.__amount_raise.set(self.__amount_raise.get() + amount)
        value = int(amount / self.__price.get())

        self.__sample_token_score.transfer(self.msg.sender, value)

        if self.msg.sender not in self.__joiner_list:
            self.__joiner_list.put(self.msg.sender)

        self.eventlog_fund_transfer(self.msg.sender, amount, True)

    @external
    def check_goal_reached(self):
        if not self.__after_dead_line():
            raise IconScoreException('before deadline')

        if self.__amount_raise.get() >= self.__funding_goal.get():
            self.__funding_goal_reached.set(True)
            self.eventlog_goal_reached(self.__addr_beneficiary.get(), self.__amount_raise.get())
        self.__crowd_sale_closed.set(True)

    def __after_dead_line(self):
        return self.now() >= self.__dead_line.get()

    @external
    def safe_withdrawal(self):
        if not self.__after_dead_line():
            raise IconScoreException('before deadline')

        if not self.__funding_goal_reached.get():
            amount = self.__balances[self.msg.sender]
            if amount > 0:
                if self.send(self.msg.sender, amount):
                    self.eventlog_fund_transfer(self.msg.sender, amount, False)
                else:
                    self.__balances[self.msg.sender] = amount

        if self.__funding_goal_reached.get() and self.__addr_beneficiary.get() == self.msg.sender:
            if self.send(self.__addr_beneficiary.get(), self.__amount_raise.get()):
                self.eventlog_fund_transfer(self.__addr_beneficiary.get(), self.__amount_raise.get())
            else:
                self.__funding_goal_reached.set(False)
